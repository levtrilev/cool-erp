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
from app.core.sections.models import SectionModel, SectionType
from app.core.access import get_access_service
from app.core.access.schemas import UserProtocol
# from app.core.users.models import UserModel

class CRUDNote(CRUDBase[NotesModel, NoteCreateSchema, NoteUpdateSchema]):
    """
    CRUD заметок с поддержкой кросс-организационного доступа через раздел "Общий".
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
            section.tenant_id is not None and section.tenant_id != tenant_id
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

    # async def list_for_user(
    #     self,
    #     db: AsyncSession,
    #     *,
    #     tenant_id: uuid.UUID,
    #     is_superadmin: bool = False,
    #     target_tenant_id: uuid.UUID | None = None,
    #     skip: int = 0,
    #     limit: int = 10,
    #     search: str | None = None,
    # ) -> tuple[list[NotesModel], int]:
    #     """
    #     Список активных заметок с пагинацией и поиском.
        
    #     ✅ Кросс-организационный доступ: документы в разделе "Общий" (platform)
    #     видны пользователям всех организаций.
    #     """
    #     model = self.model

    #     effective_tenant: uuid.UUID | None = tenant_id
    #     if is_superadmin:
    #         effective_tenant = target_tenant_id

    #     conditions: list[ColumnElement[bool]] = [model.deleted_at.is_(None)]

    #     if effective_tenant is not None:
    #         # ✅ Кросс-организационный доступ через раздел "Общий"
    #         conditions.append(
    #             or_(
    #                 model.tenant_id == effective_tenant,
    #                 model.section_id.in_(
    #                     select(SectionModel.id).where(
    #                         SectionModel.section_type == SectionType.PLATFORM
    #                     )
    #                 ),
    #             )
    #         )

    #     if search:
    #         pattern = f"%{search}%"
    #         conditions.append(
    #             or_(
    #                 model.title.ilike(pattern),
    #                 model.content.ilike(pattern),
    #             )
    #         )

    #     count_stmt = select(func.count()).select_from(model).where(*conditions)
    #     total = (await db.execute(count_stmt)).scalar_one()

    #     stmt = (
    #         select(model)
    #         .where(*conditions)
    #         .order_by(model.created_at.desc(), model.id.desc())
    #         .offset(skip)
    #         .limit(limit)
    #     )

    #     items = list((await db.execute(stmt)).scalars().all())

    #     return items, total

    async def list_for_user(
        self,
        db: AsyncSession,
        *,
        user: UserProtocol,  # ✅ Передаём весь объект пользователя
        skip: int = 0,
        limit: int = 10,
        search: str | None = None,
    ) -> tuple[list[NotesModel], int]:
        """
        Список активных заметок с фильтрацией через AccessService.
        
        Использует SQL-фильтрацию для эффективной работы с большими объёмами данных.
        """
        model = self.model
        
        # Базовые условия
        conditions: list[ColumnElement[bool]] = [model.deleted_at.is_(None)]
        
        # Получаем SQL-фильтр доступа от AccessService
        access_service = get_access_service(db)
        access_filter = await access_service.build_access_filter(user, model)
        
        if access_filter is None:
            # Доступа нет вообще — возвращаем пустой список
            return [], 0
        
        conditions.append(access_filter)
        
        # Поиск по названию и содержимому
        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    model.title.ilike(pattern),
                    model.content.ilike(pattern),
                )
            )
        
        # Подсчёт общего количества
        count_stmt = select(func.count()).select_from(model).where(*conditions)
        total = (await db.execute(count_stmt)).scalar_one()
        
        # Выборка с пагинацией
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
        """
        Одна активная заметка с проверкой доступности.
        
        ✅ Кросс-организационный доступ: документы в разделе "Общий" (platform)
        видны пользователям всех организаций.
        """
        model = self.model

        conditions: list[ColumnElement[bool]] = [
            model.id == note_id,
            model.deleted_at.is_(None),
        ]

        if not is_superadmin:
            # ✅ Документ доступен, если принадлежит своей организации
            # ИЛИ находится в разделе "Общий" (platform)
            conditions.append(
                or_(
                    model.tenant_id == tenant_id,
                    model.section_id.in_(
                        select(SectionModel.id).where(
                            SectionModel.section_type == SectionType.PLATFORM
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
        """Атомарное сохранение с оптимистической блокировкой."""
        model = self.model

        note = await self.get_for_user(
            db,
            note_id=note_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )

        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        # ✅ ЖЁСТКАЯ проверка пессимистической блокировки
        if (
            note.editing_by_user_id is not None
            and note.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
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
                section.tenant_id is not None
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

        # ✅ Кросс-организационный доступ для UPDATE
        conditions: list[ColumnElement[bool]] = [
            model.id == note_id,
            model.version == obj_in.version,
            model.deleted_at.is_(None),
        ]

        if not is_superadmin:
            # ✅ Разрешаем сохранение для своей организации ИЛИ для раздела "Общий"
            conditions.append(
                or_(
                    model.tenant_id == tenant_id,
                    model.section_id.in_(
                        select(SectionModel.id).where(
                            SectionModel.section_type == SectionType.PLATFORM
                        )
                    ),
                )
            )

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

        # ✅ Проверка пессимистической блокировки перед удалением
        if (
            note.editing_by_user_id is not None
            and note.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
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
        """
        Атомарный захват блокировки с учётом таймаута.
        
        ✅ Кросс-организационный доступ: пользователи могут захватывать блокировку
        на документы в разделе "Общий" (platform), даже если документ принадлежит
        другой организации.
        """
        model = self.model

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

        if not is_superadmin:
            # ✅ Кросс-организационный доступ: разрешаем захват для своей организации
            # ИЛИ для раздела "Общий" (platform)
            conditions.append(
                or_(
                    model.tenant_id == tenant_id,
                    model.section_id.in_(
                        select(SectionModel.id).where(
                            SectionModel.section_type == SectionType.PLATFORM
                        )
                    ),
                )
            )

        stmt = (
            update(model)
            .where(*conditions)
            .values(editing_by_user_id=user_id, editing_since=now)
            .returning(model.id)
        )

        locked_id = (await db.execute(stmt)).scalar_one_or_none()

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
        """
        Освобождение блокировки владельцем или суперадмином.
        
        ✅ Кросс-организационный доступ: пользователи могут освобождать блокировку
        на документы в разделе "Общий" (platform).
        """
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