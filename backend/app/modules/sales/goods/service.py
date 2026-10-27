"""Сервис товаров с публикацией событий репликации."""
import uuid
import logging
from datetime import datetime, timezone # pyright: ignore[reportUnusedImport]

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.outbox import outbox
from app.modules.sales.goods.crud import (
    crud_goods,
    GoodsNotFoundError, # pyright: ignore[reportUnusedImport]
)
from app.modules.sales.goods.models import SalesGoodsModel
from app.modules.sales.goods.schemas import (
    SalesGoodsCreateSchema,
    SalesGoodsUpdateSchema,
)

logger = logging.getLogger(__name__)


class GoodsService:
    """Публичный сервис домена sales."""

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: SalesGoodsCreateSchema,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """Создание товара + публикация события для репликации."""
        # ✅ Мультивенантная изоляция: обычный пользователь не может
        # создавать товар в чужой организации
        tenant_id = obj_in.tenant_id or current_tenant_id
        if not is_superadmin and tenant_id != current_tenant_id:
            raise PermissionError("Нет доступа к другой организации")

        data_dict = obj_in.model_dump(exclude_unset=True)
        data_dict["tenant_id"] = tenant_id
        data_dict["author_id"] = user_id
        data_dict["created_by_user_id"] = user_id

        goods = SalesGoodsModel(**data_dict)
        db.add(goods)
        await db.flush()
        await db.refresh(goods)

        await self._publish_event(db, "sales.goods.created", goods)
        return goods

    async def update(
        self,
        db: AsyncSession,
        *,
        goods_id: uuid.UUID,
        obj_in: SalesGoodsUpdateSchema,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """Обновление товара с проверкой блокировок."""
        updated = await crud_goods.save_with_version(
            db,
            goods_id=goods_id,
            obj_in=obj_in,
            tenant_id=current_tenant_id,
            user_id=user_id,
            is_superadmin=is_superadmin,
        )
        await self._publish_event(db, "sales.goods.updated", updated)
        return updated

    async def delete(
        self,
        db: AsyncSession,
        *,
        goods_id: uuid.UUID,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """Мягкое удаление товара."""
        deleted = await crud_goods.mark_deleted(
            db,
            goods_id=goods_id,
            tenant_id=current_tenant_id,
            user_id=user_id,
            is_superadmin=is_superadmin,
        )
        # ✅ Публикация события удаления для репликации
        # await outbox.publish_ordered(
        await outbox.publish(
            db,
            event_type="sales.goods.deleted",
            source_domain="sales",
            aggregate_type="sales_goods",
            aggregate_id=goods_id,
            payload={"id": str(goods_id), "is_deleted": True},
            ordering_key=f"sales:sales_goods:{goods_id}",
        )
        return deleted

    # ==================================================================
    # ПУБЛИКАЦИЯ СОБЫТИЙ ДЛЯ РЕПЛИКАЦИИ
    # ==================================================================

    async def _publish_event(
        self,
        db: AsyncSession,
        event_type: str,
        goods: SalesGoodsModel,
    ) -> None:
        """Публикация события изменения товара для репликации в другие домены."""
        await outbox.publish(
            db,
            event_type=event_type,
            source_domain="sales",
            aggregate_type="sales_goods",
            aggregate_id=goods.id,
            payload={
                "id": str(goods.id),
                "name": goods.name,
                "description": goods.description,
                "tenant_id": str(goods.tenant_id),
                "is_deleted": False,
            },
            ordering_key=f"sales:sales_goods:{goods.id}",
        )


goods_service = GoodsService()