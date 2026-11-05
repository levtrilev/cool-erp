"""CRUD для регионов с использованием AccessService (ТЗ §8.2).

✅ АРХИТЕКТУРНОЕ РЕШЕНИЕ:
Вся логика вычисления доступа делегирована AccessService:
- build_access_filter() — для списков (фильтрация на уровне SQL)
- resolve_access()      — для одного документа (полная проверка)

Это обеспечивает:
- Кросс-организационную видимость для раздела «Общий» (ТЗ §3.1.2.1, §4.3)
- Потолок уровня 1 для не-суперадмина в «Общем» (ТЗ §4.3.3)
- Тег-проверку (ТЗ §6)
- Проверку ролей и permissions (ТЗ §3.2, §3.4)
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, cast as typing_cast

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.access.schemas import (
    ACCESS_LEVEL_AUTHOR,  # pyright: ignore[reportUnusedImport]
    AccessResult,
    UserProtocol,
)
from app.core.access.service import AccessService, DocumentProtocol
from app.core.crud.base import CRUDBase
from app.core.doctypes.document_base import EDITING_LOCK_TIMEOUT_MINUTES
from app.modules.sales.regions.exceptions import (
    RegionEditingLockedError,
    RegionNotFoundError,
    RegionVersionConflictError,
)
from app.modules.sales.regions.models import SalesRegionModel
from app.modules.sales.regions.schemas import (
    SalesRegionCreateSchema,
    SalesRegionUpdateSchema,
)


class CRUDRegion(
    CRUDBase[SalesRegionModel, SalesRegionCreateSchema, SalesRegionUpdateSchema]
):
    """CRUD для регионов с делегированием проверки доступа в AccessService."""

    # ==================================================================
    # СПИСОК С ФИЛЬТРАЦИЕЙ ЧЕРЕЗ AccessService.build_access_filter
    # ==================================================================

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        user: UserProtocol,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[SalesRegionModel], int]:
        """
        Список регионов с фильтрацией по полному алгоритму ТЗ §8.2.

        ✅ Использует AccessService.build_access_filter(), который:
        - ШАГ 1: Тенант ИЛИ платформенный раздел ИЛИ суперадмин
        - ШАГИ 2-4: Роли пользователя с разделами и permissions
        - ШАГИ 5-7: Тег-проверка на уровне SQL
        - НЕ применяет потолок уровня (это для одного документа)

        Фильтрация выполняется на уровне SQL (ТЗ §3.1.4).
        """
        model: type[SalesRegionModel] = self.model

        # ✅ Делегируем построение фильтра в AccessService
        access_service = AccessService(db)
        access_filter: ColumnElement[bool] | None = (
            await access_service.build_access_filter(user, model)
        )

        # Если фильтр None — у пользователя нет доступа ни к одному региону
        # (ТЗ §2.2: безопасность по умолчанию)
        if access_filter is None:
            return [], 0

        stmt: Select[tuple[SalesRegionModel]] = select(model).where(
            model.deleted_at.is_(None),
            access_filter,  # ✅ SQL-фильтр из AccessService
        )
        count_stmt = (
            select(func.count())
            .select_from(model)
            .where(
                model.deleted_at.is_(None),
                access_filter,
            )
        )

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
        stmt = stmt.order_by(model.name.asc()).offset(skip).limit(limit)
        items: list[SalesRegionModel] = list((await db.execute(stmt)).scalars().all())
        return items, total

    # ==================================================================
    # ОДИН ДОКУМЕНТ С ПОЛНОЙ ПРОВЕРКОЙ ЧЕРЕЗ AccessService.resolve_access
    # ==================================================================

    # async def get_for_user(
    #     self,
    #     db: AsyncSession,
    #     *,
    #     region_id: uuid.UUID,
    #     user: UserProtocol,
    # ) -> SalesRegionModel | None:
    #     """
    #     Получение одного региона с полной проверкой доступа.

    #     ✅ Использует AccessService.resolve_access(), который выполняет
    #     все 9 шагов алгоритма ТЗ §8.2, включая:
    #     - Потолок уровня 1 для платформенного раздела (§4.3.3)
    #     - Тег-проверку (§6)
    #     - Делегирование (§11, когда будет реализовано)

    #     Возвращает None, если документ не существует для пользователя
    #     (ТЗ §2.3, §2.6: запись не возвращается, не находится поиском).
    #     """
    #     model: type[SalesRegionModel] = self.model

    #     # Загружаем регион
    #     stmt: Select[tuple[SalesRegionModel]] = (
    #         select(model)
    #         .where(
    #             model.id == region_id,
    #             model.deleted_at.is_(None),
    #         )
    #     )
    #     result = await db.execute(stmt)
    #     region = result.scalar_one_or_none()

    #     if region is None:
    #         return None

    #     # ✅ Делегируем проверку доступа в AccessService
    #     access_service = AccessService(db)
    #     access_result: AccessResult = await access_service.resolve_access(
    #         user, region
    #     )

    #     # ТЗ §2.3: нет права на чтение ⇒ запись не существует
    #     if not access_result.visible:
    #         return None

    #     return region

    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        user: UserProtocol,
    ) -> SalesRegionModel | None:
        """
        Получение одного региона с полной проверкой доступа.

        ✅ Использует AccessService.resolve_access() с DocumentProtocolV2.
        typing.cast не требуется — протокол с @property совместим
        с дескрипторами Mapped[...] модели.
        """
        model: type[SalesRegionModel] = self.model

        stmt: Select[tuple[SalesRegionModel]] = select(model).where(
            model.id == region_id,
            model.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        region = result.scalar_one_or_none()

        if region is None:
            return None

        # ✅ Передаём модель напрямую — она совместима с DocumentProtocolV2
        access_service = AccessService(db)
        region_doc: DocumentProtocol = typing_cast(DocumentProtocol, region)
        access_result: AccessResult = await access_service.resolve_access(user, region_doc)

        # ТЗ §2.3: нет права на чтение ⇒ запись не существует
        if not access_result.visible:
            return None

        return region

    # ==================================================================
    # ПРОВЕРКА ПРАВА НА РЕДАКТИРОВАНИЕ (для роутера)
    # ==================================================================
    # async def check_edit_access(
    #     self,
    #     db: AsyncSession,
    #     *,
    #     region_id: uuid.UUID,
    #     user: UserProtocol,
    # ) -> AccessResult | None:
    #     """
    #     Проверка права на редактирование региона.

    #     Возвращает AccessResult, если документ видим.
    #     Возвращает None, если документ не существует для пользователя.

    #     Роутер использует access_result.level для определения
    #     возможности редактирования:
    #     - level >= ACCESS_LEVEL_AUTHOR (2) → может редактировать
    #     - level < ACCESS_LEVEL_AUTHOR → только чтение (ТЗ §5.4)
    #     """
    #     model: type[SalesRegionModel] = self.model

    #     stmt: Select[tuple[SalesRegionModel]] = (
    #         select(model)
    #         .where(
    #             model.id == region_id,
    #             model.deleted_at.is_(None),
    #         )
    #     )
    #     result = await db.execute(stmt)
    #     region = result.scalar_one_or_none()

    #     if region is None:
    #         return None

    #     access_service = AccessService(db)
    #     return await access_service.resolve_access(user, region)

    async def check_edit_access(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        user: UserProtocol,
    ) -> AccessResult | None:
        """Проверка права на редактирование региона."""
        model: type[SalesRegionModel] = self.model

        stmt: Select[tuple[SalesRegionModel]] = select(model).where(
            model.id == region_id,
            model.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        region = result.scalar_one_or_none()

        if region is None:
            return None

        access_service = AccessService(db)
        # ✅ typing.cast — обход ограничения типизации протоколов с дескрипторами
        region_doc: DocumentProtocol = typing_cast("DocumentProtocol", region)
        return await access_service.resolve_access(user, region_doc)

    # ==================================================================
    # БЛОКИРОВКИ (Правило №40, часть 3-4) — без изменений
    # ==================================================================

    async def acquire_editing_lock(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        user: UserProtocol,
    ) -> SalesRegionModel:
        """Атомарный захват блокировки с учётом таймаута."""
        model = self.model
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)

        # ✅ Правило №40, часть 3.2: РОВНО ДВА условия для захвата
        conditions: list[ColumnElement[bool]] = [
            model.id == region_id,
            model.deleted_at.is_(None),
            or_(
                model.editing_by_user_id.is_(None),  # ✅ свободно
                model.editing_since < cutoff,  # ✅ истекло
            ),
        ]

        stmt = (
            update(model)
            .where(*conditions)
            .values(editing_by_user_id=user.id, editing_since=now)
            .returning(model.id)
        )
        locked_id = (await db.execute(stmt)).scalar_one_or_none()

        if locked_id is None:
            region = await self.get_for_user(db, region_id=region_id, user=user)
            if region is None:
                raise RegionNotFoundError("Регион не найден")
            raise RegionEditingLockedError("Регион уже редактируется")

        region = await self.get_for_user(db, region_id=region_id, user=user)
        if region is None:
            raise RegionNotFoundError("Регион не найден")

        # ✅ Только flush в CRUD (Правило №40, часть 8.1)
        await db.flush()
        await db.refresh(region)
        return region

    async def release_editing_lock(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        user: UserProtocol,
    ) -> SalesRegionModel:
        """Освобождение блокировки владельцем или суперадмином."""
        region = await self.get_for_user(db, region_id=region_id, user=user)
        if region is None:
            raise RegionNotFoundError("Регион не найден")

        # ✅ Правило №40, часть 4.1: освободить может только владелец
        if (
            not user.is_superadmin
            and region.editing_by_user_id is not None
            and region.editing_by_user_id != user.id
        ):
            raise RegionEditingLockedError(
                "Блокировка принадлежит другому пользователю"
            )

        region.editing_by_user_id = None
        region.editing_since = None

        await db.flush()
        await db.refresh(region)
        return region

    # ==================================================================
    # СОХРАНЕНИЕ С ВЕРСИЕЙ (Правило №40, часть 5) — без изменений
    # ==================================================================

    async def save_with_version(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        obj_in: SalesRegionUpdateSchema,
        user: UserProtocol,
    ) -> SalesRegionModel:
        """Сохранение с проверкой обеих блокировок."""
        model = self.model
        region = await self.get_for_user(db, region_id=region_id, user=user)
        if region is None:
            raise RegionNotFoundError("Регион не найден")

        # ✅ Правило №40, часть 5.2: ЖЁСТКАЯ проверка пессимистической блокировки
        if (
            region.editing_by_user_id is not None
            and region.editing_by_user_id != user.id
            and not user.is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if region.editing_since is None or region.editing_since > cutoff:
                raise RegionEditingLockedError(
                    "Регион заблокирован другим пользователем для редактирования"
                )

        # ✅ Атомарный UPDATE с оптимистической блокировкой
        values: dict[str, Any] = obj_in.model_dump(
            exclude_unset=True, exclude={"version"}
        )
        values["version"] = model.version + 1
        values["updated_at"] = func.now()
        values["updated_by_user_id"] = user.id
        # После сохранения блокировка освобождается
        values["editing_by_user_id"] = None
        values["editing_since"] = None

        conditions: list[ColumnElement[bool]] = [
            model.id == region_id,
            model.version == obj_in.version,  # ✅ оптимистическая блокировка
            model.deleted_at.is_(None),
        ]

        stmt = update(model).where(*conditions).values(**values).returning(model.id)
        updated_id = (await db.execute(stmt)).scalar_one_or_none()

        if updated_id is None:
            raise RegionVersionConflictError(
                "Регион изменён другим пользователем. Обновите данные."
            )

        await db.flush()
        await db.refresh(region)
        return region

    # ==================================================================
    # МЯГКОЕ УДАЛЕНИЕ (Правило №40, часть 6) — без изменений
    # ==================================================================

    async def mark_deleted(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        user: UserProtocol,
    ) -> SalesRegionModel:
        """Мягкое удаление с проверкой блокировки."""
        region = await self.get_for_user(db, region_id=region_id, user=user)
        if region is None:
            raise RegionNotFoundError("Регион не найден")

        # ✅ Правило №40, часть 6.1: проверка блокировки перед удалением
        if (
            region.editing_by_user_id is not None
            and region.editing_by_user_id != user.id
            and not user.is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if region.editing_since is None or region.editing_since > cutoff:
                raise RegionEditingLockedError(
                    "Регион заблокирован другим пользователем и не может быть удалён"
                )

        region.deleted_at = datetime.now(timezone.utc)
        region.deleted_by_user_id = user.id
        region.updated_by_user_id = user.id
        region.editing_by_user_id = None
        region.editing_since = None
        region.version = region.version + 1

        await db.flush()
        await db.refresh(region)
        return region


crud_region = CRUDRegion(SalesRegionModel)
