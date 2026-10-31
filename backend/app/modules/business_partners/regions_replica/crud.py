"""CRUD для чтения реплики регионов в домене business_partners.

Реплика доступна ТОЛЬКО для чтения.
Запись выполняется исключительно репликатором через handlers.py.
Поэтому методы создания/обновления/удаления отсутствуют намеренно.

Класс НЕ наследует CRUDBase (Правило №31), так как:
- у реплики нет CreateSchema / UpdateSchema;
- нет операций записи;
- PK реплики — region_id (не id).
Это осознанное исключение, а не нарушение.
"""
import uuid
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.business_partners.regions_replica.models import BpSalesRegionsReplicaModel
from app.modules.business_partners.regions_replica.schemas import (
    BpSalesRegionsReplicaReferenceItemSchema,
)


class CRUDBpSalesRegionsReplica:
    """Read-only CRUD для реплики регионов из домена sales."""

    def __init__(self) -> None:
        self.model: type[BpSalesRegionsReplicaModel] = BpSalesRegionsReplicaModel

    # ==================================================================
    # СПИСОК РЕПЛИК С ПАГИНАЦИЕЙ И ПОИСКОМ
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
    ) -> tuple[list[BpSalesRegionsReplicaModel], int]:
        """
        Список реплик регионов с мультивенантной изоляцией (Правило №26).

        Параметры:
            db: сессия БД
            tenant_id: текущая организация
            is_superadmin: суперадмин видит все организации
            skip: смещение пагинации
            limit: размер страницы
            search: поиск по названию, столице, коду, области
            include_deleted: включать мягко удалённые реплики

        Возвращает:
            (список реплик, общее количество)
        """
        model: type[BpSalesRegionsReplicaModel] = self.model

        stmt: Select[tuple[BpSalesRegionsReplicaModel]] = select(model)
        count_stmt = select(func.count()).select_from(model)

        # ✅ Правило №26: фильтрация по тенанту на уровне SQL
        if not is_superadmin:
            stmt = stmt.where(model.tenant_id == tenant_id)
            count_stmt = count_stmt.where(model.tenant_id == tenant_id)

        # По умолчанию мягко удалённые реплики не показываются
        if not include_deleted:
            stmt = stmt.where(model.is_deleted.is_(False))
            count_stmt = count_stmt.where(model.is_deleted.is_(False))

        # Поиск по бизнес-полям
        if search:
            pattern: str = f"%{search}%"
            search_filter = or_(
                model.name.ilike(pattern),
                model.capital.ilike(pattern),
                model.code.ilike(pattern),
                model.area.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total: int = (await db.execute(count_stmt)).scalar_one() or 0
        stmt = (
            stmt.order_by(model.name.asc())
            .offset(skip)
            .limit(limit)
        )
        items: list[BpSalesRegionsReplicaModel] = list(
            (await db.execute(stmt)).scalars().all()
        )
        return items, total

    # ==================================================================
    # ОДНА РЕПЛИКА ПО ID ОРИГИНАЛА
    # ==================================================================

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpSalesRegionsReplicaModel | None:
        """
        Получение реплики региона по ID оригинала.

        ⚠️ Ищем по region_id (PK реплики), а не по id.
        """
        model: type[BpSalesRegionsReplicaModel] = self.model

        stmt: Select[tuple[BpSalesRegionsReplicaModel]] = (
            select(model)
            .where(
                model.region_id == region_id,
                model.is_deleted.is_(False),
            )
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
    ) -> list[BpSalesRegionsReplicaReferenceItemSchema]:
        """
        Все активные реплики регионов в формате ReferenceItem.

        Используется для заполнения ReferenceSelect в форме компании
        (домен business_partners).

        ⚠️ region_id приводится к str в поле id —
        это формат, который ожидает универсальный справочник фронтенда
        (Правило №27: ReferenceItem = { id: string, name: string }).
        """
        model: type[BpSalesRegionsReplicaModel] = self.model

        stmt: Select[tuple[BpSalesRegionsReplicaModel]] = (
            select(model)
            .where(model.is_deleted.is_(False))
            .order_by(model.name.asc())
        )

        if not is_superadmin:
            stmt = stmt.where(model.tenant_id == tenant_id)

        result = await db.execute(stmt)
        replicas: list[BpSalesRegionsReplicaModel] = list(
            result.scalars().all()
        )

        return [
            BpSalesRegionsReplicaReferenceItemSchema(
                id=str(replica.region_id),
                name=replica.name,
            )
            for replica in replicas
        ]

    # ==================================================================
    # ПОЛУЧЕНИЕ С БАЗОВОЙ ПРОВЕРКОЙ ДОСТУПА
    # ==================================================================

    async def get_accessible_by_id(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        user: Any,  # UserModel из сессии; Any — чтобы не создавать циклический импорт
    ) -> BpSalesRegionsReplicaModel | None:
        """
        Получение реплики с базовой проверкой доступа.

        ⚠️ ВАЖНО: этот метод выполняет только базовую фильтрацию:
        - is_deleted = false
        - tenant_id (для не-суперадминов)

        Полная проверка доступа (раздел, теги, уровень) выполняется
        через AccessService.resolve_access() с использованием полей
        контракта доступа, хранящихся в реплике:
            - section_id  (Слой 2: видимость по разделам)
            - author_id   (Слой 5: уровень «автор»)
            - or_tags     (Слой 4: разрешающие теги, ИЛИ)
            - and_tags    (Слой 4: обязательные теги, И)

        Пример использования в сервисе домена:
            replica = await crud_sales_regions_replica.get_accessible_by_id(
                db, region_id=region_id, user=session_user
            )
            if replica is None:
                raise HTTPException(status_code=404, detail="Регион не найден")

            # Полная проверка доступа через AccessService
            access = await access_service.resolve_access(
                user=session_user,
                document=ReplicaAccessView(
                    tenant_id=replica.tenant_id,
                    section_id=replica.section_id,
                    author_id=replica.author_id,
                    or_tags=replica.or_tags,
                    and_tags=replica.and_tags,
                    doctype="regions",
                ),
                now=datetime.now(timezone.utc),
            )
            if not access.visible:
                raise HTTPException(status_code=404, detail="Регион не найден")
        """
        model: type[BpSalesRegionsReplicaModel] = self.model

        stmt: Select[tuple[BpSalesRegionsReplicaModel]] = (
            select(model)
            .where(
                model.region_id == region_id,
                model.is_deleted.is_(False),
            )
        )

        # ✅ Базовая тенантная фильтрация (Слой 1)
        # Для разделов типа «Общий» (платформенных) фильтрация ослабляется —
        # это обрабатывается в AccessService, а не здесь.
        if not getattr(user, "is_superadmin", False):
            stmt = stmt.where(model.tenant_id == user.tenant_id)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()


# ✅ Единый экземпляр, как в остальных CRUD модуля
crud_sales_regions_replica = CRUDBpSalesRegionsReplica()