import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, cast as typing_cast

from sqlalchemy import ColumnElement, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import get_access_service
from app.core.access.schemas import (
    ACCESS_LEVEL_EDITOR,
    UserProtocol,
)
from app.core.access.service import DocumentProtocol
from app.core.crud.base import CRUDBase
from app.core.doctypes.document_base import EDITING_LOCK_TIMEOUT_MINUTES
from app.core.notes.exceptions import (
    NoteAccessDeniedError,
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
    CRUD заметок с интеграцией AccessService (ТЗ §8).

    Все методы принимают `user: UserProtocol` вместо разрозненных
    `tenant_id` / `user_id` / `is_superadmin`. Это обеспечивает
    единообразие проверок доступа через единый алгоритм resolve_access.
    """

    async def create_for_user(
        self,
        db: AsyncSession,
        *,
        obj_in: NoteCreateSchema,
        user: UserProtocol,
    ) -> NotesModel:
        """Создание заметки с заполнением контракта из сессии."""
        model = self.model

        # Проверка доступности раздела (через AccessService — для будущей логики)
        section_stmt = select(SectionModel).where(
            SectionModel.id == obj_in.section_id
        )
        section = (await db.execute(section_stmt)).scalar_one_or_none()

        if section is None:
            raise SectionNotInTenantError("Раздел не найден")

        # Раздел должен быть либо платформенный, либо принадлежать организации пользователя
        if (
            section.tenant_id is not None
            and section.tenant_id != user.tenant_id
            and not user.is_superadmin
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
            tenant_id=user.tenant_id,
            author_id=user.id,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )

        db.add(note)
        await db.flush()
        await db.refresh(note)
        return note

    async def list_for_user(
        self,
        db: AsyncSession,
        *,
        user: UserProtocol,
        skip: int = 0,
        limit: int = 10,
        search: str | None = None,
    ) -> tuple[list[NotesModel], int]:
        """
        Список активных заметок с SQL-фильтрацией через AccessService.

        Использует build_access_filter для эффективной фильтрации на уровне БД.
        """
        model = self.model

        conditions: list[ColumnElement[bool]] = [model.deleted_at.is_(None)]

        # ✅ Получаем SQL-фильтр доступа от AccessService
        access_service = get_access_service(db)
        access_filter = await access_service.build_access_filter(user, model)

        if access_filter is None:
            # Доступа нет вообще (нет ролей, нет валидных section_ids)
            return [], 0

        conditions.append(access_filter)

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
        user: UserProtocol,
    ) -> NotesModel | None:
        """
        Одна активная заметка с проверкой доступа через AccessService.
        """
        model = self.model

        # ✅ Загружаем документ без tenant-фильтрации (AccessService проверит доступ)
        stmt = select(model).where(
            model.id == note_id,
            model.deleted_at.is_(None),
        )
        note = (await db.execute(stmt)).scalar_one_or_none()

        if note is None:
            return None

        # ✅ Проверка доступа через AccessService (ТЗ §8)
        access_service = get_access_service(db)
        # result = await access_service.resolve_access(user, note)
        result = await access_service.resolve_access(
            user, typing_cast(DocumentProtocol, note)
        )

        if not result.visible:
            return None

        return note

    async def save_with_version(
        self,
        db: AsyncSession,
        *,
        note_id: uuid.UUID,
        obj_in: NoteUpdateSchema,
        user: UserProtocol,
    ) -> NotesModel:
        """
        Атомарное сохранение с проверкой доступа и оптимистической блокировкой.

        Порядок:
        1. Загрузка документа
        2. Проверка доступа через AccessService (level >= EDITOR)
        3. Проверка пессимистической блокировки
        4. Атомарный UPDATE с version
        """
        model = self.model

        # ШАГ 1: Загрузка
        stmt = select(model).where(
            model.id == note_id,
            model.deleted_at.is_(None),
        )
        note = (await db.execute(stmt)).scalar_one_or_none()

        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        # ШАГ 2: ✅ Проверка доступа через AccessService (ТЗ §8)
        access_service = get_access_service(db)
        # access_result = await access_service.resolve_access(user, note)
        access_result = await access_service.resolve_access(
            user, typing_cast(DocumentProtocol, note)
        )

        if not access_result.visible:
            raise NoteAccessDeniedError("Нет доступа к документу")

        if access_result.level < ACCESS_LEVEL_EDITOR:
            raise NoteAccessDeniedError(
                "Недостаточно прав для редактирования. "
                f"Требуется уровень >= 2 (редактор), текущий: {access_result.level}"
            )

        # ШАГ 3: ЖЁСТКАЯ проверка пессимистической блокировки (Правило №40)
        if (
            note.editing_by_user_id is not None
            and note.editing_by_user_id != user.id
            and not user.is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if note.editing_since is None or note.editing_since > cutoff:
                raise NoteEditingLockedError(
                    "Документ заблокирован другим пользователем для редактирования"
                )

        # ШАГ 4: Проверка доступности нового раздела (если меняется)
        if obj_in.section_id is not None:
            section_stmt = select(SectionModel).where(
                SectionModel.id == obj_in.section_id
            )
            section = (await db.execute(section_stmt)).scalar_one_or_none()

            if section is None or (
                section.tenant_id is not None
                and section.tenant_id != note.tenant_id
            ):
                raise SectionNotInTenantError(
                    "Раздел недоступен в этой организации"
                )

        # ШАГ 5: Атомарный UPDATE с оптимистической блокировкой
        values: dict[str, Any] = obj_in.model_dump(
            exclude_unset=True, exclude={"version"}
        )
        values["version"] = model.version + 1
        values["updated_at"] = func.now()
        values["updated_by_user_id"] = user.id
        values["editing_by_user_id"] = None
        values["editing_since"] = None

        conditions: list[ColumnElement[bool]] = [
            model.id == note_id,
            model.version == obj_in.version,
            model.deleted_at.is_(None),
        ]

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
        user: UserProtocol,
    ) -> NotesModel:
        """
        Мягкое удаление с проверкой can_delete через AccessService.
        """
        model = self.model

        # ШАГ 1: Загрузка
        stmt = select(model).where(
            model.id == note_id,
            model.deleted_at.is_(None),
        )
        note = (await db.execute(stmt)).scalar_one_or_none()

        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        # ШАГ 2: ✅ Проверка доступа через AccessService (ТЗ §8)
        access_service = get_access_service(db)
        # access_result = await access_service.resolve_access(user, note)
        access_result = await access_service.resolve_access(
            user, typing_cast(DocumentProtocol, note)
        )

        if not access_result.visible:
            raise NoteAccessDeniedError("Нет доступа к документу")

        if not access_result.can_delete:
            raise NoteAccessDeniedError(
                "Недостаточно прав для удаления документа"
            )

        # ШАГ 3: Проверка пессимистической блокировки (Правило №40)
        if (
            note.editing_by_user_id is not None
            and note.editing_by_user_id != user.id
            and not user.is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if note.editing_since is None or note.editing_since > cutoff:
                raise NoteEditingLockedError(
                    "Документ заблокирован другим пользователем и не может быть удалён"
                )

        # ШАГ 4: Мягкое удаление
        note.deleted_at = datetime.now(timezone.utc)
        note.deleted_by_user_id = user.id
        note.updated_by_user_id = user.id
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
        user: UserProtocol,
    ) -> NotesModel:
        """
        Атомарный захват блокировки с проверкой доступа через AccessService.
        """
        model = self.model

        # ШАГ 1: Загрузка
        stmt = select(model).where(
            model.id == note_id,
            model.deleted_at.is_(None),
        )
        note = (await db.execute(stmt)).scalar_one_or_none()

        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        # ШАГ 2: ✅ Проверка доступа через AccessService (ТЗ §8)
        access_service = get_access_service(db)
        # access_result = await access_service.resolve_access(user, note)
        access_result = await access_service.resolve_access(
            user, typing_cast(DocumentProtocol, note)
        )
        if not access_result.visible:
            raise NoteAccessDeniedError("Нет доступа к документу")

        if access_result.level < ACCESS_LEVEL_EDITOR:
            raise NoteAccessDeniedError(
                "Недостаточно прав для редактирования. "
                f"Требуется уровень >= 2 (редактор), текущий: {access_result.level}"
            )

        # ШАГ 3: Атомарный захват блокировки (Правило №40)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)

        conditions: list[ColumnElement[bool]] = [
            model.id == note_id,
            model.deleted_at.is_(None),
            or_(
                model.editing_by_user_id.is_(None),
                model.editing_since < cutoff,
            ),
        ]

        stmt = (
            update(model)
            .where(*conditions)
            .values(editing_by_user_id=user.id, editing_since=now)
            .returning(model.id)
        )

        locked_id = (await db.execute(stmt)).scalar_one_or_none()

        if locked_id is None:
            raise NoteEditingLockedError("Документ уже редактируется")

        await db.flush()
        await db.refresh(note)
        return note

    async def release_editing_lock(
        self,
        db: AsyncSession,
        *,
        note_id: uuid.UUID,
        user: UserProtocol,
    ) -> NotesModel:
        """Освобождение блокировки владельцем или суперадмином."""
        # Загрузка с проверкой видимости
        note = await self.get_for_user(
            db,
            note_id=note_id,
            user=user,
        )

        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        # Проверка владельца блокировки (Правило №40)
        if (
            not user.is_superadmin
            and note.editing_by_user_id is not None
            and note.editing_by_user_id != user.id
        ):
            raise NoteEditingLockedError("Блокировка принадлежит другому пользователю")

        note.editing_by_user_id = None
        note.editing_since = None

        await db.flush()
        await db.refresh(note)
        return note


EDITING_LOCK_TIMEOUT_MINUTES_LOCAL: int = EDITING_LOCK_TIMEOUT_MINUTES

crud_note = CRUDNote(NotesModel)