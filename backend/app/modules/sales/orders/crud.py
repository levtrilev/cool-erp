"""
CRUD заказов продаж.

Реализует:
- Контроль доступа через AccessService — все 5 слоёв ТЗ RBAC/ABAC §3
- Оптимистическую (version) и пессимистическую (editing_*) блокировки (Правило №40)
- Синхронизацию строк спецификации (полная замена состава)
- Пересчёт total_amount из строк спецификации
- flush в CRUD, commit в роутере (Правило №31)
"""
import uuid
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any, cast as typing_cast

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from app.core.schemas import SortOrder

from app.modules.business_partners.companies.models import BpCompanyModel
from app.core.access.schemas import AccessResult, UserProtocol
from app.core.access.service import AccessService, DocumentProtocol
from app.core.crud.base import CRUDBase
from app.core.doctypes.document_base import EDITING_LOCK_TIMEOUT_MINUTES
from app.core.sections.models import SectionModel, SectionType
from app.modules.sales.orders.exceptions import (
    DeliveryMethodInvalidError,
    SalesOrderEditingLockedError,
    SalesOrderNotFoundError,
    SalesOrderPermissionError,
    SalesOrderVersionConflictError,
    SectionNotInTenantError,
)
from app.modules.sales.orders.models import (
    DeliveryMethod,
    SalesOrderLineModel,
    SalesOrderModel,
)
from app.modules.sales.orders.schemas import (
    SalesOrderCreateSchema,
    SalesOrderLineBaseSchema,
    SalesOrderLineUpdateSchema,
    SalesOrderSortField,
    SalesOrderUpdateSchema,
)


class CRUDSalesOrder(
    CRUDBase[SalesOrderModel, SalesOrderCreateSchema, SalesOrderUpdateSchema]
):
    """CRUD для заказов продаж с блокировками и контролем доступа."""

    # ==================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==================================================================

    @staticmethod
    def _validate_delivery_method(value: str | None) -> None:
        """Проверка допустимости способа доставки (белый список)."""
        if value is not None and value not in DeliveryMethod.ALL:
            raise DeliveryMethodInvalidError(
                f"Недопустимый способ доставки: {value}"
            )

    @staticmethod
    def _compute_total(lines: Sequence[SalesOrderLineBaseSchema]) -> Decimal:
        """
        Сумма заказа = Σ (количество × цена с НДС × (1 − скидка/100)).

        Параметр типизирован как Sequence[SalesOrderLineBaseSchema]:
        Sequence ковариантен, поэтому подходят и list[...CreateSchema],
        и list[...UpdateSchema] (оба наследуют BaseSchema).
        """
        total = Decimal("0")
        hundred = Decimal("100")
        for line in lines:
            line_total: Decimal = line.quantity * line.price_with_vat
            discount: Decimal = line.discount_percent
            total += line_total * (Decimal("1") - discount / hundred)
        return total

    async def _sync_lines(
        self,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        lines: Sequence[SalesOrderLineUpdateSchema],
    ) -> None:
        """
        Синхронизация состава строк спецификации:
        - строка с существующим id → обновление полей;
        - строка без id (или с чужим id) → создание;
        - строки, отсутствующие во входящем списке → удаление.

        Поля присваиваются явно (без model_dump/setattr) для strict-типизации.
        """
        stmt = select(SalesOrderLineModel).where(
            SalesOrderLineModel.order_id == order_id
        )
        existing_lines: dict[uuid.UUID, SalesOrderLineModel] = {
            line.id: line for line in (await db.execute(stmt)).scalars().all()
        }

        kept_ids: set[uuid.UUID] = set()

        for line_data in lines:
            existing: SalesOrderLineModel | None = (
                existing_lines.get(line_data.id)
                if line_data.id is not None
                else None
            )

            if existing is not None:
                existing.line_no = line_data.line_no
                existing.goods_id = line_data.goods_id
                existing.quantity = line_data.quantity
                existing.price_with_vat = line_data.price_with_vat
                existing.discount_percent = line_data.discount_percent
                existing.vat_rate_percent = line_data.vat_rate_percent
                kept_ids.add(existing.id)
            else:
                new_line = SalesOrderLineModel(
                    order_id=order_id,
                    line_no=line_data.line_no,
                    goods_id=line_data.goods_id,
                    quantity=line_data.quantity,
                    price_with_vat=line_data.price_with_vat,
                    discount_percent=line_data.discount_percent,
                    vat_rate_percent=line_data.vat_rate_percent,
                )
                db.add(new_line)

        for line_id, line in existing_lines.items():
            if line_id not in kept_ids:
                await db.delete(line)

        await db.flush()

    # ==================================================================
    # СПИСОК (ТЗ §2.6 — RLS-семантика) + СОРТИРОВКА + ФИЛЬТРЫ (SQL-уровень)
    # ==================================================================

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
        sort_by: SalesOrderSortField | None = None,
        sort_order: SortOrder = SortOrder.ASC,
        filter_doc_number: str | None = None,
        filter_doc_date: date | None = None,
        filter_customer_name: str | None = None,
        filter_supplier_name: str | None = None,
        filter_doc_status: str | None = None,
        filter_updated_at: date | None = None,
        filter_total_amount: Decimal | None = None,
    ) -> tuple[list[SalesOrderModel], int]:
        """
        Список заказов с контролем доступа, сортировкой и фильтрацией.
        Фильтр доступа включает ВСЕ 5 слоёв ТЗ RBAC/ABAC §3.
        Сортировка и фильтры выполняются на уровне SQL (Правило №26).
        """
        model = self.model
        base_where = model.deleted_at.is_(None)

        # ✅ КРИТИЧНО: SQL-фильтр видимости через AccessService
        access_service = AccessService(db)
        access_filter = await access_service.build_access_filter(user, model)
        if access_filter is None:
            return [], 0

        stmt = select(model).where(base_where, access_filter)
        count_stmt = (
            select(func.count())
            .select_from(model)
            .where(base_where, access_filter)
        )

        # ✅ Две связи с одной таблицей компаний → обязательны алиасы.
        # Явная аннотация AliasedClass[...] для strict-режима (Правило №44).
        customer_alias = aliased(BpCompanyModel)
        supplier_alias = aliased(BpCompanyModel)

        need_customer_join: bool = (
            filter_customer_name is not None
            or sort_by == SalesOrderSortField.customer_name
        )
        need_supplier_join: bool = (
            filter_supplier_name is not None
            or sort_by == SalesOrderSortField.supplier_name
        )

        if need_customer_join:
            stmt = stmt.join(
                customer_alias, model.customer_id == customer_alias.id
            )
            count_stmt = count_stmt.join(
                customer_alias, model.customer_id == customer_alias.id
            )
        if need_supplier_join:
            stmt = stmt.join(
                supplier_alias, model.supplier_id == supplier_alias.id
            )
            count_stmt = count_stmt.join(
                supplier_alias, model.supplier_id == supplier_alias.id
            )

        # Глобальный поиск (поверх фильтра доступа)
        if search:
            pattern: str = f"%{search}%"
            search_cond = or_(
                model.doc_number.ilike(pattern),
                model.contact.ilike(pattern),
            )
            stmt = stmt.where(search_cond)
            count_stmt = count_stmt.where(search_cond)

        # ── ФИЛЬТРЫ ПО КОЛОНКАМ ─────────────────────────────────────
        if filter_doc_number:
            cond = model.doc_number.ilike(f"%{filter_doc_number}%")
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_doc_date is not None:
            cond = model.doc_date == filter_doc_date
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_customer_name and need_customer_join:
            cond = customer_alias.name.ilike(f"%{filter_customer_name}%")
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_supplier_name and need_supplier_join:
            cond = supplier_alias.name.ilike(f"%{filter_supplier_name}%")
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_doc_status:
            cond = model.doc_status == filter_doc_status
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_updated_at is not None:
            # ✅ Диапазон вместо CAST по колонке (sargable, индексы работают)
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
        # ✅ Числовой фильтр: точное сравнение NUMERIC.
        # Масштаб не влияет на равенство (100 == 100.00), поэтому
        # пользователь может ввести значение без копеек.
        if filter_total_amount is not None:
            cond = model.total_amount == filter_total_amount
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
            
        total: int = (await db.execute(count_stmt)).scalar_one() or 0

        # ── СОРТИРОВКА (whitelist через Enum) ───────────────────────
        # ✅ Явные if/elif вместо dict: словарь колонок разных типов
        # ломает strict-типизацию из-за инвариантности (Правило №44).
        ascending: bool = sort_order == SortOrder.ASC
        if sort_by == SalesOrderSortField.doc_number:
            stmt = stmt.order_by(
                model.doc_number.asc() if ascending else model.doc_number.desc()
            )
        elif sort_by == SalesOrderSortField.doc_date:
            stmt = stmt.order_by(
                model.doc_date.asc() if ascending else model.doc_date.desc()
            )
        elif sort_by == SalesOrderSortField.customer_name:
            stmt = stmt.order_by(
                customer_alias.name.asc()
                if ascending
                else customer_alias.name.desc()
            )
        elif sort_by == SalesOrderSortField.supplier_name:
            stmt = stmt.order_by(
                supplier_alias.name.asc()
                if ascending
                else supplier_alias.name.desc()
            )
        elif sort_by == SalesOrderSortField.doc_status:
            stmt = stmt.order_by(
                model.doc_status.asc() if ascending else model.doc_status.desc()
            )
        elif sort_by == SalesOrderSortField.total_amount:
            stmt = stmt.order_by(
                model.total_amount.asc()
                if ascending
                else model.total_amount.desc()
            )
        elif sort_by == SalesOrderSortField.updated_at:
            stmt = stmt.order_by(
                model.updated_at.asc() if ascending else model.updated_at.desc()
            )
        else:
            # Порядок по умолчанию: новые сверху
            stmt = stmt.order_by(model.created_at.desc())
        # Вторичная сортировка для стабильной пагинации
        stmt = stmt.order_by(model.id.asc())

        stmt = stmt.offset(skip).limit(limit)
        items: list[SalesOrderModel] = list(
            (await db.execute(stmt)).scalars().all()
        )
        return items, total

    # ==================================================================
    # ОДНОЧНАЯ ЗАПИСЬ (ТЗ §2.3 — нет права на чтение ⇒ 404)
    # ==================================================================

    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesOrderModel | None:
        """
        Получение заказа с контролем доступа.
        Возвращает None, если запись не видна пользователю (ТЗ §2.3).
        """
        model = self.model
        stmt = select(model).where(
            model.id == order_id,
            model.deleted_at.is_(None),
        )

        # Базовая тенантная фильтрация как дополнительная защита.
        # Исключение для платформенного раздела «Общий» обрабатывает
        # AccessService (ТЗ §4.3), поэтому здесь она не абсолютная.
        if not is_superadmin:
            stmt = stmt.where(
                or_(
                    model.tenant_id == tenant_id,
                    model.section_id.in_(
                        select(SectionModel.id).where(
                            SectionModel.section_type == SectionType.PLATFORM
                        )
                    ),
                )
            )

        order = (await db.execute(stmt)).scalar_one_or_none()
        if order is None:
            return None

        # ✅ Проверка доступа через AccessService (все 5 слоёв).
        # typing_cast необходим: анализатор не сопоставляет дескрипторы
        # Mapped[...] модели с аннотациями значений протокола.
        # В рантайме совместимость гарантирована миксинами (Правило №47).
        access_service = AccessService(db)
        order_doc: DocumentProtocol = typing_cast("DocumentProtocol", order)
        access: AccessResult = await access_service.resolve_access(user, order_doc)
        if not access.visible:
            return None
        return order

    # ==================================================================
    # СОЗДАНИЕ (ТЗ §5 — создание требует уровень ≥ 2)
    # ==================================================================

    async def create_for_user(
        self,
        db: AsyncSession,
        *,
        obj_in: SalesOrderCreateSchema,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesOrderModel:
        """Создание заказа со строками спецификации."""
        model = self.model

        self._validate_delivery_method(obj_in.delivery_method)

        # Проверка доступности раздела
        section_stmt = select(SectionModel).where(
            SectionModel.id == obj_in.section_id
        )
        section = (await db.execute(section_stmt)).scalar_one_or_none()
        if section is None:
            raise SectionNotInTenantError("Раздел не найден")

        # ✅ Создание в «Общем» (платформенный) — только Суперадмин (ТЗ §4.3.6)
        if section.section_type == SectionType.PLATFORM and not is_superadmin:
            raise SalesOrderPermissionError(
                "Создание документов в разделе «Общий» доступно только Суперадмину"
            )

        if (
            section.tenant_id is not None
            and section.tenant_id != tenant_id
            and not is_superadmin
        ):
            raise SectionNotInTenantError("Раздел недоступен в этой организации")

        order = model(
            # Контракт доступа (§3.3) — из сессии
            tenant_id=tenant_id,
            section_id=obj_in.section_id,
            author_id=user.id,
            or_tags=obj_in.or_tags,
            and_tags=obj_in.and_tags,
            # Жизненный цикл
            doc_status=obj_in.doc_status,
            doc_number=obj_in.doc_number,
            doc_date=obj_in.doc_date,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
            # Бизнес-поля
            supplier_id=obj_in.supplier_id,
            customer_id=obj_in.customer_id,
            contact=obj_in.contact,
            manager_id=obj_in.manager_id,
            delivery_due_date=obj_in.delivery_due_date,
            payment_scheme=obj_in.payment_scheme,
            currency_id=obj_in.currency_id,
            total_amount=self._compute_total(obj_in.lines),
            delivery_address=obj_in.delivery_address,
            delivery_method=obj_in.delivery_method,
        )

        # ✅ Проверка права на создание через AccessService
        access_service = AccessService(db)
        order_doc: DocumentProtocol = typing_cast("DocumentProtocol", order)
        access: AccessResult = await access_service.resolve_access(user, order_doc)
        if access.level < 2:
            raise SalesOrderPermissionError("Нет права на создание заказа")

        db.add(order)
        await db.flush()  # Получаем order.id

        for line_data in obj_in.lines:
            db.add(
                SalesOrderLineModel(
                    order_id=order.id,
                    line_no=line_data.line_no,
                    goods_id=line_data.goods_id,
                    quantity=line_data.quantity,
                    price_with_vat=line_data.price_with_vat,
                    discount_percent=line_data.discount_percent,
                    vat_rate_percent=line_data.vat_rate_percent,
                )
            )

        await db.flush()
        await db.refresh(order)
        return order

    # ==================================================================
    # БЛОКИРОВКИ (Правило №40, части 3–4) + контроль доступа
    # ==================================================================

    async def acquire_editing_lock(
        self,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesOrderModel:
        """Атомарный захват блокировки с учётом таймаута и контроля доступа."""
        model = self.model

        # 1. СНАЧАЛА проверяем видимость
        order = await self.get_for_user(
            db,
            order_id=order_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if order is None:
            raise SalesOrderNotFoundError("Заказ не найден")

        # 2. ✅ Уровень доступа для блокировки: требуется >= 2
        access_service = AccessService(db)
        order_doc: DocumentProtocol = typing_cast("DocumentProtocol", order)
        access: AccessResult = await access_service.resolve_access(user, order_doc)
        if access.level < 2:
            raise SalesOrderPermissionError(
                "Недостаточно прав для редактирования заказа"
            )

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)

        # ✅ Правило №40, часть 3.2: РОВНО ДВА условия для захвата
        conditions: list[ColumnElement[bool]] = [
            model.id == order_id,
            model.deleted_at.is_(None),
            or_(
                model.editing_by_user_id.is_(None),  # свободно
                model.editing_since < cutoff,        # истекло
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
            order = await self.get_for_user(
                db,
                order_id=order_id,
                user=user,
                tenant_id=tenant_id,
                is_superadmin=is_superadmin,
            )
            if order is None:
                raise SalesOrderNotFoundError("Заказ не найден")
            raise SalesOrderEditingLockedError("Заказ уже редактируется")

        order = await self.get_for_user(
            db,
            order_id=order_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if order is None:
            raise SalesOrderNotFoundError("Заказ не найден")

        await db.flush()
        await db.refresh(order)
        return order

    async def release_editing_lock(
        self,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesOrderModel:
        """Освобождение блокировки владельцем или суперадмином."""
        order = await self.get_for_user(
            db,
            order_id=order_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if order is None:
            raise SalesOrderNotFoundError("Заказ не найден")

        if (
            not is_superadmin
            and order.editing_by_user_id is not None
            and order.editing_by_user_id != user_id
        ):
            raise SalesOrderEditingLockedError(
                "Блокировка принадлежит другому пользователю"
            )

        order.editing_by_user_id = None
        order.editing_since = None
        await db.flush()
        await db.refresh(order)
        return order

    # ==================================================================
    # СОХРАНЕНИЕ С ВЕРСИЕЙ (Правило №40, часть 5) + контроль доступа
    # ==================================================================

    async def save_with_version(
        self,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        obj_in: SalesOrderUpdateSchema,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesOrderModel:
        """Сохранение с проверкой обеих блокировок, доступа и синхронизацией строк."""
        model = self.model

        order = await self.get_for_user(
            db,
            order_id=order_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if order is None:
            raise SalesOrderNotFoundError("Заказ не найден")

        # ✅ Уровень доступа: изменение требует level >= 2
        # ТЗ §5.1: автор (2) — только свои, редактор (3) — любые.
        access_service = AccessService(db)
        order_doc: DocumentProtocol = typing_cast("DocumentProtocol", order)
        access: AccessResult = await access_service.resolve_access(user, order_doc)
        if access.level < 2:
            raise SalesOrderNotFoundError("Заказ не найден")

        # ✅ Правило №40, часть 5.2: ЖЁСТКАЯ проверка пессимистической блокировки
        if (
            order.editing_by_user_id is not None
            and order.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if order.editing_since is None or order.editing_since > cutoff:
                raise SalesOrderEditingLockedError(
                    "Заказ заблокирован другим пользователем для редактирования"
                )

        self._validate_delivery_method(obj_in.delivery_method)

        # Проверка доступности нового раздела (если меняется)
        if obj_in.section_id is not None and obj_in.section_id != order.section_id:
            section_stmt = select(SectionModel).where(
                SectionModel.id == obj_in.section_id
            )
            section = (await db.execute(section_stmt)).scalar_one_or_none()
            if section is None or (
                section.tenant_id is not None
                and section.tenant_id != tenant_id
                and not is_superadmin
            ):
                raise SectionNotInTenantError("Раздел недоступен в этой организации")
            # ✅ Перемещение в «Общий» — только Суперадмин (ТЗ §4.3.6)
            if section.section_type == SectionType.PLATFORM and not is_superadmin:
                raise SalesOrderPermissionError(
                    "Перемещение документа в раздел «Общий» доступно только Суперадмину"
                )

        values: dict[str, Any] = obj_in.model_dump(
            exclude_unset=True, exclude={"version", "lines"}
        )
        values["version"] = model.version + 1
        values["updated_at"] = func.now()
        values["updated_by_user_id"] = user_id
        # После сохранения блокировка освобождается (Правило №40, часть 5)
        values["editing_by_user_id"] = None
        values["editing_since"] = None

        # Пересчёт суммы заказа при переданной спецификации
        if obj_in.lines is not None:
            values["total_amount"] = self._compute_total(obj_in.lines)

        conditions: list[ColumnElement[bool]] = [
            model.id == order_id,
            model.version == obj_in.version,  # ✅ Оптимистическая блокировка
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
            raise SalesOrderVersionConflictError(
                "Заказ изменён другим пользователем. Обновите данные."
            )

        # Синхронизация строк спецификации (после успешного UPDATE)
        if obj_in.lines is not None:
            await self._sync_lines(db, order_id=order_id, lines=obj_in.lines)

        await db.flush()
        await db.refresh(order)
        return order

    # ==================================================================
    # МЯГКОЕ УДАЛЕНИЕ (Правило №40, часть 6) + контроль доступа
    # ==================================================================

    async def mark_deleted(
        self,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesOrderModel:
        """Мягкое удаление с проверкой can_delete и блокировки."""
        order = await self.get_for_user(
            db,
            order_id=order_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if order is None:
            raise SalesOrderNotFoundError("Заказ не найден")

        # ✅ Проверка права на удаление (ТЗ §5.2)
        access_service = AccessService(db)
        order_doc: DocumentProtocol = typing_cast("DocumentProtocol", order)
        access: AccessResult = await access_service.resolve_access(user, order_doc)
        if not access.can_delete:
            raise SalesOrderNotFoundError("Заказ не найден")

        # ✅ Правило №40, часть 6.1: проверка блокировки перед удалением
        if (
            order.editing_by_user_id is not None
            and order.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if order.editing_since is None or order.editing_since > cutoff:
                raise SalesOrderEditingLockedError(
                    "Заказ заблокирован другим пользователем и не может быть удалён"
                )

        order.deleted_at = datetime.now(timezone.utc)
        order.deleted_by_user_id = user_id
        order.updated_by_user_id = user_id
        order.editing_by_user_id = None
        order.editing_since = None
        order.version = order.version + 1
        await db.flush()
        await db.refresh(order)
        return order


crud_sales_order = CRUDSalesOrder(SalesOrderModel)