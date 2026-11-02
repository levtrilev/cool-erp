"""FastAPI роутер для складов с блокировками (Правило №40, часть 7)
и контролем доступа (ТЗ RBAC/ABAC §8)."""
from typing import cast
import uuid
from fastapi import APIRouter, HTTPException

from app.core.access.schemas import UserProtocol
from app.core.auth.dependencies import DBSession, CurrentUser
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.users.models import UserModel
from app.modules.inventory.warehouses.crud import (
    crud_warehouse,
    WarehouseNotFoundError,
    WarehouseVersionConflictError,
    WarehouseEditingLockedError,
)
from app.modules.inventory.warehouses.schemas import (
    InvWarehouseCreateSchema,
    InvWarehouseResponseSchema,
    InvWarehouseUpdateSchema,
)
from app.modules.inventory.warehouses.service import warehouse_service

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
        user=cast(UserProtocol, session),  # ✅ НОВОЕ: контроль доступа
        tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
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
    warehouse = await warehouse_service.create(
        db,
        obj_in=data,
        user=cast(UserModel, session),  # ✅ НОВОЕ: для установки author_id
        user_id=cast(UserProtocol, session).id,
        current_tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
    )
    await db.commit()
    await db.refresh(warehouse)
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
    """Один склад с контролем доступа (ТЗ §2.3 — нет права ⇒ 404)."""
    warehouse = await crud_warehouse.get_for_user(
        db,
        warehouse_id=warehouse_id,
        user=cast(UserProtocol, session),  # ✅ НОВОЕ: контроль доступа
        tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
    )
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Склад не найден")
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
        warehouse = await warehouse_service.update(
            db,
            warehouse_id=warehouse_id,
            obj_in=data,
            user=cast(UserProtocol, session),  # ✅ НОВОЕ: контроль доступа
            user_id=cast(UserProtocol, session).id,
            current_tenant_id=session.tenant_id,
            is_superadmin=session.is_superadmin,
        )
    except WarehouseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WarehouseVersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except WarehouseEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(warehouse)
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
            user=cast(UserProtocol, session),  # ✅ НОВОЕ: контроль доступа
            user_id=cast(UserProtocol, session).id,
            current_tenant_id=session.tenant_id,
            is_superadmin=session.is_superadmin,
        )
    except WarehouseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WarehouseEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    await db.commit()
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
            user=cast(UserProtocol, session),  # ✅ НОВОЕ: контроль доступа
            tenant_id=session.tenant_id,
            user_id=cast(UserProtocol, session).id,
            is_superadmin=session.is_superadmin,
        )
    except WarehouseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WarehouseEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
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
            user=cast(UserProtocol, session),  # ✅ НОВОЕ: контроль доступа
            tenant_id=session.tenant_id,
            user_id=cast(UserProtocol, session).id,
            is_superadmin=session.is_superadmin,
        )
    except WarehouseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WarehouseEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(warehouse)
    return ApiResponse(
        success=True,
        message="Блокировка освобождена",
        data=InvWarehouseResponseSchema.model_validate(warehouse),
    )