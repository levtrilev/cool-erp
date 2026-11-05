"""CRUD для чтения реплики регионов в домене business_partners.

Реплика доступна ТОЛЬКО для чтения.
Запись выполняется исключительно репликатором через handlers.py.

✅ Видимость записей реплики фильтруется через
AccessService.build_replica_access_filter (ТЗ §8.2, §3.1.2.1).
"""
import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access.service import AccessService
from app.core.access.schemas import UserProtocol
from app.modules.business_partners.regions_replica.models import BpSalesRegionsReplicaModel
from app.modules.business_partners.regions_replica.schemas import (
    BpSalesRegionsReplicaReferenceItemSchema,
)


class CRUDBpSalesRegionsReplica:
    """Read-only CRUD для реплики регионов из домена sales."""

    def __init__(self) -> None:
        self.model: type[BpSalesRegionsReplicaModel] = BpSalesRegionsReplicaModel

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        user: UserProtocol,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[BpSalesRegionsReplicaModel], int]:
        """
        Список реплик регионов с фильтрацией через AccessService.

        ✅ Использует build_replica_access_filter с doctype="sales_regions"
        (код типа оригинальной мастер-сущности в домене sales).

        Фильтрация выполняет ТЗ §8.2 на уровне SQL:
        - Кросс-организационная видимость для раздела «Общий» (§3.1.2.1)
        - Фильтрация по ролям и permissions (§3.2, §3.4)
        - Тег-проверка (§6)

        Дополнительно фильтрует is_deleted = false
        (мягкое удаление реплики).
        """
        model: type[BpSalesRegionsReplicaModel] = self.model

        # ✅ Делегируем построение фильтра в AccessService
        access_service = AccessService(db)
        access_filter: ColumnElement[bool] | None = (
            await access_service.build_replica_access_filter(
                user,
                model,
                doctype="sales_regions",  # Код типа оригинала
            )
        )

        # Если фильтр None — у пользователя нет доступа ни к одному региону
        if access_filter is None:
            return [], 0

        stmt: Select[tuple[BpSalesRegionsReplicaModel]] = (
            select(model)
            .where(
                model.is_deleted.is_(False),  # Мягкое удаление реплики
                access_filter,                 # Фильтр доступа из AccessService
            )
        )
        count_stmt = (
            select(func.count())
            .select_from(model)
            .where(
                model.is_deleted.is_(False),
                access_filter,
            )
        )

        # Поиск по бизнес-полям
        if search:
            pattern: str = f"%{search}%"
            search_filter = model.name.ilike(pattern)
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total: int = (await db.execute(count_stmt)).scalar_one() or 0
        stmt = stmt.order_by(model.name.asc()).offset(skip).limit(limit)
        items: list[BpSalesRegionsReplicaModel] = list(
            (await db.execute(stmt)).scalars().all()
        )
        return items, total

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        user: UserProtocol,
    ) -> BpSalesRegionsReplicaModel | None:
        """
        Получение реплики региона по ID оригинала.

        ✅ Проверяет доступ через AccessService.resolve_access.
        Реплика не реализует DocumentProtocol, поэтому используется
        ручная проверка через _build_filter_core.
        """
        model: type[BpSalesRegionsReplicaModel] = self.model

        # Строим фильтр доступа
        access_service = AccessService(db)
        access_filter: ColumnElement[bool] | None = (
            await access_service.build_replica_access_filter(
                user,
                model,
                doctype="sales_regions",
            )
        )

        if access_filter is None:
            return None

        stmt: Select[tuple[BpSalesRegionsReplicaModel]] = (
            select(model)
            .where(
                model.region_id == region_id,
                model.is_deleted.is_(False),
                access_filter,
            )
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_reference_items(
        self,
        db: AsyncSession,
        *,
        user: UserProtocol,
    ) -> list[BpSalesRegionsReplicaReferenceItemSchema]:
        """
        Все активные реплики регионов в формате ReferenceItem.
        Используется для заполнения ReferenceSelect в форме компании.
        """
        items, _ = await self.get_multi(
            db,
            user=user,
            skip=0,
            limit=1000,
            search=None,
        )

        return [
            BpSalesRegionsReplicaReferenceItemSchema(
                id=str(replica.region_id),
                name=replica.name,
            )
            for replica in items
        ]


crud_sales_regions_replica = CRUDBpSalesRegionsReplica()