"""FastAPI роутер для товаров с блокировками (Правило №40, часть 7)
и контролем доступа."""
import logging
from typing import cast
import uuid
from typing import cast

from fastapi import APIRouter, HTTPException, status

from app.core.access.schemas import UserProtocol
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
# from app.core.audit.utils import get_entity_name
from app.modules.sales.goods.service import goods_service

logger = logging.getLogger(__name__)

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
    """Список товаров с контролем доступа."""
    items, total = await crud_goods.get_multi(
        db,
        user=cast(UserProtocol, session),
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
    """Создание товара с проверкой права создания."""
    try:
        goods = await goods_service.create(
            db,
            obj_in=data,
            user=cast(UserProtocol, session),
            user_id=cast(UserProtocol, session).id,
            current_tenant_id=session.tenant_id,
            is_superadmin=session.is_superadmin,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(goods)

    # ✅ ЗАПИСЬ В АУДИТ: создание товара
    # try:
    #     from app.core.audit.models import DataAuditLog

    #     audit_log = DataAuditLog(
    #         id=uuid.uuid4(),
    #         tenant_id=session.tenant_id,
    #         user_id=session.id,
    #         entity_type="goods",
    #         entity_id=goods.id,
    #         entity_name=goods.name,
    #         action="create",
    #         changes=None,
    #     )
    #     db.add(audit_log)
    #     await db.commit()
    # except Exception as e:
    #     logger.warning(f"Could not write data audit: {e}")

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
        is_superadmin=session.is_superadmin,
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
    try:
        # ✅ Сохраняем текущие значения полей перед обновлением
        # goods_before = await crud_goods.get(db, id=goods_id)
        # old_values = {}
        # if goods_before:
        #     for field in data.model_fields:
        #         if field in data.model_dump(exclude_unset=True):
        #             old_values[field] = getattr(goods_before, field, None)

        goods = await goods_service.update(
            db,
            goods_id=goods_id,
            obj_in=data,
            user=cast(UserProtocol, session),
            user_id=cast(UserProtocol, session).id,
            current_tenant_id=session.tenant_id,
            is_superadmin=session.is_superadmin,
        )
    except GoodsNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoodsVersionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except GoodsEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(goods)

    # ✅ ЗАПИСЬ В АУДИТ: обновление товара
    # try:
    #     from app.core.audit.models import DataAuditLog

    #     # Формируем словарь изменений
    #     changes = {}
    #     dump = data.model_dump(exclude_unset=True)
    #     for field, new_value in dump.items():
    #         if field in old_values and old_values[field] != new_value:
    #             if field.endswith('_id'):
    #                 old_name = await get_entity_name(db, field[:-3], old_values[field])
    #                 new_name = await get_entity_name(db, field[:-3], new_value)
    #                 changes[field] = {
    #                     "old": old_name if old_name else str(old_values[field]),
    #                     "new": new_name if new_name else str(new_value)
    #                 }
    #             else:
    #                 changes[field] = {"old": str(old_values[field]), "new": str(new_value)}

    #     if changes:
    #         audit_log = DataAuditLog(
    #             id=uuid.uuid4(),
    #             tenant_id=session.tenant_id,
    #             user_id=session.id,
    #             entity_type="goods",
    #             entity_id=goods.id,
    #             entity_name=goods.name,
    #             action="update",
    #             changes=changes if changes else None,
    #         )
    #         db.add(audit_log)
    #         await db.commit()
    # except Exception as e:
    #     logger.warning(f"Could not write data audit: {e}")

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
            user_id=cast(UserProtocol, session).id,
            current_tenant_id=session.tenant_id,
            is_superadmin=session.is_superadmin,
        )
    except GoodsNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoodsEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc

    await db.commit()

    # ✅ ЗАПИСЬ В АУДИТ: удаление товара
    # try:
    #     from app.core.audit.models import DataAuditLog

    #     audit_log = DataAuditLog(
    #         id=uuid.uuid4(),
    #         tenant_id=session.tenant_id,
    #         user_id=session.id,
    #         entity_type="goods",
    #         entity_id=goods.id,
    #         entity_name=goods.name,
    #         action="delete",
    #         changes={"deleted": True},
    #     )
    #     db.add(audit_log)
    #     await db.commit()
    # except Exception as e:
    #     logger.warning(f"Could not write data audit: {e}")

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
            user_id=cast(UserProtocol, session).id,
            is_superadmin=session.is_superadmin,
        )
    except GoodsNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoodsEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc

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
            user=cast(UserProtocol, session),
            tenant_id=session.tenant_id,
            user_id=cast(UserProtocol, session).id,
            is_superadmin=session.is_superadmin,
        )
    except GoodsNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoodsEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(goods)

    return ApiResponse(
        success=True,
        message="Блокировка освобождена",
        data=SalesGoodsResponseSchema.model_validate(goods),
    )