"""FastAPI роутер для регионов с блокировками (Правило №40, часть 7)."""
from typing import cast
import uuid

from fastapi import APIRouter, HTTPException

from app.core.auth.dependencies import DBSession, CurrentUser
from app.core.schemas import ApiResponse, PaginatedResponse
from app.modules.sales.regions.crud import (
    crud_region,
    RegionEditingLockedError,
    RegionNotFoundError,
    RegionVersionConflictError,
)
from app.modules.sales.regions.schemas import (
    SalesRegionCreateSchema,
    SalesRegionResponseSchema,
    SalesRegionUpdateSchema,
)
from app.modules.sales.regions.service import region_service
from app.core.access.schemas import UserProtocol

router = APIRouter(
    prefix="/sales/regions",
    tags=["Sales: regions"],
)


@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[SalesRegionResponseSchema]],
)
async def list_regions(
    db: DBSession,
    session: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
) -> ApiResponse[PaginatedResponse[SalesRegionResponseSchema]]:
    """Список регионов."""
    items, total = await crud_region.get_multi(
        db,
        tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
        skip=skip,
        limit=limit,
        search=search,
    )
    return ApiResponse(
        success=True,
        message="Регионы получены",
        data=PaginatedResponse(
            items=[SalesRegionResponseSchema.model_validate(i) for i in items],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
        ),
    )


@router.post(
    "/",
    response_model=ApiResponse[SalesRegionResponseSchema],
)
async def create_region(
    data: SalesRegionCreateSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesRegionResponseSchema]:
    """Создание региона."""
    try:
        region = await region_service.create(
            db,
            obj_in=data,
            user_id=cast(UserProtocol, session).id,
            current_tenant_id=session.tenant_id,
            is_superadmin=session.is_superadmin,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    # ✅ Правило №40, часть 8.1: commit выполняется в роутере
    await db.commit()
    await db.refresh(region)
    return ApiResponse(
        success=True,
        message="Регион создан",
        data=SalesRegionResponseSchema.model_validate(region),
    )


@router.get(
    "/{region_id}",
    response_model=ApiResponse[SalesRegionResponseSchema],
)
async def get_region(
    region_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesRegionResponseSchema]:
    """Один регион."""
    region = await crud_region.get_for_user(
        db,
        region_id=region_id,
        tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
    )
    if region is None:
        raise HTTPException(status_code=404, detail="Регион не найден")
    return ApiResponse(
        success=True,
        message="Регион получен",
        data=SalesRegionResponseSchema.model_validate(region),
    )


@router.put(
    "/{region_id}",
    response_model=ApiResponse[SalesRegionResponseSchema],
)
async def update_region(
    region_id: uuid.UUID,
    data: SalesRegionUpdateSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesRegionResponseSchema]:
    """Сохранение с проверкой версии (409) и блокировки (423)."""
    try:
        region = await region_service.update(
            db,
            region_id=region_id,
            obj_in=data,
            user_id=cast(UserProtocol, session).id,
            current_tenant_id=session.tenant_id,
            is_superadmin=session.is_superadmin,
        )
    except RegionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RegionVersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RegionEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(region)
    return ApiResponse(
        success=True,
        message="Регион обновлён",
        data=SalesRegionResponseSchema.model_validate(region),
    )


@router.delete(
    "/{region_id}",
    response_model=ApiResponse[SalesRegionResponseSchema],
)
async def delete_region(
    region_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesRegionResponseSchema]:
    """Мягкое удаление с проверкой блокировки (423)."""
    try:
        region = await region_service.delete(
            db,
            region_id=region_id,
            user_id=cast(UserProtocol, session).id,
            current_tenant_id=session.tenant_id,
            is_superadmin=session.is_superadmin,
        )
    except RegionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RegionEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    return ApiResponse(
        success=True,
        message="Регион удалён",
        data=SalesRegionResponseSchema.model_validate(region),
    )


# ==================================================================
# БЛОКИРОВКИ РЕДАКТИРОВАНИЯ (Правило №40, часть 7.1)
# ==================================================================


@router.post(
    "/{region_id}/lock",
    response_model=ApiResponse[SalesRegionResponseSchema],
)
async def acquire_region_lock(
    region_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesRegionResponseSchema]:
    """Захват пессимистической блокировки редактирования."""
    try:
        region = await crud_region.acquire_editing_lock(
            db,
            region_id=region_id,
            tenant_id=session.tenant_id,
            user_id=cast(UserProtocol, session).id,
            is_superadmin=session.is_superadmin,
        )
    except RegionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RegionEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(region)
    return ApiResponse(
        success=True,
        message="Блокировка захвачена",
        data=SalesRegionResponseSchema.model_validate(region),
    )


@router.delete(
    "/{region_id}/lock",
    response_model=ApiResponse[SalesRegionResponseSchema],
)
async def release_region_lock(
    region_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesRegionResponseSchema]:
    """Освобождение пессимистической блокировки редактирования."""
    try:
        region = await crud_region.release_editing_lock(
            db,
            region_id=region_id,
            tenant_id=session.tenant_id,
            user_id=cast(UserProtocol, session).id,
            is_superadmin=session.is_superadmin,
        )
    except RegionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RegionEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(region)
    return ApiResponse(
        success=True,
        message="Блокировка освобождена",
        data=SalesRegionResponseSchema.model_validate(region),
    )