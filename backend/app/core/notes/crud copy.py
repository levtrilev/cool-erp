import logging
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

logger = logging.getLogger(__name__)


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
        model = self.model

        section_stmt = select(SectionModel).where(
            SectionModel.id == obj_in.section_id
        )
        section = (await db.execute(section_stmt)).scalar_one_or_none()

        if section is None or (
            section.tenant_id is not None and section.tenant_id != tenant_id # type: ignore
        ):
            raise SectionNotInTenantError("Раздел недоступен в этой организации")

        note = model(
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
        model = self.model

        effective_tenant: uuid.UUID | None = tenant_id
        if is_superadmin:
            effective_tenant = target_tenant_id

        conditions: list[ColumnElement[bool]] = [model.deleted_at.is_(None)]

        # if effective_tenant is not None:
        #     conditions.append(model.tenant_id == effective_tenant)
        if effective_tenant is not None:
        # ✅ Временное решение до реализации AccessService (ТЗ §8):
        # Показываем документы своей организации ИЛИ документы в разделе "Общий"
        # TODO: Заменить на AccessService, который будет проверять видимость
        # через роли и разделы
            conditions.append(
            or_(
                model.tenant_id == effective_tenant,
                # Документы в разделе "Общий" (platform) видны всем
                model.section_id.in_(
                    select(SectionModel.id).where(
                        SectionModel.section_type == "platform"
                    )
                ),
            )
        )

        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    model.title.ilike(pattern),
                    model.content.ilike(pattern),
                )
            )

        count_stmt = select(func.count()).select_from(model).where(*conditions)
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = (
            select(model)
            .where(*conditions)
            .order_by(model.created_at.desc(), model.id.desc())
            .offset(skip)
            .limit(limit)
        )

        items = list((await db.execute(stmt)).scalars().all())

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
        model = self.model

        conditions: list[ColumnElement[bool]] = [
            model.id == note_id,
            model.deleted_at.is_(None),
        ]

        # if not is_superadmin:
        #     conditions.append(model.tenant_id == tenant_id)
        if not is_superadmin:
            # ✅ Документ доступен, если:
            # 1. Принадлежит организации пользователя, ИЛИ
            # 2. Находится в разделе "Общий" (platform)
            conditions.append(
                or_(
                    model.tenant_id == tenant_id,
                    model.section_id.in_(
                        select(SectionModel.id).where(
                            SectionModel.section_type == "platform"
                        )
                    ),
                )
            )        

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
        """
        model = self.model

        note = await self.get_for_user(
            db,
            note_id=note_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )

        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        # ✅ ЛОГИРОВАНИЕ для диагностики
        logger.info(
            f"[save_with_version] note_id={note_id}, user_id={user_id}, "
            f"is_superadmin={is_superadmin}, "
            f"editing_by_user_id={note.editing_by_user_id}, "
            f"editing_since={note.editing_since}"
        )

        # ✅ ЖЁСТКАЯ проверка пессимистической блокировки
        if (
            note.editing_by_user_id is not None
            and note.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES_LOCAL)
            
            logger.info(
                f"[save_with_version] Проверка блокировки: "
                f"now={now}, cutoff={cutoff}, "
                f"editing_since={note.editing_since}"
            )
            
            if note.editing_since is None or note.editing_since > cutoff:
                raise NoteEditingLockedError(
                    "Документ заблокирован другим пользователем для редактирования"
                )

        if obj_in.section_id is not None:
            section_stmt = select(SectionModel).where(
                SectionModel.id == obj_in.section_id
            )
            section = (await db.execute(section_stmt)).scalar_one_or_none()

            if section is None or (
                section.tenant_id is not None # type: ignore
                and section.tenant_id != note.tenant_id
            ):
                raise SectionNotInTenantError(
                    "Раздел недоступен в этой организации"
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

        updated_id = (await db.execute(stmt)).scalar_one_or_none()

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
        note = await self.get_for_user(
            db,
            note_id=note_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )

        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        if (
            note.editing_by_user_id is not None
            and note.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES_LOCAL)
            if note.editing_since is None or note.editing_since > cutoff:
                raise NoteEditingLockedError(
                    "Документ заблокирован другим пользователем и не может быть удалён"
                )

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
        model = self.model

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES_LOCAL)

        # ✅ УПРОЩЁННАЯ логика: разрешаем захват только в двух случаях:
        # 1. Блокировка свободна (editing_by_user_id IS NULL)
        # 2. Блокировка истекла (editing_since < cutoff)
        # Убираем аномальные условия (editing_by_user_id == user_id, editing_since IS NULL)
        conditions: list[ColumnElement[bool]] = [
            model.id == note_id,
            model.deleted_at.is_(None),
            or_(
                model.editing_by_user_id.is_(None),  # ✅ свободно
                model.editing_since < cutoff,        # ✅ истекло
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

        logger.info(
            f"[acquire_editing_lock] note_id={note_id}, user_id={user_id}, "
            f"locked_id={locked_id}, now={now}, cutoff={cutoff}"
        )

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
        note = await self.get_for_user(
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
            raise NoteEditingLockedError("Блокировка принадлежит другому пользователю")

        note.editing_by_user_id = None
        note.editing_since = None

        await db.flush()
        await db.refresh(note)

        return note


EDITING_LOCK_TIMEOUT_MINUTES_LOCAL: int = EDITING_LOCK_TIMEOUT_MINUTES

crud_note = CRUDNote(NotesModel)