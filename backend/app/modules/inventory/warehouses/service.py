"""Сервис складов с публикацией событий репликации."""
import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.outbox import outbox
from app.modules.inventory.warehouses.crud import (
    crud_warehouse,
    WarehouseNotFoundError, # pyright: ignore[reportUnusedImport]
)
from app.modules.inventory.warehouses.models import InvWarehouseModel
from app.modules.inventory.warehouses.schemas import (
    InvWarehouseCreateSchema,
    InvWarehouseUpdateSchema,
)

logger = logging.getLogger(__name__)


class WarehouseService:
    """Публичный сервис домена inventory."""

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: InvWarehouseCreateSchema,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        """Создание склада + публикация события для репликации."""
        if not is_superadmin and obj_in.tenant_id != current_tenant_id:
            raise PermissionError("Нет доступа к другой организации")

        # ✅ Формируем словарь данных и добавляем обязательные поля контракта,
        # которых нет в CreateSchema (author_id, created_by_user_id).
        # Аналогично GoodsService.create() в домене sales.
        data_dict = obj_in.model_dump(exclude_unset=True)
        data_dict["author_id"] = user_id
        data_dict["created_by_user_id"] = user_id

        warehouse = InvWarehouseModel(**data_dict)
        db.add(warehouse)
        # ✅ Правило №40, часть 8.1: flush в CRUD/сервисе, commit в роутере
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
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        updated = await crud_warehouse.save_with_version(
            db,
            warehouse_id=warehouse_id,
            obj_in=obj_in,
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
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        deleted = await crud_warehouse.mark_deleted(
            db,
            warehouse_id=warehouse_id,
            tenant_id=current_tenant_id,
            user_id=user_id,
            is_superadmin=is_superadmin,
        )
        # await outbox.publish_ordered(
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

    async def _publish_event(
        self,
        db: AsyncSession,
        event_type: str,
        warehouse: InvWarehouseModel,
    ) -> None:
        await outbox.publish(
            db,
            event_type=event_type,
            source_domain="inventory",
            aggregate_type="inv_warehouses",
            aggregate_id=warehouse.id,
            payload={
                "id": str(warehouse.id),
                "name": warehouse.name,
                "description": warehouse.description,
                "tenant_id": str(warehouse.tenant_id),
                "is_deleted": False,
            },
            ordering_key=f"inventory:inv_warehouses:{warehouse.id}",
        )


warehouse_service = WarehouseService()