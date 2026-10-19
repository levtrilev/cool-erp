import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import ColumnElement, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud.base import CRUDBase
from app.core.doctypes.document_base import EDITING_LOCK_TIMEOUT_MINUTES
from app.core.notes.exceptions import (
    NoteEditingLockedError,
    NoteNotFoundError,
    NoteVersionConflictError,
    SectionNotInTenantError,
)
from app.core.notes.models import NotesModel
from app.core.notes.schemas import NoteCreateSchema, NoteUpdateSchema
from app.core.sections.models import SectionModel


class CRUDNote(CRUDBase[NotesModel, NoteCreateSchema, NoteUpdateSchema]):
    """
    CRUD заметок.

    ✅ Правило №31: наследование от CRUDBase с явными дженериками.
    ✅ Используется self.model (не прямое имя класса).
    ✅ Только flush(); commit выполняется в роутере/сервисе.
    ✅ Новые методы не переопределяют сигнатуры базового класса.
    """

    async def create_for_user(
        self,
        db: AsyncSession,
        *,
        obj_in: NoteCreateSchema,
        tenant_id: uuid.UUID,
        author_id: uuid.UUID,
    ) -> NotesModel:
        """Создание заметки с заполнением контракта из сессии."""
        model: type[NotesModel] = self.model

        # ✅ Правило №26: раздел обязан принадлежать организации
        section_stmt = select(SectionModel).where(
            SectionModel.id == obj_in.section_id
        )
        section: SectionModel | None = (
            await db.execute(section_stmt)
        ).scalar_one_or_none()

        if section is None or section.tenant_id != tenant_id:
            raise SectionNotInTenantError("Раздел недоступен в этой организации")

        note: NotesModel = model(
            title=obj_in.title,
            content=obj_in.content,
            section_id=obj_in.section_id,
            doc_status=obj_in.doc_status,
            doc_number=obj_in.doc_number,
            doc_date=obj_in.doc_date,
            or_tags=obj_in.or_tags,
            and_tags=obj_in.and_tags,
            tenant_id=tenant_id,
            author_id=author_id,
            created_by_user_id=author_id,
            updated_by_user_id=author_id,
        )

        db.add(note)
        await db.flush()

        # ✅ Загружаем server_default (created_at, version) до commit
        await db.refresh(note)

        return note

    async def list_for_user(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
        target_tenant_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 10,
        search: str | None = None,
    ) -> tuple[list[NotesModel], int]:
        """Список активных заметок с пагинацией и поиском."""
        model: type[NotesModel] = self.model

        effective_tenant: uuid.UUID | None = tenant_id
        if is_superadmin:
            effective_tenant = target_tenant_id  # None = все организации

        conditions: list[ColumnElement[bool]] = [model.deleted_at.is_(None)]

        if effective_tenant is not None:
            conditions.append(model.tenant_id == effective_tenant)

        if search:
            pattern: str = f"%{search}%"
            conditions.append(
                or_(
                    model.title.ilike(pattern),
                    model.content.ilike(pattern),
                )
            )

        count_stmt = select(func.count()).select_from(model).where(*conditions)
        total: int = (await db.execute(count_stmt)).scalar_one()

        stmt = (
            select(model)
            .where(*conditions)
            .order_by(model.created_at.desc(), model.id.desc())
            .offset(skip)
            .limit(limit)
        )

        items: list[NotesModel] = list(
            (await db.execute(stmt)).scalars().all()
        )

        return items, total

    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        note_id: uuid.UUID,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> NotesModel | None:
        """Одна активная заметка с проверкой тенанта."""
        model: type[NotesModel] = self.model

        conditions: list[ColumnElement[bool]] = [
            model.id == note_id,
            model.deleted_at.is_(None),
        ]

        if not is_superadmin:
            conditions.append(model.tenant_id == tenant_id)

        stmt = select(model).where(*conditions)

        return (await db.execute(stmt)).scalar_one_or_none()

    async def save_with_version(
        self,
        db: AsyncSession,
        *,
        note_id: uuid.UUID,
        obj_in: NoteUpdateSchema,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> NotesModel:
        """
        Атомарное сохранение с оптимистической блокировкой.

        UPDATE ... WHERE version = :expected_version
        → 0 строк = конфликт (409), а не перезапись чужих изменений.
        """
        model: type[NotesModel] = self.model

        note: NotesModel | None = await self.get_for_user(
            db,
            note_id=note_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )

        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        # ✅ Пессимистическая блокировка с таймаутом
        now: datetime = datetime.now(timezone.utc)
        cutoff: datetime = now - timedelta(
            minutes=EDITING_LOCK_TIMEOUT_MINUTES_LOCAL
        )

        if (
            note.editing_by_user_id is not None
            and note.editing_by_user_id != user_id
            and note.editing_since is not None
            and note.editing_since > cutoff
        ):
            raise NoteEditingLockedError(
                "Документ редактируется другим пользователем"
            )

        if obj_in.section_id is not None:
            section_stmt = select(SectionModel).where(
                SectionModel.id == obj_in.section_id
            )
            section: SectionModel | None = (
                await db.execute(section_stmt)
            ).scalar_one_or_none()

            if section is None or section.tenant_id != note.tenant_id:
                raise SectionNotInTenantError(
                    "Раздел недоступен в этой организации"
                )

        # ✅ Any необходим: SQLAlchemy values() принимает смешанные
        # скалярные значения и SQL-выражения (version + 1, func.now())
        values: dict[str, Any] = obj_in.model_dump(
            exclude_unset=True,
            exclude={"version"},
        )

        values["version"] = model.version + 1
        values["updated_at"] = func.now()
        values["updated_by_user_id"] = user_id
        values["editing_by_user_id"] = None
        values["editing_since"] = None

        conditions: list[ColumnElement[bool]] = [
            model.id == note_id,
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

        updated_id: uuid.UUID | None = (
            await db.execute(stmt)
        ).scalar_one_or_none()

        if updated_id is None:
            raise NoteVersionConflictError(
                "Документ изменён другим пользователем. Обновите данные."
            )

        await db.flush()
        await db.refresh(note)

        return note

    async def mark_deleted(
        self,
        db: AsyncSession,
        *,
        note_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> NotesModel:
        """Мягкое удаление: deleted_at + аудит + инкремент версии."""
        note: NotesModel | None = await self.get_for_user(
            db,
            note_id=note_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )

        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        note.deleted_at = datetime.now(timezone.utc)
        note.deleted_by_user_id = user_id
        note.updated_by_user_id = user_id
        note.editing_by_user_id = None
        note.editing_since = None
        note.version = note.version + 1

        await db.flush()
        await db.refresh(note)

        return note

    async def acquire_editing_lock(
        self,
        db: AsyncSession,
        *,
        note_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> NotesModel:
        """Атомарный захват блокировки с учётом таймаута."""
        model: type[NotesModel] = self.model

        now: datetime = datetime.now(timezone.utc)
        cutoff: datetime = now - timedelta(
            minutes=EDITING_LOCK_TIMEOUT_MINUTES_LOCAL
        )

        conditions: list[ColumnElement[bool]] = [
            model.id == note_id,
            model.deleted_at.is_(None),
            or_(
                model.editing_by_user_id.is_(None),
                model.editing_by_user_id == user_id,
                model.editing_since.is_(None),
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

        locked_id: uuid.UUID | None = (
            await db.execute(stmt)
        ).scalar_one_or_none()

        if locked_id is None:
            note = await self.get_for_user(
                db,
                note_id=note_id,
                tenant_id=tenant_id,
                is_superadmin=is_superadmin,
            )

            if note is None:
                raise NoteNotFoundError("Заметка не найдена")

            raise NoteEditingLockedError("Документ уже редактируется")

        note = await self.get_for_user(
            db,
            note_id=note_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )

        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        await db.flush()
        await db.refresh(note)

        return note

    async def release_editing_lock(
        self,
        db: AsyncSession,
        *,
        note_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> NotesModel:
        """Освобождение блокировки владельцем или суперадмином."""
        note: NotesModel | None = await self.get_for_user(
            db,
            note_id=note_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )

        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        if (
            not is_superadmin
            and note.editing_by_user_id is not None
            and note.editing_by_user_id != user_id
        ):
            raise NoteEditingLockedError(
                "Блокировка принадлежит другому пользователю"
            )

        note.editing_by_user_id = None
        note.editing_since = None

        await db.flush()
        await db.refresh(note)

        return note


# ✅ Таймаут берётся из контракта, локальный алиас — для читаемости
EDITING_LOCK_TIMEOUT_MINUTES_LOCAL: int = EDITING_LOCK_TIMEOUT_MINUTES

crud_note = CRUDNote(NotesModel)