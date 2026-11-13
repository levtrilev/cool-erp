"""FastAPI роутер для складов с блокировками (Правило №40, часть 7)
и контролем доступа (ТЗ RBAC/ABAC §8)."""
import logging
from typing import cast
import uuid
from fastapi import APIRouter, HTTPException, status

from app.core.access.schemas import UserProtocol
from app.core.auth.dependencies import DBSession, CurrentUser
from app.core.schemas import ApiResponse, PaginatedResponse
from app.modules.inventory.warehouses.crud import (
    crud_warehouse,
    WarehouseNotFoundError,
    WarehouseVersionConflictError,
    WarehouseEditingLockedError,
    WarehousePermissionError,
)
from app.modules.inventory.warehouses.schemas import (
    InvWarehouseCreateSchema,
    InvWarehouseResponseSchema,
    InvWarehouseUpdateSchema,
)
from app.core.audit.utils import get_entity_name
from app.modules.inventory.warehouses.service import warehouse_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory/warehouses", tags=["Inventory: warehouses"])


@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[InvWarehouseResponseSchema]],
)
async def list_warehouses(
    db: DBSession,
    session: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
) -> ApiResponse[PaginatedResponse[InvWarehouseResponseSchema]]:
    """Список складов с контролем доступа через AccessService (все 5 слоёв)."""
    items, total = await crud_warehouse.get_multi(
        db,
        user=cast(UserProtocol, session),
        tenant_id=session.tenant_id,
        is_superadmin=bool(session.is_superadmin),
        skip=skip,
        limit=limit,
        search=search,
    )
    return ApiResponse(
        success=True,
        message="Склады получены",
        data=PaginatedResponse(
            items=[InvWarehouseResponseSchema.model_validate(i) for i in items],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
        ),
    )


@router.post(
    "/",
    response_model=ApiResponse[InvWarehouseResponseSchema],
)
async def create_warehouse(
    data: InvWarehouseCreateSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[InvWarehouseResponseSchema]:
    """Создание склада."""
    try:
        warehouse = await warehouse_service.create(
            db,
            obj_in=data,
            user=cast(UserProtocol, session),
            user_id=session.id,
            current_tenant_id=session.tenant_id,
            is_superadmin=bool(session.is_superadmin),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(warehouse)

    # ✅ ЗАПИСЬ В АУДИТ: создание склада
    try:
        from app.core.audit.models import DataAuditLog

        audit_log = DataAuditLog(
            id=uuid.uuid4(),
            tenant_id=session.tenant_id,
            user_id=session.id,
            entity_type="warehouse",
            entity_id=warehouse.id,
            entity_name=warehouse.name,
            action="create",
            changes=None,
        )
        db.add(audit_log)
        await db.commit()
    except Exception as e:
        logger.warning(f"Could not write data audit: {e}")

    return ApiResponse(
        success=True,
        message="Склад создан",
        data=InvWarehouseResponseSchema.model_validate(warehouse),
    )


@router.get(
    "/{warehouse_id}",
    response_model=ApiResponse[InvWarehouseResponseSchema],
)
async def get_warehouse(
    warehouse_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[InvWarehouseResponseSchema]:
    """Один склад с контролем доступа (ТЗ §2.3 — нет права ⇒ 404,403)."""
    warehouse = await crud_warehouse.get_for_user(
        db,
        warehouse_id=warehouse_id,
        user=cast(UserProtocol, session),
        tenant_id=session.tenant_id,
        is_superadmin=bool(session.is_superadmin),
    )
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Склад не найден")
    return ApiResponse(
        success=True,
        message="Склад получен",
        data=InvWarehouseResponseSchema.model_validate(warehouse),
    )


@router.put(
    "/{warehouse_id}",
    response_model=ApiResponse[InvWarehouseResponseSchema],
)
async def update_warehouse(
    warehouse_id: uuid.UUID,
    data: InvWarehouseUpdateSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[InvWarehouseResponseSchema]:
    """Сохранение с проверкой версии (409), блокировки (423) и контроля доступа."""
    try:
        # ✅ Сохраняем текущие значения полей перед обновлением
        warehouse_before = await crud_warehouse.get(db, id=warehouse_id)
        old_values: dict[str, uuid.UUID | str | None] = {}
        if warehouse_before:
            for field in InvWarehouseUpdateSchema.model_fields:
                if field in data.model_dump(exclude_unset=True):
                    old_values[field] = getattr(warehouse_before, field, None)

        warehouse = await warehouse_service.update(
            db,
            warehouse_id=warehouse_id,
            obj_in=data,
            user=cast(UserProtocol, session),
            user_id=session.id,
            current_tenant_id=session.tenant_id,
            is_superadmin=bool(session.is_superadmin),
        )
    except WarehouseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WarehouseVersionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WarehouseEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(warehouse)

    # ✅ ЗАПИСЬ В АУДИТ: обновление склада
    try:
        from app.core.audit.models import DataAuditLog

        # Формируем словарь изменений
        changes = {}
        dump = data.model_dump(exclude_unset=True)
        for field, new_value in dump.items():
            if field in old_values and old_values[field] != new_value:
                if field.endswith('_id'):
                    old_entity_id = uuid.UUID(str(old_values[field])) if old_values[field] else None
                    new_entity_id = uuid.UUID(str(new_value)) if new_value else None
                    if old_entity_id:
                        old_name = await get_entity_name(db, field[:-3], old_entity_id)
                    else:
                        old_name = ""
                    if new_entity_id:
                        new_name = await get_entity_name(db, field[:-3], new_entity_id)
                    else:
                        new_name = ""
                    changes[field] = {
                        "old": old_name if old_name else str(old_values[field]),
                        "new": new_name if new_name else str(new_value)
                    }
                else:
                    changes[field] = {"old": str(old_values[field]), "new": str(new_value)}

        if changes:
            audit_log = DataAuditLog(
                id=uuid.uuid4(),
                tenant_id=session.tenant_id,
                user_id=session.id,
                entity_type="warehouse",
                entity_id=warehouse.id,
                entity_name=warehouse.name,
                action="update",
                changes=changes if changes else None,
            )
            db.add(audit_log)
            await db.commit()
    except Exception as e:
        logger.warning(f"Could not write data audit: {e}")

    return ApiResponse(
        success=True,
        message="Склад обновлён",
        data=InvWarehouseResponseSchema.model_validate(warehouse),
    )


@router.delete(
    "/{warehouse_id}",
    response_model=ApiResponse[InvWarehouseResponseSchema],
)
async def delete_warehouse(
    warehouse_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[InvWarehouseResponseSchema]:
    """Мягкое удаление с проверкой блокировки (423) и контроля доступа (can_delete)."""
    try:
        warehouse = await warehouse_service.delete(
            db,
            warehouse_id=warehouse_id,
            user=cast(UserProtocol, session),
            user_id=session.id,
            current_tenant_id=session.tenant_id,
            is_superadmin=bool(session.is_superadmin),
        )
    except WarehouseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WarehouseEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except WarehousePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    await db.commit()

    # ✅ ЗАПИСЬ В АУДИТ: удаление склада
    try:
        from app.core.audit.models import DataAuditLog

        audit_log = DataAuditLog(
            id=uuid.uuid4(),
            tenant_id=session.tenant_id,
            user_id=session.id,
            entity_type="warehouse",
            entity_id=warehouse.id,
            entity_name=warehouse.name,
            action="delete",
            changes={"deleted": True},
        )
        db.add(audit_log)
        await db.commit()
    except Exception as e:
        logger.warning(f"Could not write data audit: {e}")

    return ApiResponse(
        success=True,
        message="Склад удалён",
        data=InvWarehouseResponseSchema.model_validate(warehouse),
    )


# ================================================================
# БЛОКИРОВКИ РЕДАКТИРОВАНИЯ (Правило №40, часть 7.1)
# ================================================================


@router.post(
    "/{warehouse_id}/lock",
    response_model=ApiResponse[InvWarehouseResponseSchema],
)
async def acquire_warehouse_lock(
    warehouse_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[InvWarehouseResponseSchema]:
    """Захват пессимистической блокировки редактирования."""
    try:
        warehouse = await crud_warehouse.acquire_editing_lock(
            db,
            warehouse_id=warehouse_id,
            user=cast(UserProtocol, session),
            tenant_id=session.tenant_id,
            user_id=session.id,
            is_superadmin=bool(session.is_superadmin),
        )
    except WarehouseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WarehouseEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except WarehousePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(warehouse)
    return ApiResponse(
        success=True,
        message="Блокировка захвачена",
        data=InvWarehouseResponseSchema.model_validate(warehouse),
    )


@router.delete(
    "/{warehouse_id}/lock",
    response_model=ApiResponse[InvWarehouseResponseSchema],
)
async def release_warehouse_lock(
    warehouse_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[InvWarehouseResponseSchema]:
    """Освобождение пессимистической блокировки редактирования."""
    try:
        warehouse = await crud_warehouse.release_editing_lock(
            db,
            warehouse_id=warehouse_id,
            user=cast(UserProtocol, session),
            tenant_id=session.tenant_id,
            user_id=session.id,
            is_superadmin=bool(session.is_superadmin),
        )
    except WarehouseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WarehouseEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(warehouse)
    return ApiResponse(
        success=True,
        message="Блокировка освобождена",
        data=InvWarehouseResponseSchema.model_validate(warehouse),
    )