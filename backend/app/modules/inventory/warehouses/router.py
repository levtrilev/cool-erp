"""FastAPI роутер для складов с блокировками."""
from typing import cast
import uuid

from fastapi import APIRouter, HTTPException

from app.core.auth.dependencies import DBSession, CurrentUser
from app.core.schemas import ApiResponse, PaginatedResponse
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
from app.core.access.schemas import UserProtocol

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
    items, total = await crud_warehouse.get_multi(
        db,
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
    warehouse = await warehouse_service.create(
        db,
        obj_in=data,
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
    """Сохранение с проверкой версии (409) и блокировки (423)."""
    try:
        warehouse = await warehouse_service.update(
            db,
            warehouse_id=warehouse_id,
            obj_in=data,
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
    try:
        warehouse = await warehouse_service.delete(
            db,
            warehouse_id=warehouse_id,
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