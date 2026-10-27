"""FastAPI роутер для товаров с блокировками (Правило №40, часть 7)."""
from typing import cast
import uuid

from fastapi import APIRouter, HTTPException

from app.core.auth.dependencies import DBSession, CurrentUser
from app.core.schemas import ApiResponse, PaginatedResponse
from app.modules.sales.goods.crud import (
    crud_goods,
    GoodsEditingLockedError,
    GoodsNotFoundError,
    GoodsVersionConflictError,
)
from app.modules.sales.goods.schemas import (
    SalesGoodsCreateSchema,
    SalesGoodsResponseSchema,
    SalesGoodsUpdateSchema,
)
from app.modules.sales.goods.service import goods_service
from app.core.access.schemas import UserProtocol

router = APIRouter(prefix="/sales/goods", tags=["Sales: goods"])


@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[SalesGoodsResponseSchema]],
)
async def list_goods(
    db: DBSession,
    session: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
) -> ApiResponse[PaginatedResponse[SalesGoodsResponseSchema]]:
    """Список товаров."""
    items, total = await crud_goods.get_multi(
        db,
        tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
        skip=skip,
        limit=limit,
        search=search,
    )
    return ApiResponse(
        success=True,
        message="Товары получены",
        data=PaginatedResponse(
            items=[SalesGoodsResponseSchema.model_validate(i) for i in items],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
        ),
    )


@router.post(
    "/",
    response_model=ApiResponse[SalesGoodsResponseSchema],
)
async def create_goods(
    data: SalesGoodsCreateSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesGoodsResponseSchema]:
    """Создание товара."""
    try:
        goods = await goods_service.create(
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
    await db.refresh(goods)
    return ApiResponse(
        success=True,
        message="Товар создан",
        data=SalesGoodsResponseSchema.model_validate(goods),
    )


@router.get(
    "/{goods_id}",
    response_model=ApiResponse[SalesGoodsResponseSchema],
)
async def get_goods(
    goods_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesGoodsResponseSchema]:
    """Один товар."""
    goods = await crud_goods.get_for_user(
        db,
        goods_id=goods_id,
        tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
    )
    if goods is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return ApiResponse(
        success=True,
        message="Товар получен",
        data=SalesGoodsResponseSchema.model_validate(goods),
    )


@router.put(
    "/{goods_id}",
    response_model=ApiResponse[SalesGoodsResponseSchema],
)
async def update_goods(
    goods_id: uuid.UUID,
    data: SalesGoodsUpdateSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesGoodsResponseSchema]:
    """Сохранение с проверкой версии (409) и блокировки (423)."""
    try:
        goods = await goods_service.update(
            db,
            goods_id=goods_id,
            obj_in=data,
            user_id=cast(UserProtocol, session).id,
            current_tenant_id=session.tenant_id,
            is_superadmin=session.is_superadmin,
        )
    except GoodsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GoodsVersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GoodsEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(goods)
    return ApiResponse(
        success=True,
        message="Товар обновлён",
        data=SalesGoodsResponseSchema.model_validate(goods),
    )


@router.delete(
    "/{goods_id}",
    response_model=ApiResponse[SalesGoodsResponseSchema],
)
async def delete_goods(
    goods_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesGoodsResponseSchema]:
    """Мягкое удаление с проверкой блокировки (423)."""
    try:
        goods = await goods_service.delete(
            db,
            goods_id=goods_id,
            user_id=cast(UserProtocol, session).id,
            current_tenant_id=session.tenant_id,
            is_superadmin=session.is_superadmin,
        )
    except GoodsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GoodsEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    return ApiResponse(
        success=True,
        message="Товар удалён",
        data=SalesGoodsResponseSchema.model_validate(goods),
    )


# ==================================================================
# БЛОКИРОВКИ РЕДАКТИРОВАНИЯ (Правило №40, часть 7.1)
# ==================================================================


@router.post(
    "/{goods_id}/lock",
    response_model=ApiResponse[SalesGoodsResponseSchema],
)
async def acquire_goods_lock(
    goods_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesGoodsResponseSchema]:
    """Захват пессимистической блокировки редактирования."""
    try:
        goods = await crud_goods.acquire_editing_lock(
            db,
            goods_id=goods_id,
            tenant_id=session.tenant_id,
            user_id=cast(UserProtocol, session).id,
            is_superadmin=session.is_superadmin,
        )
    except GoodsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GoodsEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(goods)
    return ApiResponse(
        success=True,
        message="Блокировка захвачена",
        data=SalesGoodsResponseSchema.model_validate(goods),
    )


@router.delete(
    "/{goods_id}/lock",
    response_model=ApiResponse[SalesGoodsResponseSchema],
)
async def release_goods_lock(
    goods_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesGoodsResponseSchema]:
    """Освобождение пессимистической блокировки редактирования."""
    try:
        goods = await crud_goods.release_editing_lock(
            db,
            goods_id=goods_id,
            tenant_id=session.tenant_id,
            user_id=cast(UserProtocol, session).id,
            is_superadmin=session.is_superadmin,
        )
    except GoodsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GoodsEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(goods)
    return ApiResponse(
        success=True,
        message="Блокировка освобождена",
        data=SalesGoodsResponseSchema.model_validate(goods),
    )