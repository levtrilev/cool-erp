"""Сервис регионов с публикацией событий репликации."""
import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.outbox import outbox
from app.modules.sales.regions.crud import crud_region
from app.modules.sales.regions.models import SalesRegionModel
from app.modules.sales.regions.schemas import (
    SalesRegionCreateSchema,
    SalesRegionUpdateSchema,
)

logger = logging.getLogger(__name__)


class RegionService:
    """Публичный сервис подмодуля regions домена sales."""

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: SalesRegionCreateSchema,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesRegionModel:
        """Создание региона + публикация события для репликации."""
        tenant_id = obj_in.tenant_id or current_tenant_id
        if not is_superadmin and tenant_id != current_tenant_id:
            raise PermissionError("Нет доступа к другой организации")

        data_dict = obj_in.model_dump(exclude_unset=True)
        data_dict["tenant_id"] = tenant_id
        data_dict["author_id"] = user_id
        data_dict["created_by_user_id"] = user_id

        region = SalesRegionModel(**data_dict)
        db.add(region)
        await db.flush()
        await db.refresh(region)

        await self._publish_event(db, "sales.region.created", region)
        return region

    async def update(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        obj_in: SalesRegionUpdateSchema,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesRegionModel:
        """Обновление региона с проверкой блокировок."""
        updated = await crud_region.save_with_version(
            db,
            region_id=region_id,
            obj_in=obj_in,
            tenant_id=current_tenant_id,
            user_id=user_id,
            is_superadmin=is_superadmin,
        )
        await self._publish_event(db, "sales.region.updated", updated)
        return updated

    async def delete(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesRegionModel:
        """Мягкое удаление региона."""
        deleted = await crud_region.mark_deleted(
            db,
            region_id=region_id,
            tenant_id=current_tenant_id,
            user_id=user_id,
            is_superadmin=is_superadmin,
        )
        # await outbox.publish(
        #     db,
        #     event_type="sales.region.deleted",
        #     source_domain="sales",
        #     aggregate_type="sales_regions",
        #     aggregate_id=region_id,
        #     payload={"id": str(region_id), "is_deleted": True},
        #     ordering_key=f"sales:sales_regions:{region_id}",
        # )
        await outbox.publish(
            db,
            event_type="sales.region.deleted",
            source_domain="sales",
            aggregate_type="sales_regions",
            aggregate_id=region_id,
            payload={
                "id": str(region_id),
                "is_deleted": True,
            },
            ordering_key=f"sales:sales_regions:{region_id}",
        )
        return deleted

    # ==================================================================
    # ПУБЛИКАЦИЯ СОБЫТИЙ ДЛЯ РЕПЛИКАЦИИ
    # ==================================================================

    # async def _publish_event(
    #     self,
    #     db: AsyncSession,
    #     event_type: str,
    #     region: SalesRegionModel,
    # ) -> None:
    #     """Публикация события изменения региона для репликации."""
    #     await outbox.publish(
    #         db,
    #         event_type=event_type,
    #         source_domain="sales",
    #         aggregate_type="sales_regions",
    #         aggregate_id=region.id,
    #         payload={
    #             "id": str(region.id),
    #             "name": region.name,
    #             "capital": region.capital,
    #             "code": region.code,
    #             "area": region.area,
    #             "tenant_id": str(region.tenant_id),
    #             "is_deleted": False,
    #         },
    #         ordering_key=f"sales:sales_regions:{region.id}",
    #     )

    # ==================================================================
    # ПУБЛИКАЦИЯ СОБЫТИЙ ДЛЯ РЕПЛИКАЦИИ
    # ✅ Обновлён: включает ПОЛНЫЙ КОНТРАКТ ДОСТУПА (§3.3, раздел 4.10 ТЗ)
    # ==================================================================

    async def _publish_event(
        self,
        db: AsyncSession,
        event_type: str,
        region: SalesRegionModel,
    ) -> None:
        """Публикация события изменения региона для репликации.

        ⚠️ Payload ОБЯЗАН содержать все 5 полей контракта доступа.
        Без них домен-получатель не сможет вычислить доступ
        через AccessService (ТЗ RBAC/ABAC §8).
        """
        await outbox.publish(
            db,
            event_type=event_type,
            source_domain="sales",
            aggregate_type="sales_regions",
            aggregate_id=region.id,
            payload={
                # Бизнес-данные
                "id": str(region.id),
                "name": region.name,
                "capital": region.capital,
                "code": region.code,
                "area": region.area,
                # ✅ КОНТРАКТ ДОСТУПА (§3.3) — обязателен в каждом событии
                "tenant_id": str(region.tenant_id),
                "section_id": str(region.section_id),
                "author_id": str(region.author_id),
                "or_tags": list(region.or_tags or []),
                "and_tags": list(region.and_tags or []),
                "is_deleted": False,
            },
            ordering_key=f"sales:sales_regions:{region.id}",
        )

region_service = RegionService()