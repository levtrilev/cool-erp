"""CRUD для заметок с блокировками (Правило №40) и контролем доступа (ТЗ RBAC/ABAC §8)."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any # pyright: ignore[reportUnusedImport]
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from typing import cast as typing_cast

from app.core.access.service import AccessService, DocumentProtocol
from app.core.access.schemas import AccessResult, UserProtocol
from app.core.crud.base import CRUDBase
from app.core.doctypes.document_base import EDITING_LOCK_TIMEOUT_MINUTES
from app.core.notes.exceptions import (
    NoteEditingLockedError,
    NoteNotFoundError,
    NotePermissionError,
    NoteVersionConflictError,
    SectionNotInTenantError,
)
from app.core.notes.models import NotesModel
from app.core.notes.schemas import NoteCreateSchema, NoteUpdateSchema
from app.core.sections.models import SectionModel, SectionType

from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy import and_
from app.core.notes.schemas import NoteSortField, SortOrder

# if TYPE_CHECKING:
#     from app.core.users.models import UserModel


class CRUDNote(CRUDBase[NotesModel, NoteCreateSchema, NoteUpdateSchema]):
    """CRUD для заметок с блокировками и контролем доступа."""

    # ==================================================================
    # ВСПОМОГАТЕЛЬНЫЙ МЕТОД: проверка доступа к одиночной записи
    # ==================================================================
    async def _ensure_visible_for_user(
        self,
        db: AsyncSession,
        *,
        note: NotesModel,
        user: UserProtocol,
    ) -> None:
        """
        Проверка видимости заметки для пользователя через AccessService.
        Если запись не видна — поднимает NoteNotFoundError (ТЗ §2.3, §2.6:
        'запись не существует для пользователя').
        """
        access_service = AccessService(db)
        note_doc: DocumentProtocol = typing_cast("DocumentProtocol", note)
        access = await access_service.resolve_access(user, note_doc)
        if not access.visible:
            raise NoteNotFoundError("Заметка не найдена")

    # ==================================================================
    # СПИСОК (ТЗ §2.6 — RLS-семантика: скрытые записи не возвращаются)
    # ==================================================================
    # async def get_multi(
    #     self,
    #     db: AsyncSession,
    #     *,
    #     user: UserProtocol,
    #     tenant_id: uuid.UUID,
    #     is_superadmin: bool = False,
    #     skip: int = 0,
    #     limit: int = 100,
    #     search: str | None = None,
    # ) -> tuple[list[NotesModel], int]:
    #     """
    #     Список заметок с контролем доступа через AccessService.
    #     Фильтр включает ВСЕ 5 слоёв ТЗ RBAC/ABAC §3:
    #       Слой 1 (тенант) + Слой 2 (разделы роли) + Слой 3 (doctype/permission)
    #       + Слой 4 (теги) + Слой 5 (уровень ≥ 1 для видимости).
    #     """
    #     model = self.model
    #     base_where = model.deleted_at.is_(None)

    #     # ✅ КРИТИЧНО: SQL-фильтр видимости через AccessService
    #     access_service = AccessService(db)
    #     access_filter = await access_service.build_access_filter(user, model)
    #     if access_filter is None:
    #         return [], 0

    #     stmt = select(model).where(base_where, access_filter)
    #     count_stmt = (
    #         select(func.count())
    #         .select_from(model)
    #         .where(base_where, access_filter)
    #     )

    #     # Поиск по тексту (применяется поверх фильтра доступа)
    #     if search:
    #         pattern: str = f"%{search}%"
    #         search_cond = or_(
    #             model.title.ilike(pattern),
    #             model.content.ilike(pattern),
    #         )
    #         stmt = stmt.where(search_cond)
    #         count_stmt = count_stmt.where(search_cond)

    #     total: int = (await db.execute(count_stmt)).scalar_one() or 0
    #     stmt = stmt.order_by(model.created_at.desc(), model.id.desc()).offset(skip).limit(limit)
    #     items: list[NotesModel] = list((await db.execute(stmt)).scalars().all())
    #     return items, total

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
        sort_by: NoteSortField | None = None,
        sort_order: SortOrder = SortOrder.ASC,
        filter_title: str | None = None,
        filter_doc_number: str | None = None,
        filter_doc_date: date | None = None,
        filter_doc_status: str | None = None,
        filter_section_name: str | None = None,
        filter_updated_at: date | None = None,
    ) -> tuple[list[NotesModel], int]:
        """
        Список заметок с контролем доступа, сортировкой и фильтрацией.
        Фильтр доступа включает ВСЕ 5 слоёв ТЗ RBAC/ABAC §3.
        Сортировка и фильтры колонок выполняются на уровне SQL
        (Бэкенд Правило №26: фильтрация в SQL, не в памяти).
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

        # JOIN с sections нужен только при фильтре/сортировке по имени раздела
        if filter_section_name is not None:
            stmt = stmt.join(SectionModel, model.section_id == SectionModel.id)
            count_stmt = count_stmt.join(
                SectionModel, model.section_id == SectionModel.id
            )
        elif sort_by == NoteSortField.SECTION_NAME:
            stmt = stmt.join(SectionModel, model.section_id == SectionModel.id)

        # Глобальный поиск (поверх фильтра доступа)
        if search:
            pattern: str = f"%{search}%"
            search_cond = or_(
                model.title.ilike(pattern),
                model.content.ilike(pattern),
            )
            stmt = stmt.where(search_cond)
            count_stmt = count_stmt.where(search_cond)

        # ── ФИЛЬТРЫ ПО КОЛОНКАМ ─────────────────────────────────────
        if filter_title:
            cond = model.title.ilike(f"%{filter_title}%")
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_doc_number:
            cond = model.doc_number.ilike(f"%{filter_doc_number}%")
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_doc_date is not None:
            cond = model.doc_date == filter_doc_date
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_doc_status:
            cond = model.doc_status == filter_doc_status
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if filter_section_name:
            cond = SectionModel.name.ilike(f"%{filter_section_name}%")
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

        total: int = (await db.execute(count_stmt)).scalar_one() or 0

        # ── СОРТИРОВКА (whitelist через Enum) ───────────────────────
        ascending: bool = sort_order == SortOrder.ASC
        if sort_by == NoteSortField.TITLE:
            stmt = stmt.order_by(
                model.title.asc() if ascending else model.title.desc()
            )
        elif sort_by == NoteSortField.DOC_NUMBER:
            stmt = stmt.order_by(
                model.doc_number.asc() if ascending else model.doc_number.desc()
            )
        elif sort_by == NoteSortField.DOC_DATE:
            stmt = stmt.order_by(
                model.doc_date.asc() if ascending else model.doc_date.desc()
            )
        elif sort_by == NoteSortField.DOC_STATUS:
            stmt = stmt.order_by(
                model.doc_status.asc() if ascending else model.doc_status.desc()
            )
        elif sort_by == NoteSortField.SECTION_NAME:
            stmt = stmt.order_by(
                SectionModel.name.asc() if ascending else SectionModel.name.desc()
            )
        elif sort_by == NoteSortField.UPDATED_AT:
            stmt = stmt.order_by(
                model.updated_at.asc() if ascending else model.updated_at.desc()
            )
        else:
            # Порядок по умолчанию: новые сверху
            stmt = stmt.order_by(model.created_at.desc())
        # Вторичная сортировка для стабильной пагинации
        stmt = stmt.order_by(model.id.asc())

        stmt = stmt.offset(skip).limit(limit)
        items: list[NotesModel] = list((await db.execute(stmt)).scalars().all())
        return items, total

    # ==================================================================
    # ОДНОЧНАЯ ЗАПИСЬ (ТЗ §2.3 — нет права на чтение ⇒ 404)
    # ==================================================================
    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        note_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> NotesModel | None:
        """
        Получение заметки с контролем доступа.
        Возвращает None, если запись не видна пользователю (ТЗ §2.3).
        """
        model = self.model
        stmt = select(model).where(
            model.id == note_id,
            model.deleted_at.is_(None),
        )
        # Базовая тенантная фильтрация остаётся как дополнительная защита
        if not is_superadmin:
            stmt = stmt.where(model.tenant_id == tenant_id)

        note = (await db.execute(stmt)).scalar_one_or_none()
        if note is None:
            return None

        # ✅ Проверка доступа через AccessService (все 5 слоёв)
        access_service = AccessService(db)
        note_doc: DocumentProtocol = typing_cast("DocumentProtocol", note)
        access = await access_service.resolve_access(user, note_doc)
        if not access.visible:
            return None
        return note

    # ==================================================================
    # СОЗДАНИЕ (ТЗ §5 — создание требует уровень ≥ 2)
    # ==================================================================
    async def create_for_user(
        self,
        db: AsyncSession,
        *,
        obj_in: NoteCreateSchema,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> NotesModel:
        """Создание заметки с заполнением контракта из сессии."""
        model = self.model

        # Проверка доступности раздела
        section_stmt = select(SectionModel).where(SectionModel.id == obj_in.section_id)
        section = (await db.execute(section_stmt)).scalar_one_or_none()
        if section is None:
            raise SectionNotInTenantError("Раздел не найден")

        # ✅ Вариант D: создание в «Общем» — только Суперадмин
        if section.section_type == SectionType.PLATFORM and not is_superadmin:
            raise NotePermissionError(
                "Создание документов в разделе «Общий» доступно только Суперадмину"
            )

        # Раздел должен быть либо платформенный, либо принадлежать организации пользователя
        if (
            section.tenant_id is not None
            and section.tenant_id != tenant_id
            and not is_superadmin
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
            author_id=user.id,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )

        # ✅ Проверка права на создание через AccessService
        access_service = AccessService(db)
        note_doc: DocumentProtocol = typing_cast("DocumentProtocol", note)
        access: AccessResult = await access_service.resolve_access(user, note_doc)
        if access.level < 2:
            raise NotePermissionError("Нет права на создание заметки")

        db.add(note)
        await db.flush()
        await db.refresh(note)
        return note

    # ==================================================================
    # БЛОКИРОВКИ (Правило №40, часть 3) + контроль доступа
    # ==================================================================
    async def acquire_editing_lock(
        self,
        db: AsyncSession,
        *,
        note_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> NotesModel:
        """Атомарный захват блокировки с учётом таймаута и контроля доступа."""
        model = self.model

        # 1. СНАЧАЛА проверяем доступ
        note = await self.get_for_user(
            db,
            note_id=note_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        # 2. ✅ КРИТИЧНО: Проверяем уровень доступа для блокировки (требуется >= 2)
        access_service = AccessService(db)
        note_doc: DocumentProtocol = typing_cast("DocumentProtocol", note)
        access: AccessResult = await access_service.resolve_access(user, note_doc)
        if access.level < 2:
            raise NotePermissionError("Недостаточно прав для редактирования заметки")

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)

        # ✅ Правило №40, часть 3.2: РОВНО ДВА условия для захвата
        conditions: list[ColumnElement[bool]] = [
            model.id == note_id,
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
            # Повторная проверка
            note = await self.get_for_user(
                db,
                note_id=note_id,
                user=user,
                tenant_id=tenant_id,
                is_superadmin=is_superadmin,
            )
            if note is None:
                raise NoteNotFoundError("Заметка не найдена")
            raise NoteEditingLockedError("Заметка уже редактируется")

        note = await self.get_for_user(
            db,
            note_id=note_id,
            user=user,
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
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> NotesModel:
        """Освобождение блокировки владельцем или суперадмином."""
        note = await self.get_for_user(
            db,
            note_id=note_id,
            user=user,
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

    # ==================================================================
    # СОХРАНЕНИЕ С ВЕРСИЕЙ (Правило №40, часть 5) + контроль доступа
    # ==================================================================

    async def save_with_version(
        self,
        db: AsyncSession,
        *,
        note_id: uuid.UUID,
        obj_in: NoteUpdateSchema,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> NotesModel:
        """Сохранение с проверкой обеих блокировок и контроля доступа."""
        model = self.model

        note = await self.get_for_user(
            db,
            note_id=note_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        # ✅ Проверка уровня доступа: изменение требует минимум level >= 2
        access_service = AccessService(db)
        note_doc: DocumentProtocol = typing_cast("DocumentProtocol", note)
        access = await access_service.resolve_access(user, note_doc)

        # level >= 2 означает «автор своей записи» или выше.
        # ТЗ §5.1: автор (2) может изменять только свои, редактор (3) — любые.
        if access.level < 2:
            raise NoteNotFoundError("Заметка не найдена")

        # ✅ Правило №40, часть 5.2: ЖЁСТКАЯ проверка пессимистической блокировки
        if (
            note.editing_by_user_id is not None
            and note.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if note.editing_since is None or note.editing_since > cutoff:
                raise NoteEditingLockedError(
                    "Заметка заблокирована другим пользователем для редактирования"
                )

        # Проверка доступности нового раздела (если меняется)
        if obj_in.section_id is not None and obj_in.section_id != note.section_id:
            section_stmt = select(SectionModel).where(SectionModel.id == obj_in.section_id)
            section = (await db.execute(section_stmt)).scalar_one_or_none()
            if section is None or (
                section.tenant_id is not None
                and section.tenant_id != tenant_id
            ):
                raise SectionNotInTenantError("Раздел недоступен в этой организации")

            # ✅ Вариант D: перемещение в «Общий» — только Суперадмин
            if section.section_type == SectionType.PLATFORM and not is_superadmin:
                raise NotePermissionError(
                    "Перемещение документа в раздел «Общий» доступно только Суперадмину"
                )

        values: dict[str, Any] = obj_in.model_dump(exclude_unset=True, exclude={"version"})
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
                "Заметка изменена другим пользователем. Обновите данные."
            )

        await db.flush()
        await db.refresh(note)
        return note

    # ==================================================================
    # МЯГКОЕ УДАЛЕНИЕ (Правило №40, часть 6) + контроль доступа
    # ==================================================================
    async def mark_deleted(
        self,
        db: AsyncSession,
        *,
        note_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> NotesModel:
        """Мягкое удаление с проверкой блокировки и контроля доступа."""
        note = await self.get_for_user(
            db,
            note_id=note_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if note is None:
            raise NoteNotFoundError("Заметка не найдена")

        # ✅ Проверка права на удаление
        access_service = AccessService(db)
        note_doc: DocumentProtocol = typing_cast("DocumentProtocol", note)
        access = await access_service.resolve_access(user, note_doc)
        if not access.can_delete:
            raise NoteNotFoundError("Заметка не найдена")

        # ✅ Правило №40, часть 6.1: проверка блокировки перед удалением
        if (
            note.editing_by_user_id is not None
            and note.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if note.editing_since is None or note.editing_since > cutoff:
                raise NoteEditingLockedError(
                    "Заметка заблокирована другим пользователем и не может быть удалена"
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


crud_note = CRUDNote(NotesModel)