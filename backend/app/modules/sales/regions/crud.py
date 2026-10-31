"""CRUD для регионов с блокировками (Правило №40)."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

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
    """CRUD для регионов с блокировками."""

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[SalesRegionModel], int]:
        """Список регионов с мультивенантной изоляцией (Правило №26)."""
        stmt = select(self.model).where(self.model.deleted_at.is_(None))
        count_stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.deleted_at.is_(None))
        )

        if not is_superadmin:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
            count_stmt = count_stmt.where(self.model.tenant_id == tenant_id)

        if search:
            pattern: str = f"%{search}%"
            stmt = stmt.where(
                or_(
                    self.model.name.ilike(pattern),
                    self.model.capital.ilike(pattern),
                    self.model.code.ilike(pattern),
                    self.model.area.ilike(pattern),
                )
            )
            count_stmt = count_stmt.where(
                or_(
                    self.model.name.ilike(pattern),
                    self.model.capital.ilike(pattern),
                    self.model.code.ilike(pattern),
                    self.model.area.ilike(pattern),
                )
            )

        total: int = (await db.execute(count_stmt)).scalar_one() or 0
        stmt = stmt.order_by(self.model.name.asc()).offset(skip).limit(limit)
        items: list[SalesRegionModel] = list(
            (await db.execute(stmt)).scalars().all()
        )
        return items, total

    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesRegionModel | None:
        """Получение региона с мультивенантной изоляцией."""
        stmt = select(self.model).where(
            self.model.id == region_id,
            self.model.deleted_at.is_(None),
        )
        if not is_superadmin:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ==================================================================
    # БЛОКИРОВКИ (Правило №40, часть 3)
    # ==================================================================

    async def acquire_editing_lock(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
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
                model.editing_by_user_id.is_(None),   # ✅ свободно
                model.editing_since < cutoff,          # ✅ истекло
            ),
        ]
        if not is_superadmin:
            conditions.append(model.tenant_id == tenant_id)

        stmt = (
            update(model)
            .where(*conditions)
            .values(editing_by_user_id=user_id, editing_since=now)
            .returning(model.id)
        )
        locked_id = (await db.execute(stmt)).scalar_one_or_none()

        if locked_id is None:
            region = await self.get_for_user(
                db,
                region_id=region_id,
                tenant_id=tenant_id,
                is_superadmin=is_superadmin,
            )
            if region is None:
                raise RegionNotFoundError("Регион не найден")
            raise RegionEditingLockedError("Регион уже редактируется")

        region = await self.get_for_user(
            db,
            region_id=region_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
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
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesRegionModel:
        """Освобождение блокировки владельцем или суперадмином."""
        region = await self.get_for_user(
            db,
            region_id=region_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if region is None:
            raise RegionNotFoundError("Регион не найден")

        # ✅ Правило №40, часть 4.1: освободить может только владелец
        if (
            not is_superadmin
            and region.editing_by_user_id is not None
            and region.editing_by_user_id != user_id
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
    # СОХРАНЕНИЕ С ВЕРСИЕЙ (Правило №40, часть 5)
    # ==================================================================

    async def save_with_version(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        obj_in: SalesRegionUpdateSchema,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesRegionModel:
        """Сохранение с проверкой обеих блокировок."""
        model = self.model
        region = await self.get_for_user(
            db,
            region_id=region_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if region is None:
            raise RegionNotFoundError("Регион не найден")

        # ✅ Правило №40, часть 5.2: ЖЁСТКАЯ проверка пессимистической блокировки
        if (
            region.editing_by_user_id is not None
            and region.editing_by_user_id != user_id
            and not is_superadmin
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
        values["updated_by_user_id"] = user_id
        # После сохранения блокировка освобождается
        values["editing_by_user_id"] = None
        values["editing_since"] = None

        conditions: list[ColumnElement[bool]] = [
            model.id == region_id,
            model.version == obj_in.version,  # ✅ оптимистическая блокировка
            model.deleted_at.is_(None),
        ]
        if not is_superadmin:
            conditions.append(model.tenant_id == tenant_id)

        stmt = (
            update(model)
            .where(*conditions)
            .values(**values)
            .returning(model.id)
        )
        updated_id = (await db.execute(stmt)).scalar_one_or_none()

        if updated_id is None:
            raise RegionVersionConflictError(
                "Регион изменён другим пользователем. Обновите данные."
            )

        await db.flush()
        await db.refresh(region)
        return region

    # ==================================================================
    # МЯГКОЕ УДАЛЕНИЕ (Правило №40, часть 6)
    # ==================================================================

    async def mark_deleted(
        self,
        db: AsyncSession,
        *,
        region_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesRegionModel:
        """Мягкое удаление с проверкой блокировки."""
        region = await self.get_for_user(
            db,
            region_id=region_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if region is None:
            raise RegionNotFoundError("Регион не найден")

        # ✅ Правило №40, часть 6.1: проверка блокировки перед удалением
        if (
            region.editing_by_user_id is not None
            and region.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if region.editing_since is None or region.editing_since > cutoff:
                raise RegionEditingLockedError(
                    "Регион заблокирован другим пользователем и не может быть удалён"
                )

        region.deleted_at = datetime.now(timezone.utc)
        region.deleted_by_user_id = user_id
        region.updated_by_user_id = user_id
        region.editing_by_user_id = None
        region.editing_since = None
        region.version = region.version + 1

        await db.flush()
        await db.refresh(region)
        return region


crud_region = CRUDRegion(SalesRegionModel)