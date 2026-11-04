"""Сервис складов с публикацией событий репликации и контролем доступа."""

import uuid
import logging
from typing import TYPE_CHECKING, cast as typing_cast # pyright: ignore[reportUnusedImport]
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.outbox import outbox
from app.modules.inventory.warehouses.crud import crud_warehouse
from app.modules.inventory.warehouses.models import InvWarehouseModel
from app.modules.inventory.warehouses.schemas import (
    InvWarehouseCreateSchema,
    InvWarehouseUpdateSchema,
)
from app.core.access.schemas import AccessResult, UserProtocol
from app.core.access.service import AccessService, DocumentProtocol

# ✅ Избегаем циклического импорта — UserModel нужен только для типизации
# if TYPE_CHECKING:
#     from app.core.users.models import UserModel

logger = logging.getLogger(__name__)


class WarehouseService:
    """Публичный сервис домена inventory."""

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: InvWarehouseCreateSchema,
        user: UserProtocol,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        """Создание склада + публикация события для репликации."""
        if not is_superadmin and obj_in.tenant_id != current_tenant_id:
            raise PermissionError("Нет доступа к другой организации")

        data_dict = obj_in.model_dump(exclude_unset=True)
        # ✅ author_id и created_by_user_id — из user
        data_dict["author_id"] = user.id
        data_dict["created_by_user_id"] = user.id

        warehouse = InvWarehouseModel(**data_dict)

        # ✅ КРИТИЧНО: Проверка права на создание через AccessService

        access_service = AccessService(db)
        wh_doc: DocumentProtocol = typing_cast("DocumentProtocol", warehouse)
        access: AccessResult = await access_service.resolve_access(user, wh_doc)

        if not access.visible or access.level < 2:
            raise PermissionError("Нет права на создание склада")

        db.add(warehouse)
        await db.flush()
        await db.refresh(warehouse)

        await self._publish_event(db, "inventory.warehouse.created", warehouse)
        return warehouse

    async def update(
        self,
        db: AsyncSession,
        *,
        warehouse_id: uuid.UUID,
        obj_in: InvWarehouseUpdateSchema,
        user: UserProtocol,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        """Обновление склада с проверкой блокировок и контроля доступа."""
        updated = await crud_warehouse.save_with_version(
            db,
            warehouse_id=warehouse_id,
            obj_in=obj_in,
            user=user,
            tenant_id=current_tenant_id,
            user_id=user_id,
            is_superadmin=is_superadmin,
        )
        await self._publish_event(db, "inventory.warehouse.updated", updated)
        return updated

    async def delete(
        self,
        db: AsyncSession,
        *,
        warehouse_id: uuid.UUID,
        user: UserProtocol,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        """Мягкое удаление склада с проверкой блокировки и контроля доступа."""
        deleted = await crud_warehouse.mark_deleted(
            db,
            warehouse_id=warehouse_id,
            user=user,  # ✅ НОВОЕ: передача user для контроля доступа
            tenant_id=current_tenant_id,
            user_id=user_id,
            is_superadmin=is_superadmin,
        )
        await outbox.publish(
            db,
            event_type="inventory.warehouse.deleted",
            source_domain="inventory",
            aggregate_type="inv_warehouses",
            aggregate_id=warehouse_id,
            payload={"id": str(warehouse_id), "is_deleted": True},
            ordering_key=f"inventory:inv_warehouses:{warehouse_id}",
        )
        return deleted

    # ==================================================================
    # ПУБЛИКАЦИЯ СОБЫТИЙ ДЛЯ РЕПЛИКАЦИИ
    # ==================================================================
    async def _publish_event(
        self,
        db: AsyncSession,
        event_type: str,
        warehouse: InvWarehouseModel,
    ) -> None:
        """
        Публикация события изменения склада для репликации.

        ⚠️ КРИТИЧНО (ТЗ репликации §4.10.4):
        payload ОБЯЗАН содержать все 5 полей контракта доступа:
        tenant_id, section_id, author_id, or_tags, and_tags.
        """
        await outbox.publish(
            db,
            event_type=event_type,
            source_domain="inventory",
            aggregate_type="inv_warehouses",
            aggregate_id=warehouse.id,
            payload={
                # Бизнес-данные
                "id": str(warehouse.id),
                "name": warehouse.name,
                "description": warehouse.description,
                # ✅ КОНТРАКТ ДОСТУПА (§3.3) — все 5 полей обязательны
                "tenant_id": str(warehouse.tenant_id),
                "section_id": str(warehouse.section_id),
                "author_id": str(warehouse.author_id),
                "or_tags": list(warehouse.or_tags or []),
                "and_tags": list(warehouse.and_tags or []),
                "is_deleted": False,
            },
            ordering_key=f"inventory:inv_warehouses:{warehouse.id}",
        )


warehouse_service = WarehouseService()
