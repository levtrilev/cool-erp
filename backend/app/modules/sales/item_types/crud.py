# backend/app/modules/sales/item_types/crud.py
"""
CRUD типов номенклатуры.
Контроль доступа через AccessService, двойные блокировки (Правило №40),
flush в CRUD / commit в роутере (Правило №31).
"""
import string
import uuid
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any, cast as typing_cast

from sqlalchemy import ColumnElement, and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access.schemas import AccessResult, UserProtocol
from app.core.access.service import AccessService, DocumentProtocol
from app.core.crud.base import CRUDBase
from app.core.doctypes.document_base import EDITING_LOCK_TIMEOUT_MINUTES
from app.core.schemas import SortOrder
from app.core.sections.models import SectionModel, SectionType
from app.modules.sales.item_types.exceptions import (
    SalesItemTypeEditingLockedError,
    SalesItemTypeNotFoundError,
    SalesItemTypePermissionError,
    SalesItemTypeVersionConflictError,
    SectionNotInTenantError,
)
from app.modules.sales.item_types.models import SalesItemTypeModel
from app.modules.sales.item_types.schemas import (
    SalesItemTypeCreateSchema,
    SalesItemTypeSortField,
    SalesItemTypeUpdateSchema,
)


class CRUDSalesItemType(
    CRUDBase[
        SalesItemTypeModel, SalesItemTypeCreateSchema, SalesItemTypeUpdateSchema
    ]
):
    """CRUD типов номенклатуры с блокировками и контролем доступа."""

    # ==================================================================
    # СПИСОК: доступ + поиск + фильтры + сортировка на уровне SQL
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
        sort_by: SalesItemTypeSortField | None = None,
        sort_order: SortOrder = SortOrder.ASC,
        filter_name: str | None = None,
        filter_item_class: str | None = None,
        filter_vat_rate: Decimal | None = None,
        filter_doc_number: str | None = None,
        filter_updated_at: datetime | None = None,
    ) -> tuple[list[SalesItemTypeModel], int]:
        model = self.model
        base_where = model.deleted_at.is_(None)

        access_service = AccessService(db)
        access_filter = await access_service.build_access_filter(user, model)
        if access_filter is None:
            return [], 0

        stmt = select(model).where(base_where, access_filter)
        count_stmt = (
            select(func.count()).select_from(model).where(base_where, access_filter)
        )

        if search:
            pattern: str = f"%{search}%"
            search_cond = or_(
                model.name.ilike(pattern),
                model.description.ilike(pattern),
                model.doc_number.ilike(pattern),
            )
            stmt = stmt.where(search_cond)
            count_stmt = count_stmt.where(search_cond)

        if filter_name:
            cond = model.name.ilike(f"%{filter_name}%")
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_item_class:
            cond = model.item_class == filter_item_class
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_vat_rate is not None:
            cond = model.vat_rate == filter_vat_rate
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_doc_number:
            cond = model.doc_number.ilike(f"%{filter_doc_number}%")
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_updated_at is not None:
            day_start = datetime.combine(
                filter_updated_at.date(), time.min, tzinfo=timezone.utc
            )
            day_end = day_start + timedelta(days=1)
            cond = and_(model.updated_at >= day_start, model.updated_at < day_end)
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        total: int = (await db.execute(count_stmt)).scalar_one() or 0

        ascending: bool = sort_order == SortOrder.ASC
        if sort_by == typing_cast(string, SalesItemTypeSortField.item_name):
            stmt = stmt.order_by(
                model.name.asc() if ascending else model.name.desc()
            )
        elif sort_by == SalesItemTypeSortField.item_class:
            stmt = stmt.order_by(
                model.item_class.asc() if ascending else model.item_class.desc()
            )
        elif sort_by == SalesItemTypeSortField.vat_rate:
            stmt = stmt.order_by(
                model.vat_rate.asc() if ascending else model.vat_rate.desc()
            )
        elif sort_by == SalesItemTypeSortField.doc_number:
            stmt = stmt.order_by(
                model.doc_number.asc() if ascending else model.doc_number.desc()
            )
        elif sort_by == SalesItemTypeSortField.updated_at:
            stmt = stmt.order_by(
                model.updated_at.asc() if ascending else model.updated_at.desc()
            )
        else:
            stmt = stmt.order_by(model.created_at.desc())
        stmt = stmt.order_by(model.id.asc())
        stmt = stmt.offset(skip).limit(limit)

        items: list[SalesItemTypeModel] = list(
            (await db.execute(stmt)).scalars().all()
        )
        return items, total

    # ==================================================================
    # ОДНА ЗАПИСЬ (ТЗ §2.3)
    # ==================================================================
    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        item_type_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesItemTypeModel | None:
        model = self.model
        stmt = select(model).where(
            model.id == item_type_id, model.deleted_at.is_(None)
        )
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
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        access_service = AccessService(db)
        # ✅ typing_cast: анализатор не сопоставляет дескрипторы Mapped[...]
        # модели с аннотациями значений протокола; в рантайме совместимость
        # гарантирована миксинами (Правило №47).
        row_doc: DocumentProtocol = typing_cast("DocumentProtocol", row)
        access: AccessResult = await access_service.resolve_access(user, row_doc)
        if not access.visible:
            return None
        return row

    # ==================================================================
    # СОЗДАНИЕ (ТЗ §5: уровень ≥ 2)
    # ==================================================================
    async def create_for_user(
        self,
        db: AsyncSession,
        *,
        obj_in: SalesItemTypeCreateSchema,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesItemTypeModel:
        model = self.model
        section_stmt = select(SectionModel).where(
            SectionModel.id == obj_in.section_id
        )
        section = (await db.execute(section_stmt)).scalar_one_or_none()
        if section is None:
            raise SectionNotInTenantError("Раздел не найден")
        if section.section_type == SectionType.PLATFORM and not is_superadmin:
            raise SalesItemTypePermissionError(
                "Создание документов в разделе «Общий» доступно только Суперадмину"
            )
        if (
            section.tenant_id is not None
            and section.tenant_id != tenant_id
            and not is_superadmin
        ):
            raise SectionNotInTenantError("Раздел недоступен в этой организации")

        row = model(
            tenant_id=tenant_id,
            section_id=obj_in.section_id,
            author_id=user.id,
            or_tags=obj_in.or_tags,
            and_tags=obj_in.and_tags,
            doc_status=obj_in.doc_status,
            doc_number=obj_in.doc_number,
            doc_date=obj_in.doc_date,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
            name=obj_in.name,
            description=obj_in.description,
            item_class=obj_in.item_class,
            serial_tracking=obj_in.serial_tracking,
            expiration_tracking=obj_in.expiration_tracking,
            vat_rate=obj_in.vat_rate,
            base_uom=obj_in.base_uom,
            price_group=obj_in.price_group,
            supply_type=obj_in.supply_type,
            has_variants=obj_in.has_variants,
        )
        access_service = AccessService(db)
        row_doc: DocumentProtocol = typing_cast("DocumentProtocol", row)
        access: AccessResult = await access_service.resolve_access(user, row_doc)
        if access.level < 2:
            raise SalesItemTypePermissionError(
                "Нет права на создание типа номенклатуры"
            )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row

    # ==================================================================
    # БЛОКИРОВКИ (Правило №40, части 3–4)
    # ==================================================================
    async def acquire_editing_lock(
        self,
        db: AsyncSession,
        *,
        item_type_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesItemTypeModel:
        model = self.model
        row = await self.get_for_user(
            db,
            item_type_id=item_type_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if row is None:
            raise SalesItemTypeNotFoundError("Тип номенклатуры не найден")
        access_service = AccessService(db)
        row_doc: DocumentProtocol = typing_cast("DocumentProtocol", row)
        access: AccessResult = await access_service.resolve_access(user, row_doc)
        if access.level < 2:
            raise SalesItemTypePermissionError(
                "Недостаточно прав для редактирования типа номенклатуры"
            )
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
        conditions: list[ColumnElement[bool]] = [
            model.id == item_type_id,
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
            raise SalesItemTypeEditingLockedError(
                "Тип номенклатуры уже редактируется"
            )
        row = await self.get_for_user(
            db,
            item_type_id=item_type_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if row is None:
            raise SalesItemTypeNotFoundError("Тип номенклатуры не найден")
        await db.flush()
        await db.refresh(row)
        return row

    async def release_editing_lock(
        self,
        db: AsyncSession,
        *,
        item_type_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesItemTypeModel:
        row = await self.get_for_user(
            db,
            item_type_id=item_type_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if row is None:
            raise SalesItemTypeNotFoundError("Тип номенклатуры не найден")
        if (
            not is_superadmin
            and row.editing_by_user_id is not None
            and row.editing_by_user_id != user_id
        ):
            raise SalesItemTypeEditingLockedError(
                "Блокировка принадлежит другому пользователю"
            )
        row.editing_by_user_id = None
        row.editing_since = None
        await db.flush()
        await db.refresh(row)
        return row

    # ==================================================================
    # СОХРАНЕНИЕ С ВЕРСИЕЙ (Правило №40, часть 5)
    # ==================================================================
    async def save_with_version(
        self,
        db: AsyncSession,
        *,
        item_type_id: uuid.UUID,
        obj_in: SalesItemTypeUpdateSchema,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesItemTypeModel:
        model = self.model
        row = await self.get_for_user(
            db,
            item_type_id=item_type_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if row is None:
            raise SalesItemTypeNotFoundError("Тип номенклатуры не найден")
        access_service = AccessService(db)
        row_doc: DocumentProtocol = typing_cast("DocumentProtocol", row)
        access: AccessResult = await access_service.resolve_access(user, row_doc)
        if access.level < 2:
            raise SalesItemTypeNotFoundError("Тип номенклатуры не найден")
        if (
            row.editing_by_user_id is not None
            and row.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if row.editing_since is None or row.editing_since > cutoff:
                raise SalesItemTypeEditingLockedError(
                    "Документ заблокирован другим пользователем для редактирования"
                )
        if obj_in.section_id is not None and obj_in.section_id != row.section_id:
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
            if section.section_type == SectionType.PLATFORM and not is_superadmin:
                raise SalesItemTypePermissionError(
                    "Перемещение документа в раздел «Общий» доступно только Суперадмину"
                )

        values: dict[str, Any] = obj_in.model_dump(exclude_unset=True, exclude={"version"})
        values["version"] = model.version + 1
        values["updated_at"] = func.now()
        values["updated_by_user_id"] = user_id
        values["editing_by_user_id"] = None
        values["editing_since"] = None

        conditions: list[ColumnElement[bool]] = [
            model.id == item_type_id,
            model.version == obj_in.version,
            model.deleted_at.is_(None),
        ]
        if not is_superadmin:
            conditions.append(model.tenant_id == tenant_id)
        stmt = (
            update(model).where(*conditions).values(**values).returning(model.id)
        )
        updated_id = (await db.execute(stmt)).scalar_one_or_none()
        if updated_id is None:
            raise SalesItemTypeVersionConflictError(
                "Тип номенклатуры изменён другим пользователем. Обновите данные."
            )
        await db.flush()
        await db.refresh(row)
        return row

    # ==================================================================
    # МЯГКОЕ УДАЛЕНИЕ (Правило №40, часть 6)
    # ==================================================================
    async def mark_deleted(
        self,
        db: AsyncSession,
        *,
        item_type_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SalesItemTypeModel:
        row = await self.get_for_user(
            db,
            item_type_id=item_type_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if row is None:
            raise SalesItemTypeNotFoundError("Тип номенклатуры не найден")
        access_service = AccessService(db)
        row_doc: DocumentProtocol = typing_cast("DocumentProtocol", row)
        access: AccessResult = await access_service.resolve_access(user, row_doc)
        if not access.can_delete:
            raise SalesItemTypeNotFoundError("Тип номенклатуры не найден")
        if (
            row.editing_by_user_id is not None
            and row.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if row.editing_since is None or row.editing_since > cutoff:
                raise SalesItemTypeEditingLockedError(
                    "Документ заблокирован другим пользователем и не может быть удалён"
                )
        row.deleted_at = datetime.now(timezone.utc)
        row.deleted_by_user_id = user_id
        row.updated_by_user_id = user_id
        row.editing_by_user_id = None
        row.editing_since = None
        row.version = row.version + 1
        await db.flush()
        await db.refresh(row)
        return row


crud_sales_item_type = CRUDSalesItemType(SalesItemTypeModel)