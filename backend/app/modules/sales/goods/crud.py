"""CRUD для товаров с блокировками (Правило №40) и контролем доступа."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import cast as typing_cast

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.access.schemas import AccessResult, UserProtocol
from app.core.access.service import AccessService, DocumentProtocol
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
    """CRUD для товаров с блокировками и контролем доступа."""

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[SalesGoodsModel], int]:
        """
        Список товаров с контролем доступа через AccessService.

        Важно:
        - Не фильтруем список только по tenant_id.
        - Видимость определяет AccessService.build_access_filter().
        - Если фильтр None — пользователь не видит ни одной записи.
        """
        model = self.model
        access_service = AccessService(db)

        access_filter = await access_service.build_access_filter(user, model)
        if access_filter is None:
            return [], 0

        base_where: ColumnElement[bool] = model.deleted_at.is_(None)

        stmt = select(model).where(base_where, access_filter)
        count_stmt = (
            select(func.count())
            .select_from(model)
            .where(base_where, access_filter)
        )

        if search:
            pattern: str = f"%{search}%"
            search_condition: ColumnElement[bool] = model.name.ilike(pattern)
            stmt = stmt.where(search_condition)
            count_stmt = count_stmt.where(search_condition)

        total: int = (await db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(model.name.asc()).offset(skip).limit(limit)

        items: list[SalesGoodsModel] = list(
            (await db.execute(stmt)).scalars().all()
        )
        return items, total

    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        goods_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel | None:
        """
        Получение товара с проверкой видимости.

        Если пользователь не имеет права чтения, возвращаем None.
        Роутер должен превратить это в 404.
        """
        model = self.model

        stmt = select(model).where(
            model.id == goods_id,
            model.deleted_at.is_(None),
        )

        if not is_superadmin:
            stmt = stmt.where(model.tenant_id == tenant_id)

        goods = (await db.execute(stmt)).scalar_one_or_none()
        if goods is None:
            return None

        access_service = AccessService(db)

        # Правило №45: каст экземпляра модели к DocumentProtocol в точке вызова.
        # Причина: Pyright не сопоставляет SQLAlchemy Mapped[...] дескрипторы
        # с аннотациями значений протокола. Runtime-совместимость обеспечена
        # миксинами документного контракта.
        goods_doc: DocumentProtocol = typing_cast("DocumentProtocol", goods)
        access: AccessResult = await access_service.resolve_access(user, goods_doc)

        if not access.visible:
            return None

        return goods

    async def acquire_editing_lock(
        self,
        db: AsyncSession,
        *,
        goods_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """Атомарный захват блокировки редактирования."""
        model = self.model

        goods = await self.get_for_user(
            db,
            goods_id=goods_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if goods is None:
            raise GoodsNotFoundError("Товар не найден")

        access_service = AccessService(db)

        # Правило №45: каст нужен только для экземпляра документа.
        goods_doc: DocumentProtocol = typing_cast("DocumentProtocol", goods)
        access: AccessResult = await access_service.resolve_access(user, goods_doc)

        # Блокировка нужна только для редактирования.
        # Пользователь с read-only доступом не должен захватывать lock.
        if access.level < 2:
            raise GoodsNotFoundError("Товар не найден")

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)

        conditions: list[ColumnElement[bool]] = [
            model.id == goods_id,
            model.deleted_at.is_(None),
            or_(
                model.editing_by_user_id.is_(None),
                model.editing_since < cutoff,
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
                user=user,
                tenant_id=tenant_id,
                is_superadmin=is_superadmin,
            )
            if goods is None:
                raise GoodsNotFoundError("Товар не найден")

            raise GoodsEditingLockedError("Товар уже редактируется")

        goods = await self.get_for_user(
            db,
            goods_id=goods_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if goods is None:
            raise GoodsNotFoundError("Товар не найден")

        await db.flush()
        await db.refresh(goods)
        return goods

    async def release_editing_lock(
        self,
        db: AsyncSession,
        *,
        goods_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """Освобождение блокировки владельцем или суперадмином."""
        goods = await self.get_for_user(
            db,
            goods_id=goods_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if goods is None:
            raise GoodsNotFoundError("Товар не найден")

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

        await db.flush()
        await db.refresh(goods)
        return goods

    async def save_with_version(
        self,
        db: AsyncSession,
        *,
        goods_id: uuid.UUID,
        obj_in: SalesGoodsUpdateSchema,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """Сохранение с проверкой версии, блокировки и права изменения."""
        model = self.model

        goods = await self.get_for_user(
            db,
            goods_id=goods_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if goods is None:
            raise GoodsNotFoundError("Товар не найден")

        access_service = AccessService(db)

        # Правило №45: каст экземпляра модели к DocumentProtocol.
        goods_doc: DocumentProtocol = typing_cast("DocumentProtocol", goods)
        access: AccessResult = await access_service.resolve_access(user, goods_doc)

        # Изменение разрешено только при уровне >= 2.
        if access.level < 2:
            raise GoodsNotFoundError("Товар не найден")

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

        values: dict[str, object] = obj_in.model_dump(
            exclude_unset=True,
            exclude={"version"},
        )
        values["version"] = model.version + 1
        values["updated_at"] = func.now()
        values["updated_by_user_id"] = user_id
        values["editing_by_user_id"] = None
        values["editing_since"] = None

        conditions: list[ColumnElement[bool]] = [
            model.id == goods_id,
            model.version == obj_in.version,
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

        await db.flush()
        await db.refresh(goods)
        return goods

    async def mark_deleted(
        self,
        db: AsyncSession,
        *,
        goods_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesGoodsModel:
        """Мягкое удаление с проверкой блокировки и can_delete."""
        goods = await self.get_for_user(
            db,
            goods_id=goods_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if goods is None:
            raise GoodsNotFoundError("Товар не найден")

        access_service = AccessService(db)

        # Правило №45: каст экземпляра модели к DocumentProtocol.
        goods_doc: DocumentProtocol = typing_cast("DocumentProtocol", goods)
        access: AccessResult = await access_service.resolve_access(user, goods_doc)

        if not access.can_delete:
            raise GoodsNotFoundError("Товар не найден")

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

        await db.flush()
        await db.refresh(goods)
        return goods


crud_goods = CRUDSalesGoods(SalesGoodsModel)