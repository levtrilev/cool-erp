"""CRUD для компаний с блокировками (Правило №40) и контролем доступа (ТЗ RBAC/ABAC §8)."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any # pyright: ignore[reportUnusedImport]
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from typing import cast as typing_cast

from app.core.access.service import AccessService, DocumentProtocol
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
from app.core.access.schemas import UserProtocol

# ✅ Избегаем циклического импорта — UserModel нужен только для типизации
# if TYPE_CHECKING:
#     from app.core.users.models import UserModel


class CRUDCompany(
    CRUDBase[BpCompanyModel, BpCompanyCreateSchema, BpCompanyUpdateSchema]
):
    """CRUD для компаний с блокировками и контролем доступа."""

    # ==================================================================
    # ВСПОМОГАТЕЛЬНЫЙ МЕТОД: проверка доступа к одиночной записи
    # ==================================================================
    async def _ensure_visible_for_user(
        self,
        db: AsyncSession,
        *,
        company: BpCompanyModel,
        user: UserProtocol,
    ) -> None:
        """
        Проверка видимости компании для пользователя через AccessService.
        Если запись не видна — поднимает CompanyNotFoundError (ТЗ §2.3, §2.6:
        'запись не существует для пользователя').
        """
        access_service = AccessService(db)
        # ✅ Правило №45: typing_cast в точке вызова resolve_access.
        # Статический анализатор не сопоставляет дескрипторы Mapped[...]
        # модели с аннотациями значений протокола. В рантайме совместимость
        # гарантирована миксинами DocumentAccessMixin + DocumentLifecycleMixin.
        company_doc: DocumentProtocol = typing_cast("DocumentProtocol", company)
        access = await access_service.resolve_access(user, company_doc)
        if not access.visible:
            raise CompanyNotFoundError("Компания не найдена")

    # ==================================================================
    # СПИСОК (ТЗ §2.6 — RLS-семантика: скрытые записи не возвращаются)
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
    ) -> tuple[list[BpCompanyModel], int]:
        """
        Список компаний с контролем доступа через AccessService.
        Фильтр включает ВСЕ 5 слоёв ТЗ RBAC/ABAC §3:
          Слой 1 (тенант) + Слой 2 (разделы роли) + Слой 3 (doctype/permission)
          + Слой 4 (теги) + Слой 5 (уровень ≥ 1 для видимости).
        """
        model = self.model
        base_where = model.deleted_at.is_(None)

        # ✅ КРИТИЧНО: SQL-фильтр видимости через AccessService
        access_service = AccessService(db)
        access_filter = await access_service.build_access_filter(user, model)
        if access_filter is None:
            # Пользователю не видна ни одна запись (нет ролей / нет разделов /
            # не прошёл тег-фильтр для всех записей) — возвращаем пустой список.
            return [], 0

        stmt = select(model).where(base_where, access_filter)
        count_stmt = (
            select(func.count())
            .select_from(model)
            .where(base_where, access_filter)
        )

        # Поиск по тексту (применяется поверх фильтра доступа)
        if search:
            pattern: str = f"%{search}%"
            search_cond = or_(
                model.name.ilike(pattern),
                model.fullname.ilike(pattern),
                model.inn.ilike(pattern),
            )
            stmt = stmt.where(search_cond)
            count_stmt = count_stmt.where(search_cond)

        total: int = (await db.execute(count_stmt)).scalar_one() or 0
        stmt = stmt.order_by(model.name.asc()).offset(skip).limit(limit)
        items: list[BpCompanyModel] = list(
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
        company_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel | None:
        """
        Получение компании с контролем доступа.
        Возвращает None, если запись не видна пользователю (ТЗ §2.3).
        """
        model = self.model
        stmt = select(model).where(
            model.id == company_id,
            model.deleted_at.is_(None),
        )
        # Базовая тенантная фильтрация остаётся как дополнительная защита
        if not is_superadmin:
            stmt = stmt.where(model.tenant_id == tenant_id)

        company = (await db.execute(stmt)).scalar_one_or_none()
        if company is None:
            return None

        # ✅ Проверка доступа через AccessService (все 5 слоёв)
        access_service = AccessService(db)
        company_doc: DocumentProtocol = typing_cast("DocumentProtocol", company)
        access = await access_service.resolve_access(user, company_doc)
        if not access.visible:
            # ТЗ §2.6: запись не существует для пользователя
            return None
        return company

    # ==================================================================
    # БЛОКИРОВКИ (Правило №40, часть 3) + контроль доступа
    # ==================================================================
    async def acquire_editing_lock(
        self,
        db: AsyncSession,
        *,
        company_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """Атомарный захват блокировки с учётом таймаута и контроля доступа."""
        model = self.model

        # ✅ СНАЧАЛА проверяем доступ — если пользователь не видит компанию,
        # он не должен иметь возможности даже попытаться её заблокировать.
        # Это также предотвращает раскрытие факта существования компании.
        pre_check = await self.get_for_user(
            db,
            company_id=company_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if pre_check is None:
            raise CompanyNotFoundError("Компания не найдена")

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)

        # ✅ Правило №40, часть 3.2: РОВНО ДВА условия для захвата
        conditions: list[ColumnElement[bool]] = [
            model.id == company_id,
            model.deleted_at.is_(None),
            or_(
                model.editing_by_user_id.is_(None),   # свободно
                model.editing_since < cutoff,          # истекло
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
            # Повторная проверка: компания может быть не найдена из-за
            # доступа, либо заблокирована другим пользователем.
            company = await self.get_for_user(
                db,
                company_id=company_id,
                user=user,
                tenant_id=tenant_id,
                is_superadmin=is_superadmin,
            )
            if company is None:
                raise CompanyNotFoundError("Компания не найдена")
            raise CompanyEditingLockedError("Компания уже редактируется")

        company = await self.get_for_user(
            db,
            company_id=company_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if company is None:
            raise CompanyNotFoundError("Компания не найдена")

        await db.flush()
        await db.refresh(company)
        return company

    async def release_editing_lock(
        self,
        db: AsyncSession,
        *,
        company_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """Освобождение блокировки владельцем или суперадмином."""
        company = await self.get_for_user(
            db,
            company_id=company_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if company is None:
            raise CompanyNotFoundError("Компания не найдена")

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
    # СОХРАНЕНИЕ С ВЕРСИЕЙ (Правило №40, часть 5) + контроль доступа
    # ==================================================================
    async def save_with_version(
        self,
        db: AsyncSession,
        *,
        company_id: uuid.UUID,
        obj_in: BpCompanyUpdateSchema,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """Сохранение с проверкой обеих блокировок и контроля доступа."""
        model = self.model

        company = await self.get_for_user(
            db,
            company_id=company_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if company is None:
            raise CompanyNotFoundError("Компания не найдена")

        # ✅ Проверка уровня доступа: изменение требует минимум level >= 2
        # (автор для своей записи) или level >= 3 (редактор).
        # resolve_access уже вычислил доступ в get_for_user, но нам нужен
        # уровень — запрашиваем повторно (кэш AccessService не кэширует
        # между вызовами, но запросы дешёвые и идут в одной транзакции).
        access_service = AccessService(db)
        company_doc: DocumentProtocol = typing_cast("DocumentProtocol", company)
        access = await access_service.resolve_access(user, company_doc)
        # level >= 2 означает «автор своей записи» или выше.
        # ТЗ §5.1: автор (2) может изменять только свои, редактор (3) — любые.
        if access.level < 2:
            # Нет права на изменение — для пользователя запись «не существует»
            # в контексте редактирования (ТЗ §2.3 + §5.4).
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

        values: dict[str, Any] = obj_in.model_dump(
            exclude_unset=True, exclude={"version"}
        )
        values["version"] = model.version + 1
        values["updated_at"] = func.now()
        values["updated_by_user_id"] = user_id
        values["editing_by_user_id"] = None
        values["editing_since"] = None

        conditions: list[ColumnElement[bool]] = [
            model.id == company_id,
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
            raise CompanyVersionConflictError(
                "Компания изменена другим пользователем. Обновите данные."
            )

        await db.flush()
        await db.refresh(company)
        return company

    # ==================================================================
    # МЯГКОЕ УДАЛЕНИЕ (Правило №40, часть 6) + контроль доступа
    # ==================================================================
    async def mark_deleted(
        self,
        db: AsyncSession,
        *,
        company_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """Мягкое удаление с проверкой блокировки и контроля доступа."""
        company = await self.get_for_user(
            db,
            company_id=company_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if company is None:
            raise CompanyNotFoundError("Компания не найдена")

        # ✅ Проверка права на удаление:
        # ТЗ §5.2.4: can_delete = (флаг из роли) OR (level >= 2).
        # AccessService уже вычислил can_delete в resolve_access.
        access_service = AccessService(db)
        company_doc: DocumentProtocol = typing_cast("DocumentProtocol", company)
        access = await access_service.resolve_access(user, company_doc)
        if not access.can_delete:
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