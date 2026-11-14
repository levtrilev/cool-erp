"""CRUD для товаров с блокировками (Правило №40) и контролем доступа."""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import cast as typing_cast

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.access.schemas import AccessResult, UserProtocol
from app.core.access.service import AccessService, DocumentProtocol
from app.core.crud.base import CRUDBase
from app.core.doctypes.document_base import EDITING_LOCK_TIMEOUT_MINUTES
from app.core.schemas import SortOrder
from app.modules.sales.goods.exceptions import (
    GoodsEditingLockedError,
    GoodsNotFoundError,
    GoodsPermissionError,
    GoodsVersionConflictError,
)
from app.modules.sales.goods.models import SalesGoodsModel
from app.modules.sales.goods.schemas import (
    SalesGoodsCreateSchema,
    SalesGoodsSortField,
    SalesGoodsUpdateSchema,
)
from app.modules.sales.item_types.models import SalesItemTypeModel


class CRUDSalesGoods(
    CRUDBase[SalesGoodsModel, SalesGoodsCreateSchema, SalesGoodsUpdateSchema]
):
    """CRUD для товаров с блокировками и контролем доступа."""

# backend/app/modules/sales/goods/crud.py (полная замена get_multi)
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
        sort_by: SalesGoodsSortField | None = None,
        sort_order: SortOrder = SortOrder.ASC,
        filter_name: str | None = None,
        filter_item_type_name: str | None = None,
        filter_updated_at: date | None = None,
    ) -> tuple[list[SalesGoodsModel], int]:
        """
        Список товаров с контролем доступа, сортировкой и фильтрами на SQL.
        Join к sales_item_types — внутри домена sales (матрица доступа §1.3),
        используется для сортировки/фильтра по наименованию типа.
        Left join не меняет число строк (связь многие-к-одному).
        """
        model = self.model
        access_service = AccessService(db)
        access_filter = await access_service.build_access_filter(user, model)
        if access_filter is None:
            return [], 0

        base_where: ColumnElement[bool] = model.deleted_at.is_(None)
        item_type_join = (
            SalesItemTypeModel,
            model.item_type_id == SalesItemTypeModel.id,
        )
        stmt = (
            select(model)
            .outerjoin(*item_type_join)
            .where(base_where, access_filter)
        )
        count_stmt = (
            select(func.count())
            .select_from(model)
            .outerjoin(*item_type_join)
            .where(base_where, access_filter)
        )

        if search:
            pattern: str = f"%{search}%"
            search_condition: ColumnElement[bool] = or_(
                model.name.ilike(pattern),
                model.description.ilike(pattern),
                model.doc_number.ilike(pattern),
            )
            stmt = stmt.where(search_condition)
            count_stmt = count_stmt.where(search_condition)

        if filter_name:
            cond = model.name.ilike(f"%{filter_name}%")
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_item_type_name:
            cond = SalesItemTypeModel.name.ilike(f"%{filter_item_type_name}%")
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_updated_at is not None:
            # ✅ Sargable-фильтр диапазона за день (индекс пригоден)
            day_start = datetime.combine(
                filter_updated_at, time.min, tzinfo=timezone.utc
            )
            day_end = day_start + timedelta(days=1)
            cond = and_(
                model.updated_at >= day_start,
                model.updated_at < day_end,
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        total: int = (await db.execute(count_stmt)).scalar_one()

        ascending: bool = sort_order == SortOrder.ASC
        if sort_by == SalesGoodsSortField.item_type_name:
            order_expr = (
                SalesItemTypeModel.name.asc()
                if ascending
                else SalesItemTypeModel.name.desc()
            ).nulls_last()
            stmt = stmt.order_by(order_expr)
        elif sort_by == SalesGoodsSortField.updated_at:
            stmt = stmt.order_by(
                model.updated_at.asc() if ascending else model.updated_at.desc()
            )
        else:
            stmt = stmt.order_by(
                model.name.asc() if ascending else model.name.desc()
            )
        stmt = stmt.order_by(model.id.asc())
        stmt = stmt.offset(skip).limit(limit)

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
            raise GoodsPermissionError("Нет права на редактирование товара")

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
            raise GoodsPermissionError("Нет права на редактирование товара")

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