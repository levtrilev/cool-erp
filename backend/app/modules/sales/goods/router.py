"""FastAPI роутер для товаров с блокировками (Правило №40, часть 7)
и контролем доступа."""
import logging
from typing import cast
import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.core.access.schemas import UserProtocol
from app.core.audit import service as audit_service
from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.schemas import ApiResponse, PaginatedResponse
from app.modules.sales.goods.crud import (
    GoodsEditingLockedError,
    GoodsNotFoundError,
    GoodsVersionConflictError,
    crud_goods,
)
from app.modules.sales.goods.schemas import (
    SalesGoodsCreateSchema,
    SalesGoodsResponseSchema,
    SalesGoodsUpdateSchema,
)
from app.modules.sales.goods.service import goods_service
# ======
from datetime import date

from app.core.schemas import ApiResponse, PaginatedResponse, SortOrder
from app.modules.sales.goods.crud import (
    GoodsEditingLockedError,
    GoodsNotFoundError,
    GoodsPermissionError,
    GoodsVersionConflictError,
    crud_goods,
)
from app.modules.sales.goods.schemas import (
    SalesGoodsCreateSchema,
    SalesGoodsResponseSchema,
    SalesGoodsSortField,
    SalesGoodsUpdateSchema,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sales/goods", tags=["Sales: goods"])


@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[SalesGoodsResponseSchema]],
)
async def list_goods(
    db: DBSession,
    session: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, gt=0, le=1000),   # ✅ защита от ZeroDivisionError
    search: str | None = None,
    sort_by: SalesGoodsSortField | None = None,
    sort_order: SortOrder = SortOrder.ASC,
    filter_name: str | None = None,
    filter_item_type_name: str | None = None,
    filter_updated_at: date | None = None,
) -> ApiResponse[PaginatedResponse[SalesGoodsResponseSchema]]:
    """Список товаров с контролем доступа, сортировкой и фильтрами."""
    items, total = await crud_goods.get_multi(
        db,
        user=cast(UserProtocol, session),
        tenant_id=session.tenant_id,
        is_superadmin=bool(session.is_superadmin),
        skip=skip,
        limit=limit,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        filter_name=filter_name,
        filter_item_type_name=filter_item_type_name,
        filter_updated_at=filter_updated_at,
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
    """Создание товара с проверкой права создания."""
    try:
        goods = await goods_service.create(
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
            tenant_id=goods.tenant_id,
            user_id=session.id,
            entity_type="goods",
            entity_id=goods.id,
            entity_name=goods.name,
            changes=data.model_dump(mode="json"),
        )


        await db.commit()          # ✅ ОДИН коммит на всю операцию
        await db.refresh(goods)
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка создания товара: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка создания товара",
        ) from exc

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
    """Один товар с контролем доступа."""
    goods = await crud_goods.get_for_user(
        db,
        goods_id=goods_id,
        user=cast(UserProtocol, session),
        tenant_id=session.tenant_id,
        is_superadmin=bool(session.is_superadmin),
    )

    if goods is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")

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
    """Сохранение с проверкой версии, блокировки и права изменения."""
    # ✅ old_values собираем ДО goods_service.update — иначе diff будет old == new
    goods_before = await crud_goods.get(db, id=goods_id)
    old_values: dict[str, uuid.UUID | str | None] = {}
    if goods_before:
        for field in SalesGoodsUpdateSchema.model_fields:
            if field in data.model_dump(exclude_unset=True):
                old_values[field] = getattr(goods_before, field, None)

    try:
        goods = await goods_service.update(
            db,
            goods_id=goods_id,
            obj_in=data,
            user=cast(UserProtocol, session),
            user_id=session.id,
            current_tenant_id=session.tenant_id,
            is_superadmin=bool(session.is_superadmin),
        )

        # ✅ Аудит обновления — в той же транзакции, через сервис
        await audit_service.log_data_update(
            db,
            tenant_id=goods.tenant_id,
            user_id=session.id,
            entity_type="goods",
            entity_id=goods.id,
            entity_name=goods.name,
            old_values=old_values,
            new_values=data.model_dump(exclude_unset=True),
        )


        await db.commit()          # ✅ ОДИН коммит на update + audit
        await db.refresh(goods)
    except GoodsNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoodsVersionConflictError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except GoodsEditingLockedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except GoodsPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

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
    """Мягкое удаление с проверкой блокировки и can_delete."""
    try:
        goods = await goods_service.delete(
            db,
            goods_id=goods_id,
            user=cast(UserProtocol, session),
            user_id=session.id,
            current_tenant_id=session.tenant_id,
            is_superadmin=bool(session.is_superadmin),
        )

        # ✅ Аудит удаления — в той же транзакции, через сервис
        await audit_service.log_data_delete(
            db,
            tenant_id=goods.tenant_id,
            user_id=session.id,
            entity_type="goods",
            entity_id=goods.id,
            entity_name=goods.name,
        )


        await db.commit()          # ✅ ОДИН коммит на delete + audit
    except GoodsNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoodsEditingLockedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка удаления товара %s: %s", goods_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка удаления товара",
        ) from exc

    return ApiResponse(
        success=True,
        message="Товар удалён",
        data=SalesGoodsResponseSchema.model_validate(goods),
    )


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
            user=cast(UserProtocol, session),
            tenant_id=session.tenant_id,
            user_id=session.id,
            is_superadmin=bool(session.is_superadmin),
        )



        await db.commit()
        await db.refresh(goods)
    except GoodsNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoodsEditingLockedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка захвата блокировки товара %s: %s", goods_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка захвата блокировки",
        ) from exc

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
            user=cast(UserProtocol, session),
            tenant_id=session.tenant_id,
            user_id=session.id,
            is_superadmin=bool(session.is_superadmin),
        )


        await db.commit()
        await db.refresh(goods)
    except GoodsNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoodsEditingLockedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка освобождения блокировки товара %s: %s", goods_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка освобождения блокировки",
        ) from exc

    return ApiResponse(
        success=True,
        message="Блокировка освобождена",
        data=SalesGoodsResponseSchema.model_validate(goods),
    )