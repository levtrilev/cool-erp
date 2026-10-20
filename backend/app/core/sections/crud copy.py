import uuid
from datetime import datetime, timezone

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud.base import CRUDBase
from app.core.notes.models import NotesModel
from app.core.sections.exceptions import (
    SectionHasDocumentsError,
    SectionNotAdminError,
    SectionNotFoundError,
    SectionNotInTenantError, # pyright: ignore[reportUnusedImport]
    SectionProtectedError,
)
from app.core.sections.models import (
    PROTECTED_SECTION_TYPES,
    SectionModel,
    SectionType,
)
from app.core.sections.schemas import (
    SectionCreateSchema,
    SectionUpdateSchema,
)


class CRUDSection(CRUDBase[SectionModel, SectionCreateSchema, SectionUpdateSchema]):
    """
    CRUD разделов.

    ✅ Правило №31: наследование от CRUDBase с явными дженериками.
    ✅ Используется self.model (не прямое имя класса).
    ✅ Только flush(); commit выполняется в роутере/сервисе.
    """

    async def list_for_user(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[SectionModel], int]:
        """
        Список разделов, видимых пользователю.

        Пользователь видит:
        - Платформенные разделы (tenant_id IS NULL)
        - Разделы своей организации

        Суперадмин видит все разделы.
        """
        model = self.model

        conditions: list[ColumnElement[bool]] = []

        if not is_superadmin:
            # ✅ Правило №26: фильтрация на уровне SQL
            conditions.append(
                or_(
                    model.tenant_id.is_(None),       # платформенные
                    model.tenant_id == tenant_id,    # своей организации
                )
            )

        if search:
            pattern = f"%{search}%"
            conditions.append(model.name.ilike(pattern))

        count_stmt = select(func.count()).select_from(model)
        stmt = select(model).order_by(model.name.asc())

        if conditions:
            count_stmt = count_stmt.where(*conditions)
            stmt = stmt.where(*conditions)

        stmt = stmt.offset(skip).limit(limit)

        total = (await db.execute(count_stmt)).scalar_one()
        items = list((await db.execute(stmt)).scalars().all())

        return items, total

    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        section_id: uuid.UUID,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> SectionModel | None:
        """Один раздел с проверкой доступности."""
        model = self.model

        conditions: list[ColumnElement[bool]] = [
            model.id == section_id,
        ]

        if not is_superadmin:
            conditions.append(
                or_(
                    model.tenant_id.is_(None),
                    model.tenant_id == tenant_id,
                )
            )

        stmt = select(model).where(*conditions)

        return (await db.execute(stmt)).scalar_one_or_none()

    async def create_custom(
        self,
        db: AsyncSession,
        *,
        obj_in: SectionCreateSchema,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool,
        is_superadmin: bool,
    ) -> SectionModel:
        """
        Создание произвольного раздела.

        ТЗ §9: Создать/переименовать произвольный Раздел —
        только Администратор Организации или Суперадмин.
        """
        # ✅ Проверка прав
        if not is_admin and not is_superadmin:
            raise SectionNotAdminError(
                "Создание разделов доступно только администратору или суперадмину"
            )

        model = self.model

        section = model(
            tenant_id=tenant_id,
            name=obj_in.name,
            description=obj_in.description,
            section_type=SectionType.CUSTOM,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )

        db.add(section)
        await db.flush()
        await db.refresh(section)

        return section

    async def create_tenant_default(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        tenant_name: str,
    ) -> SectionModel:
        """
        Автоматическое создание раздела «Общий для организации».

        ТЗ §4.1: Общий для организации — создаётся автоматически
        при создании Организации. Удаление запрещено.
        """
        model = self.model

        section = model(
            tenant_id=tenant_id,
            name=f"Общий для организации «{tenant_name}»",
            description="Автоматически созданный раздел для организации",
            section_type=SectionType.TENANT_DEFAULT,
            created_by_user_id=None,  # системное создание
            updated_by_user_id=None,
        )

        db.add(section)
        await db.flush()
        await db.refresh(section)

        return section

    async def get_or_create_platform_default(
        self,
        db: AsyncSession,
    ) -> SectionModel:
        """
        Получение или создание платформенного раздела «Общий».

        ТЗ §4.1: Общий (платформенный) — создаётся при инициализации платформы.
        Удаление запрещено.
        """
        model = self.model

        stmt = select(model).where(
            model.section_type == SectionType.PLATFORM
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing is not None:
            return existing

        section = model(
            tenant_id=None,  # платформенный — виден всем
            name="Общий",
            description="Общий платформенный раздел для всех организаций",
            section_type=SectionType.PLATFORM,
            created_by_user_id=None,
            updated_by_user_id=None,
        )

        db.add(section)
        await db.flush()
        await db.refresh(section)

        return section

    async def update_custom(
        self,
        db: AsyncSession,
        *,
        section_id: uuid.UUID,
        obj_in: SectionUpdateSchema,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool,
        is_superadmin: bool,
    ) -> SectionModel:
        """
        Переименование произвольного раздела.

        ТЗ §4.1: Произвольный — изменяется Администратором Организации.
        ТЗ §4.1: Общий (платформенный) и Общий для организации —
        переименование запрещено.
        """
        if not is_admin and not is_superadmin:
            raise SectionNotAdminError(
                "Изменение разделов доступно только администратору или суперадмину"
            )

        section = await self.get_for_user(
            db,
            section_id=section_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )

        if section is None:
            raise SectionNotFoundError("Раздел не найден")

        # ✅ ТЗ §4.1: защищённые разделы нельзя переименовывать
        if section.section_type in PROTECTED_SECTION_TYPES:
            raise SectionProtectedError(
                "Платформенные и общие разделы нельзя переименовывать"
            )

        if obj_in.name is not None:
            section.name = obj_in.name
        if obj_in.description is not None:
            section.description = obj_in.description

        section.updated_by_user_id = user_id
        section.updated_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(section)

        return section

    async def delete_custom(
        self,
        db: AsyncSession,
        *,
        section_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool,
        is_superadmin: bool,
    ) -> SectionModel:
        """
        Удаление произвольного раздела.

        ТЗ §4.1: Произвольный — удаляется Администратором
        при отсутствии документов.
        ТЗ §4.1: Общий (платформенный) и Общий для организации —
        удаление запрещено.
        """
        if not is_admin and not is_superadmin:
            raise SectionNotAdminError(
                "Удаление разделов доступно только администратору или суперадмину"
            )

        section = await self.get_for_user(
            db,
            section_id=section_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )

        if section is None:
            raise SectionNotFoundError("Раздел не найден")

        # ✅ ТЗ §4.1: защищённые разделы нельзя удалять
        if section.section_type in PROTECTED_SECTION_TYPES:
            raise SectionProtectedError(
                "Платформенные и общие разделы нельзя удалить"
            )

        # ✅ Проверка наличия документов в разделе
        # Пока проверяем только notes; в будущем — все типы документов
        docs_count = await db.scalar(
            select(func.count()).select_from(NotesModel).where(
                NotesModel.section_id == section_id,
                NotesModel.deleted_at.is_(None),
            )
        )

        if docs_count and docs_count > 0:
            raise SectionHasDocumentsError(
                f"Раздел содержит {docs_count} документ(ов) и не может быть удалён. "
                f"Сначала переместите или удалите документы."
            )

        # Физическое удаление (раздел не содержит документов)
        await db.delete(section)
        await db.flush()

        return section

    async def get_sections_for_role(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> list[SectionModel]:
        """
        Список всех разделов, доступных для назначения в роли.

        Используется в форме редактирования роли.
        """
        model = self.model

        conditions: list[ColumnElement[bool]] = []

        if not is_superadmin:
            conditions.append(
                or_(
                    model.tenant_id.is_(None),
                    model.tenant_id == tenant_id,
                )
            )

        stmt = select(model).order_by(model.name.asc())

        if conditions:
            stmt = stmt.where(*conditions)

        return list((await db.execute(stmt)).scalars().all())


crud_section = CRUDSection(SectionModel)