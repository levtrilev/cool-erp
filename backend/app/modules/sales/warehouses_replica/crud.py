"""CRUD для чтения реплики складов в домене sales.

Реплика складов приходит из домена inventory через механизм
core_outbox → core_replication_tasks → handlers.py.

⚠️ Методы записи отсутствуют намеренно:
   единственным источником записи в реплику является репликатор.
   Прямая запись из сервиса sales нарушила бы целостность репликации.

⚠️ Класс не наследует CRUDBase:
   - PK реплики — warehouse_id (не id);
   - нет CreateSchema / UpdateSchema;
   - нет операций create / update / delete.
   Это read-only проекция чужой мастер-таблицы.
"""
import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sales.replica.models import SalesInvWarehousesReplicaModel
from app.modules.sales.replica.schemas import SalesInvWarehousesReferenceItemSchema


class CRUDSalesInvWarehousesReplica:
    """Read-only CRUD для реплики складов из домена inventory."""

    def __init__(self) -> None:
        self.model: type[SalesInvWarehousesReplicaModel] = (
            SalesInvWarehousesReplicaModel
        )

    # ==================================================================
    # СПИСОК РЕПЛИК
    # ==================================================================

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[SalesInvWarehousesReplicaModel], int]:
        """
        Список реплик складов с мультивенантной изоляцией (Правило №26).

        Параметры:
            db: сессия БД
            tenant_id: текущая организация
            is_superadmin: суперадмин видит все организации
            skip: смещение пагинации
            limit: размер страницы
            search: поиск по названию (ILIKE)
            include_deleted: включать мягко удалённые реплики

        Возвращает:
            (список реплик, общее количество)
        """
        model: type[SalesInvWarehousesReplicaModel] = self.model

        stmt: Select[tuple[SalesInvWarehousesReplicaModel]] = select(model)
        count_stmt = select(func.count()).select_from(model)

        # ✅ Правило №26: фильтрация по tenant_id на уровне SQL
        if not is_superadmin:
            stmt = stmt.where(model.tenant_id == tenant_id)
            count_stmt = count_stmt.where(model.tenant_id == tenant_id)

        # ✅ По умолчанию мягко удалённые реплики не показываются
        if not include_deleted:
            stmt = stmt.where(model.is_deleted.is_(False))
            count_stmt = count_stmt.where(model.is_deleted.is_(False))

        if search:
            pattern: str = f"%{search}%"
            stmt = stmt.where(model.name.ilike(pattern))
            count_stmt = count_stmt.where(model.name.ilike(pattern))

        total: int = (await db.execute(count_stmt)).scalar_one() or 0

        stmt = (
            stmt.order_by(model.name.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        items: list[SalesInvWarehousesReplicaModel] = list(
            result.scalars().all()
        )
        return items, total

    # ==================================================================
    # ОДНА РЕПЛИКА ПО ID
    # ==================================================================

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        warehouse_id: uuid.UUID,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesInvWarehousesReplicaModel | None:
        """
        Получение реплики склада по ID оригинала.

        ⚠️ Ищем по warehouse_id (PK реплики), а не по id.
        """
        model: type[SalesInvWarehousesReplicaModel] = self.model

        stmt: Select[tuple[SalesInvWarehousesReplicaModel]] = select(model).where(
            model.warehouse_id == warehouse_id
        )

        if not is_superadmin:
            stmt = stmt.where(model.tenant_id == tenant_id)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ==================================================================
    # ЭЛЕМЕНТЫ ДЛЯ СПРАВОЧНИКА ФРОНТЕНДА
    # ==================================================================

    async def get_reference_items(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> list[SalesInvWarehousesReferenceItemSchema]:
        """
        Все активные реплики складов в формате ReferenceItem.

        Используется для заполнения ReferenceSelect во вкладках
        документов домена sales (например, выбор склада для отгрузки).

        ⚠️ warehouse_id приводится к str в поле id —
        это формат, который ожидает универсальный справочник фронтенда.
        """
        model: type[SalesInvWarehousesReplicaModel] = self.model

        stmt: Select[tuple[SalesInvWarehousesReplicaModel]] = (
            select(model)
            .where(model.is_deleted.is_(False))
            .order_by(model.name.asc())
        )

        if not is_superadmin:
            stmt = stmt.where(model.tenant_id == tenant_id)

        result = await db.execute(stmt)
        replicas: list[SalesInvWarehousesReplicaModel] = list(
            result.scalars().all()
        )

        return [
            SalesInvWarehousesReferenceItemSchema(
                id=str(replica.warehouse_id),
                name=replica.name,
            )
            for replica in replicas
        ]


# ✅ Единый экземпляр, как в остальных CRUD модуля
crud_sales_inv_warehouses_replica = CRUDSalesInvWarehousesReplica()