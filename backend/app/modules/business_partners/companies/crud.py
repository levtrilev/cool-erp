"""CRUD для компаний с блокировками (Правило №40)."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.crud.base import CRUDBase
from app.core.doctypes.document_base import EDITING_LOCK_TIMEOUT_MINUTES
from app.modules.business_partners.companies.exceptions import (
    CompanyEditingLockedError,
    CompanyNotFoundError,
    CompanyVersionConflictError,
)
from app.modules.business_partners.companies.models import BpCompanyModel
from app.modules.business_partners.companies.schemas import (
    BpCompanyCreateSchema,
    BpCompanyUpdateSchema,
)


class CRUDCompany(
    CRUDBase[BpCompanyModel, BpCompanyCreateSchema, BpCompanyUpdateSchema]
):
    """CRUD для компаний с блокировками."""

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[BpCompanyModel], int]:
        """Список компаний с мультивенантной изоляцией (Правило №26)."""
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
                    self.model.fullname.ilike(pattern),
                    self.model.inn.ilike(pattern),
                )
            )
            count_stmt = count_stmt.where(
                or_(
                    self.model.name.ilike(pattern),
                    self.model.fullname.ilike(pattern),
                    self.model.inn.ilike(pattern),
                )
            )

        total: int = (await db.execute(count_stmt)).scalar_one() or 0
        stmt = stmt.order_by(self.model.name.asc()).offset(skip).limit(limit)
        items: list[BpCompanyModel] = list(
            (await db.execute(stmt)).scalars().all()
        )
        return items, total

    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        company_id: uuid.UUID,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel | None:
        """Получение компании с мультивенантной изоляцией."""
        stmt = select(self.model).where(
            self.model.id == company_id,
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
        company_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """Атомарный захват блокировки с учётом таймаута."""
        model = self.model
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)

        # ✅ Правило №40, часть 3.2: РОВНО ДВА условия для захвата
        conditions: list[ColumnElement[bool]] = [
            model.id == company_id,
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
            company = await self.get_for_user(
                db,
                company_id=company_id,
                tenant_id=tenant_id,
                is_superadmin=is_superadmin,
            )
            if company is None:
                raise CompanyNotFoundError("Компания не найдена")
            raise CompanyEditingLockedError("Компания уже редактируется")

        company = await self.get_for_user(
            db,
            company_id=company_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if company is None:
            raise CompanyNotFoundError("Компания не найдена")

        # ✅ Только flush в CRUD (Правило №40, часть 8.1)
        await db.flush()
        await db.refresh(company)
        return company

    async def release_editing_lock(
        self,
        db: AsyncSession,
        *,
        company_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """Освобождение блокировки владельцем или суперадмином."""
        company = await self.get_for_user(
            db,
            company_id=company_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if company is None:
            raise CompanyNotFoundError("Компания не найдена")

        # ✅ Правило №40, часть 4.1: освободить может только владелец
        if (
            not is_superadmin
            and company.editing_by_user_id is not None
            and company.editing_by_user_id != user_id
        ):
            raise CompanyEditingLockedError(
                "Блокировка принадлежит другому пользователю"
            )

        company.editing_by_user_id = None
        company.editing_since = None

        await db.flush()
        await db.refresh(company)
        return company

    # ==================================================================
    # СОХРАНЕНИЕ С ВЕРСИЕЙ (Правило №40, часть 5)
    # ==================================================================

    async def save_with_version(
        self,
        db: AsyncSession,
        *,
        company_id: uuid.UUID,
        obj_in: BpCompanyUpdateSchema,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """Сохранение с проверкой обеих блокировок."""
        model = self.model
        company = await self.get_for_user(
            db,
            company_id=company_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if company is None:
            raise CompanyNotFoundError("Компания не найдена")

        # ✅ Правило №40, часть 5.2: ЖЁСТКАЯ проверка пессимистической блокировки
        if (
            company.editing_by_user_id is not None
            and company.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if company.editing_since is None or company.editing_since > cutoff:
                raise CompanyEditingLockedError(
                    "Компания заблокирована другим пользователем для редактирования"
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
            model.id == company_id,
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
            raise CompanyVersionConflictError(
                "Компания изменена другим пользователем. Обновите данные."
            )

        await db.flush()
        await db.refresh(company)
        return company

    # ==================================================================
    # МЯГКОЕ УДАЛЕНИЕ (Правило №40, часть 6)
    # ==================================================================

    async def mark_deleted(
        self,
        db: AsyncSession,
        *,
        company_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """Мягкое удаление с проверкой блокировки."""
        company = await self.get_for_user(
            db,
            company_id=company_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if company is None:
            raise CompanyNotFoundError("Компания не найдена")

        # ✅ Правило №40, часть 6.1: проверка блокировки перед удалением
        if (
            company.editing_by_user_id is not None
            and company.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if company.editing_since is None or company.editing_since > cutoff:
                raise CompanyEditingLockedError(
                    "Компания заблокирована другим пользователем и не может быть удалена"
                )

        company.deleted_at = datetime.now(timezone.utc)
        company.deleted_by_user_id = user_id
        company.updated_by_user_id = user_id
        company.editing_by_user_id = None
        company.editing_since = None
        company.version = company.version + 1

        await db.flush()
        await db.refresh(company)
        return company


crud_company = CRUDCompany(BpCompanyModel)