"""CRUD для товаров с блокировками (Правило №40)."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.crud.base import CRUDBase
from app.core.doctypes.document_base import EDITING_LOCK_TIMEOUT_MINUTES
from app.modules.sales.goods.exceptions import (
    GoodsEditingLockedError,
    GoodsNotFoundError,
    GoodsVersionConflictError,
)
from app.modules.sales.goods.models import SalesGoodsModel
from app.modules.sales.goods.schemas import (
    SalesGoodsCreateSchema,
    SalesGoodsUpdateSchema,
)


class CRUDSalesGoods(
    CRUDBase[SalesGoodsModel, SalesGoodsCreateSchema, SalesGoodsUpdateSchema]
):
    """CRUD для товаров с блокировками."""

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[SalesGoodsModel], int]:
        """Список товаров с мультивенантной изоляцией (Правило №26)."""
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
            pattern = f"%{search}%"
            stmt = stmt.where(self.model.name.ilike(pattern))
            count_stmt = count_stmt.where(self.model.name.ilike(pattern))

        total = (await db.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(self.model.name).offset(skip).limit(limit)
        items = list((await db.execute(stmt)).scalars().all())
        return items, total

    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        goods_id: uuid.UUID,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel | None:
        """Получение товара с мультивенантной изоляцией."""
        stmt = select(self.model).where(
            self.model.id == goods_id,
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
        goods_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """Атомарный захват блокировки с учётом таймаута."""
        model = self.model
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)

        # ✅ Правило №40, часть 3.2: РОВНО ДВА условия для захвата
        conditions: list[ColumnElement[bool]] = [
            model.id == goods_id,
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
            goods = await self.get_for_user(
                db,
                goods_id=goods_id,
                tenant_id=tenant_id,
                is_superadmin=is_superadmin,
            )
            if goods is None:
                raise GoodsNotFoundError("Товар не найден")
            raise GoodsEditingLockedError("Товар уже редактируется")

        goods = await self.get_for_user(
            db,
            goods_id=goods_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if goods is None:
            raise GoodsNotFoundError("Товар не найден")

        # ✅ Правило №40, часть 8.1: только flush в CRUD
        await db.flush()
        await db.refresh(goods)
        return goods

    async def release_editing_lock(
        self,
        db: AsyncSession,
        *,
        goods_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """Освобождение блокировки владельцем или суперадмином."""
        goods = await self.get_for_user(
            db,
            goods_id=goods_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if goods is None:
            raise GoodsNotFoundError("Товар не найден")

        # ✅ Правило №40, часть 4.1: освободить может только владелец
        if (
            not is_superadmin
            and goods.editing_by_user_id is not None
            and goods.editing_by_user_id != user_id
        ):
            raise GoodsEditingLockedError(
                "Блокировка принадлежит другому пользователю"
            )

        goods.editing_by_user_id = None
        goods.editing_since = None

        # ✅ Только flush в CRUD (Правило №40, часть 8.1)
        await db.flush()
        await db.refresh(goods)
        return goods

    # ==================================================================
    # СОХРАНЕНИЕ С ВЕРСИЕЙ (Правило №40, часть 5)
    # ==================================================================

    async def save_with_version(
        self,
        db: AsyncSession,
        *,
        goods_id: uuid.UUID,
        obj_in: SalesGoodsUpdateSchema,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """Сохранение с проверкой обеих блокировок."""
        model = self.model
        goods = await self.get_for_user(
            db,
            goods_id=goods_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if goods is None:
            raise GoodsNotFoundError("Товар не найден")

        # ✅ Правило №40, часть 5.2: ЖЁСТКАЯ проверка пессимистической блокировки
        if (
            goods.editing_by_user_id is not None
            and goods.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if goods.editing_since is None or goods.editing_since > cutoff:
                raise GoodsEditingLockedError(
                    "Товар заблокирован другим пользователем для редактирования"
                )

        # ✅ Правило №40, часть 5.2: атомарный UPDATE с оптимистической блокировкой
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
            model.id == goods_id,
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
            raise GoodsVersionConflictError(
                "Товар изменён другим пользователем. Обновите данные."
            )

        # ✅ Только flush в CRUD (Правило №40, часть 8.1)
        await db.flush()
        await db.refresh(goods)
        return goods

    # ==================================================================
    # МЯГКОЕ УДАЛЕНИЕ (Правило №40, часть 6)
    # ==================================================================

    async def mark_deleted(
        self,
        db: AsyncSession,
        *,
        goods_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """Мягкое удаление с проверкой блокировки."""
        goods = await self.get_for_user(
            db,
            goods_id=goods_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if goods is None:
            raise GoodsNotFoundError("Товар не найден")

        # ✅ Правило №40, часть 6.1: проверка блокировки перед удалением
        if (
            goods.editing_by_user_id is not None
            and goods.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if goods.editing_since is None or goods.editing_since > cutoff:
                raise GoodsEditingLockedError(
                    "Товар заблокирован другим пользователем и не может быть удалён"
                )

        goods.deleted_at = datetime.now(timezone.utc)
        goods.deleted_by_user_id = user_id
        goods.updated_by_user_id = user_id
        goods.editing_by_user_id = None
        goods.editing_since = None
        goods.version = goods.version + 1

        # ✅ Только flush в CRUD (Правило №40, часть 8.1)
        await db.flush()
        await db.refresh(goods)
        return goods


crud_goods = CRUDSalesGoods(SalesGoodsModel)