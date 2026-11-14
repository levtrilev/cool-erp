"""FastAPI роутер для складов с блокировками (Правило №40, часть 7)
и контролем доступа (ТЗ RBAC/ABAC §8)."""
import logging
from typing import cast
import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.core.access.schemas import UserProtocol
from app.core.audit import service as audit_service
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
    skip: int = Query(0, ge=0),
    limit: int = Query(100, gt=0, le=1000),   # ✅ защита от ZeroDivisionError
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

        # ✅ Аудит создания — в той же транзакции, через сервис
        await audit_service.log_data_create(
            db,
            tenant_id=warehouse.tenant_id,
            user_id=session.id,
            entity_type="warehouse",
            entity_id=warehouse.id,
            entity_name=warehouse.name,
            changes=data.model_dump(mode="json"),
        )


        await db.commit()          # ✅ ОДИН коммит на всю операцию
        await db.refresh(warehouse)
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка создания склада: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка создания склада",
        ) from exc

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
    # ✅ old_values собираем ДО warehouse_service.update — иначе diff будет old == new
    warehouse_before = await crud_warehouse.get(db, id=warehouse_id)
    old_values: dict[str, uuid.UUID | str | None] = {}
    if warehouse_before:
        for field in InvWarehouseUpdateSchema.model_fields:
            if field in data.model_dump(exclude_unset=True):
                old_values[field] = getattr(warehouse_before, field, None)

    try:
        warehouse = await warehouse_service.update(
            db,
            warehouse_id=warehouse_id,
            obj_in=data,
            user=cast(UserProtocol, session),
            user_id=session.id,
            current_tenant_id=session.tenant_id,
            is_superadmin=bool(session.is_superadmin),
        )

        # ✅ Аудит обновления — в той же транзакции, через сервис
        await audit_service.log_data_update(
            db,
            tenant_id=warehouse.tenant_id,
            user_id=session.id,
            entity_type="warehouse",
            entity_id=warehouse.id,
            entity_name=warehouse.name,
            old_values=old_values,
            new_values=data.model_dump(exclude_unset=True),
        )


        await db.commit()          # ✅ ОДИН коммит на update + audit
        await db.refresh(warehouse)
    except WarehouseNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WarehouseVersionConflictError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WarehouseEditingLockedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except WarehousePermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка обновления склада %s: %s", warehouse_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка обновления склада",
        ) from exc

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

        # ✅ Аудит удаления — в той же транзакции, через сервис
        await audit_service.log_data_delete(
            db,
            tenant_id=warehouse.tenant_id,
            user_id=session.id,
            entity_type="warehouse",
            entity_id=warehouse.id,
            entity_name=warehouse.name,
        )


        await db.commit()          # ✅ ОДИН коммит на delete + audit
    except WarehouseNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WarehouseEditingLockedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except WarehousePermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка удаления склада %s: %s", warehouse_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка удаления склада",
        ) from exc

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



        await db.commit()
        await db.refresh(warehouse)
    except WarehouseNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WarehouseEditingLockedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except WarehousePermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка захвата блокировки склада %s: %s", warehouse_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка захвата блокировки",
        ) from exc

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



        await db.commit()
        await db.refresh(warehouse)
    except WarehouseNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WarehouseEditingLockedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка освобождения блокировки склада %s: %s", warehouse_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка освобождения блокировки",
        ) from exc

    return ApiResponse(
        success=True,
        message="Блокировка освобождена",
        data=InvWarehouseResponseSchema.model_validate(warehouse),
    )