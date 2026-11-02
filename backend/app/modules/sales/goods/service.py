"""Сервис товаров с публикацией событий репликации и контролем доступа."""
import uuid
from typing import cast as typing_cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access.schemas import AccessResult, UserProtocol
from app.core.access.service import AccessService, DocumentProtocol
from app.core.events.outbox import outbox
from app.modules.sales.goods.crud import crud_goods
from app.modules.sales.goods.models import SalesGoodsModel
from app.modules.sales.goods.schemas import (
    SalesGoodsCreateSchema,
    SalesGoodsUpdateSchema,
)


class GoodsService:
    """Публичный сервис домена sales."""

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: SalesGoodsCreateSchema,
        user: UserProtocol,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """
        Создание товара + публикация события репликации.

        Проверка доступа:
        - создаём экземпляр документа с author_id = user.id;
        - проверяем AccessService.resolve_access();
        - создание разрешено только при level >= 2.
        """
        if user_id != user.id:
            raise PermissionError("Некорректный пользователь операции")

        tenant_id: uuid.UUID = obj_in.tenant_id or current_tenant_id

        if not is_superadmin and tenant_id != current_tenant_id:
            raise PermissionError("Нет доступа к другой организации")

        data_dict: dict[str, object] = obj_in.model_dump(exclude_unset=True)
        data_dict["tenant_id"] = tenant_id
        data_dict["author_id"] = user.id
        data_dict["created_by_user_id"] = user.id

        goods = SalesGoodsModel(**data_dict)

        access_service = AccessService(db)

        # Правило №45: каст экземпляра документа к DocumentProtocol.
        # Экземпляр новый, ещё не сохранён в БД, но уже содержит контракт доступа:
        # tenant_id, section_id, author_id, or_tags, and_tags.
        goods_doc: DocumentProtocol = typing_cast("DocumentProtocol", goods)
        access: AccessResult = await access_service.resolve_access(user, goods_doc)

        if not access.visible or access.level < 2:
            raise PermissionError("Нет права на создание товара")

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
        user: UserProtocol,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """Обновление товара с проверкой доступа, версии и блокировки."""
        if user_id != user.id:
            raise PermissionError("Некорректный пользователь операции")

        updated = await crud_goods.save_with_version(
            db,
            goods_id=goods_id,
            obj_in=obj_in,
            user=user,
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
        user: UserProtocol,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """Мягкое удаление товара с проверкой доступа и блокировки."""
        if user_id != user.id:
            raise PermissionError("Некорректный пользователь операции")

        deleted = await crud_goods.mark_deleted(
            db,
            goods_id=goods_id,
            user=user,
            tenant_id=current_tenant_id,
            user_id=user_id,
            is_superadmin=is_superadmin,
        )

        await self._publish_event(
            db,
            "sales.goods.deleted",
            deleted,
            is_deleted=True,
        )
        return deleted

    async def _publish_event(
        self,
        db: AsyncSession,
        event_type: str,
        goods: SalesGoodsModel,
        *,
        is_deleted: bool = False,
    ) -> None:
        """
        Публикация события изменения товара для репликации.

        Контракт доступа обязателен в каждом событии:
        tenant_id, section_id, author_id, or_tags, and_tags.
        """
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
                "section_id": str(goods.section_id),
                "author_id": str(goods.author_id),
                "or_tags": list(goods.or_tags or []),
                "and_tags": list(goods.and_tags or []),
                "is_deleted": is_deleted,
            },
            ordering_key=f"sales:sales_goods:{goods.id}",
        )


goods_service = GoodsService()