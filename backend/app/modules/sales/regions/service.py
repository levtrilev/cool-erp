"""Сервис регионов с публикацией событий репликации.

✅ Архитектурные решения:
- Проверка доступа делегирована в AccessService (через CRUD)
- Создание/перемещение в платформенный раздел — только суперадмин (ТЗ §4.3.6)
- Публикация событий с ПОЛНЫМ КОНТРАКТОМ ДОСТУПА (ТЗ репликации §4.10)
- flush в сервисе, commit в роутере (Правило №40, часть 8.1)
"""
import uuid
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access.schemas import UserProtocol
from app.core.events.outbox import outbox
from app.core.sections.models import SectionModel, SectionType
from app.modules.sales.regions.crud import crud_region
from app.modules.sales.regions.models import SalesRegionModel
from app.modules.sales.regions.schemas import (
    SalesRegionCreateSchema,
    SalesRegionUpdateSchema,
)

logger = logging.getLogger(__name__)


class RegionService:
    """Публичный сервис подмодуля regions домена sales."""

    # ==================================================================
    # СОЗДАНИЕ
    # ==================================================================

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: SalesRegionCreateSchema,
        user: UserProtocol,
    ) -> SalesRegionModel:
        """Создание региона + публикация события для репликации."""
        # Определяем целевую организацию
        tenant_id: uuid.UUID = obj_in.tenant_id or user.tenant_id

        # Мульти-арендность: нельзя создавать в чужой организации
        if not user.is_superadmin and tenant_id != user.tenant_id:
            raise PermissionError("Нет доступа к другой организации")

        # ✅ ТЗ §4.3.6: Создание документа в разделе «Общий»
        # доступно только Суперадмину
        await self._check_platform_section_for_write(
            db, section_id=obj_in.section_id, user=user
        )

        # Формируем данные модели
        data_dict = obj_in.model_dump(exclude_unset=True)
        data_dict["tenant_id"] = tenant_id
        data_dict["author_id"] = user.id
        data_dict["created_by_user_id"] = user.id

        region = SalesRegionModel(**data_dict)
        db.add(region)
        # ✅ Только flush в сервисе (Правило №40, часть 8.1)
        await db.flush()
        await db.refresh(region)

        # Публикация события для репликации
        await self._publish_event(db, "sales.region.created", region)
        return region

    # ==================================================================
    # ОБНОВЛЕНИЕ
    # ==================================================================

    async def update(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        obj_in: SalesRegionUpdateSchema,
        user: UserProtocol,
    ) -> SalesRegionModel:
        """Обновление региона с проверкой блокировок."""
        # ✅ ТЗ §4.3.6: Перемещение документа в раздел «Общий»
        # доступно только Суперадмину
        if obj_in.section_id is not None:
            await self._check_platform_section_for_write(
                db, section_id=obj_in.section_id, user=user
            )

        # Обновление с оптимистической и пессимистической блокировками
        # (проверки выполняются внутри crud_region.save_with_version)
        updated = await crud_region.save_with_version(
            db,
            region_id=region_id,
            obj_in=obj_in,
            user=user,
        )

        # Публикация события для репликации
        await self._publish_event(db, "sales.region.updated", updated)
        return updated

    # ==================================================================
    # УДАЛЕНИЕ
    # ==================================================================

    async def delete(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        user: UserProtocol,
    ) -> SalesRegionModel:
        """Мягкое удаление региона."""
        # Удаление с проверкой блокировки
        # (проверки выполняются внутри crud_region.mark_deleted)
        deleted = await crud_region.mark_deleted(
            db,
            region_id=region_id,
            user=user,
        )

        # Публикация события удаления для репликации
        # ✅ Для удаления не нужен полный контракт — только id и флаг
        await outbox.publish(
            db,
            event_type="sales.region.deleted",
            source_domain="sales",
            aggregate_type="sales_regions",
            aggregate_id=region_id,
            payload={"id": str(region_id), "is_deleted": True},
            ordering_key=f"sales:sales_regions:{region_id}",
        )
        return deleted

    # ==================================================================
    # ПРОВЕРКА ПРАВА НА ЗАПИСЬ В ПЛАТФОРМЕННЫЙ РАЗДЕЛ
    # ==================================================================

    async def _check_platform_section_for_write(
        self,
        db: AsyncSession,
        *,
        section_id: uuid.UUID,
        user: UserProtocol,
    ) -> None:
        """
        ТЗ §4.3.6: Создание/перемещение документа в разделе «Общий»
        доступно только Суперадмину.

        Вызывается при создании и при смене раздела на платформенный.

        Исключения:
            ValueError: раздел не найден
            PermissionError: пользователь не суперадмин
        """
        stmt = select(SectionModel).where(SectionModel.id == section_id)
        result = await db.execute(stmt)
        section: SectionModel | None = result.scalar_one_or_none()

        if section is None:
            raise ValueError("Раздел не найден")

        if section.section_type == SectionType.PLATFORM and not user.is_superadmin:
            raise PermissionError(
                "Создание или перемещение документа в разделе «Общий» "
                "доступно только суперадмину (ТЗ §4.3.6)"
            )

    # ==================================================================
    # ПУБЛИКАЦИЯ СОБЫТИЙ ДЛЯ РЕПЛИКАЦИИ
    # ✅ Включает ПОЛНЫЙ КОНТРАКТ ДОСТУПА (ТЗ репликации §4.10)
    # ==================================================================

    async def _publish_event(
        self,
        db: AsyncSession,
        event_type: str,
        region: SalesRegionModel,
    ) -> None:
        """
        Публикация события изменения региона для репликации.

        ⚠️ Payload ОБЯЗАН содержать все 5 полей контракта доступа.
        Без них домен-получатель не сможет вычислить доступ
        через AccessService (ТЗ репликации §4.10.4).
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
                # ✅ Контракт доступа (ТЗ репликации §4.10.4)
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