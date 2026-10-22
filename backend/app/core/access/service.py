import uuid
from datetime import datetime
from typing import Protocol, runtime_checkable
from collections.abc import Sequence

from sqlalchemy import ColumnElement, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.core.access.schemas import (
    AccessResult,
    AccessSource,
    ACCESS_LEVEL_NONE,
    ACCESS_LEVEL_READER,
    ACCESS_LEVEL_EDITOR,
    ACCESS_LEVEL_AUTHOR,
    ACCESS_LEVEL_FULL,
    UserProtocol,
)
from app.core.doctypes.models import DoctypeModel
from app.core.roles.models import RoleModel
from app.core.permissions.models import PermissionModel
# from app.core.users.models import UserProtocol
from app.core.sections.models import SectionModel # type: ignore

from sqlalchemy import (
    ColumnElement,
    String,
    and_,
    cast as sql_cast,   # ✅ Алиас, чтобы не конфликтовать с typing.cast
    false,
    literal,
    not_,
    or_,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.sections.models import SectionModel, SectionType


# ✅ Protocol описывает контракт полей документа (миксины DocumentAccessMixin + DocumentLifecycleMixin)
# Это позволяет типизировать параметр без наследования и intersection types
@runtime_checkable
class DocumentProtocol(Protocol):
    """Контракт документа для AccessService (миксины §3.3 + жизненный цикл)."""
    __tablename__: str
    
    # DocumentAccessMixin (ТЗ §3.3)
    tenant_id: uuid.UUID
    section_id: uuid.UUID
    author_id: uuid.UUID
    or_tags: list[str] | None
    and_tags: list[str] | None
    
    # DocumentLifecycleMixin
    version: int
    editing_by_user_id: uuid.UUID | None
    editing_since: datetime | None
    doc_status: str
    doc_number: str | None
    doc_date: datetime | None
    deleted_at: datetime | None
    
    # Первичный ключ
    id: uuid.UUID

# ✅ Protocol для КЛАССА модели документа
# Описывает дескрипторы SQLAlchemy (Mapped-колонки) на уровне класса,
# которые используются для построения SQL-выражений (WHERE clause).
class DocumentClassProtocol(Protocol):
    """Контракт КЛАССА модели документа для построения SQL-фильтра."""

    __tablename__: str
    id: Mapped[uuid.UUID]
    tenant_id: Mapped[uuid.UUID]
    section_id: Mapped[uuid.UUID]
    author_id: Mapped[uuid.UUID]
    or_tags: Mapped[list[str] | None]
    and_tags: Mapped[list[str] | None]
    version: Mapped[int]
    deleted_at: Mapped[datetime | None]

class AccessService:
    """
    Сервис вычисления доступа к документам (ТЗ §8).
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db

# == new 22.10.2026 ========    
    async def resolve_access(
        self,
        user: UserProtocol,
        document: DocumentProtocol,
        now: datetime | None = None,
    ) -> AccessResult:
        """Вычисление доступа по ТЗ §8.2 с учётом Варианта D."""

        denied = AccessResult(
            visible=False,
            level=ACCESS_LEVEL_NONE,
            can_delete=False,
            source=AccessSource.NONE,
        )

        # --- Раздел документа -------------------------------------------------
        section: SectionModel | None = await self._get_section(document.section_id)
        if section is None:
            return denied

        is_platform: bool = section.section_type == SectionType.PLATFORM

        # --- ШАГ 1. ТЕНАНТ (§3.1) + исключение platform (Вариант D) -------------
        if (
            document.tenant_id != user.tenant_id
            and not user.is_superadmin
            and not is_platform
        ):
            return denied

        # --- ШАГ 2–3. РОЛИ / РАЗДЕЛЫ / PERMISSION ------------------------------
        doctype: str = self._get_doctype(document)
        candidates: list[tuple[RoleModel, PermissionModel]] = (
            await self._load_candidates(user, doctype)
        )
        if not candidates:
            return denied

        # --- ШАГ 4. МАКСИМАЛЬНЫЙ УРОВЕНЬ ---------------------------------------
        max_level: int = ACCESS_LEVEL_NONE
        can_delete: bool = False

        for role, permission in candidates:
            if document.section_id not in (role.section_ids or []):
                continue  # §3.2.5

            level: int = self._role_level(
                permission, is_author=(document.author_id == user.id)
            )
            max_level = max(max_level, level)
            can_delete = can_delete or permission.can_delete  # §5.2.3

        # Нет уровня чтения — записи для пользователя не существует (§2.3)
        if max_level < ACCESS_LEVEL_READER:
            return denied

        # --- ШАГ 5. ПЕРЕКЛЮЧАТЕЛИ ТИПА ДОКУМЕНТА (§7) ---------------------------
        doctype_model: DoctypeModel | None = await self._get_doctype_model(doctype)
        if doctype_model is None:
            return denied

        or_enforced: bool = doctype_model.apply_or_tags
        and_enforced: bool = doctype_model.apply_and_tags

        # --- ШАГ 6. ПРАВИЛО «НЕТ ТЕГОВ» (§6.6) ----------------------------------
        doc_or_tags: list[str] = list(document.or_tags or [])
        doc_and_tags: list[str] = list(document.and_tags or [])

        untagged: bool = (or_enforced and not doc_or_tags) or (
            and_enforced and not doc_and_tags
        )

        if untagged and max_level < ACCESS_LEVEL_FULL:
            return denied

        # --- ШАГ 7. ГЛОБАЛЬНАЯ ТЕГ-ПРОВЕРКА (§6.7) ------------------------------
        if not untagged:
            user_tags: list[str] = list(user.tags or [])
            if not self._check_tags(
                user_tags, doc_or_tags, doc_and_tags, or_enforced, and_enforced
            ):
                return denied

        # --- ШАГ 8. ДЕЛЕГИРОВАНИЕ (§11) — пока не реализовано -------------------

        # --- ШАГ 9. ФИНАЛ: видимось пройдена, вычисляем возможности -------------
        if is_platform and not user.is_superadmin:
            # Потолок чтения: автор/редактор/полный в «Общем» не дают записи
            max_level = ACCESS_LEVEL_READER
            can_delete = False
        else:
            # Автоматическое право удаления при уровне >= 2 (§5.2, расширение ТЗ)
            can_delete = can_delete or (max_level >= ACCESS_LEVEL_EDITOR)

        return AccessResult(
            visible=True,
            level=max_level,
            can_delete=can_delete,
            source=AccessSource.ROLE,
        )
# ==========================
#         
    def _check_tags(
        self,
        user_tags: list[str],
        doc_or_tags: list[str],
        doc_and_tags: list[str],
        or_enforced: bool,
        and_enforced: bool,
    ) -> bool:
        """Проверка тегов (ТЗ §6.7)."""
        if and_enforced and len(doc_and_tags) > 0:
            if not all(tag in user_tags for tag in doc_and_tags):
                return False
        
        if or_enforced and len(doc_or_tags) > 0:
            if not any(tag in user_tags for tag in doc_or_tags):
                return False
        
        return True
    
    def _get_doctype(self, document: DocumentProtocol) -> str:
        """Получает код типа документа из модели."""
        return document.__tablename__
    
    async def _get_doctype_model(self, doctype: str) -> DoctypeModel | None:
        """Загружает модель типа документа из БД."""
        query = select(DoctypeModel).where(DoctypeModel.doctype == doctype)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

# == new 22.10.2026 ===================    
    async def build_access_filter(
        self,
        user: UserProtocol,
        document_model: type[DocumentClassProtocol],
        now: datetime | None = None,
    ) -> ColumnElement[bool] | None:
        """
        SQL-условие видимости для списка документов.

        Возвращает None только если доступа нет вообще.
        Для Суперадмина НЕ возвращает None: он проходит те же слои,
        кроме проверки тенанта (§2.5, §3.1.3).
        """
        doctype: str = document_model.__tablename__

        candidates: list[tuple[RoleModel, PermissionModel]] = (
            await self._load_candidates(user, doctype)
        )
        if not candidates:
            return None

        # --- Агрегация конфигурации ролей (НЕ документов) ----------------------
        section_levels: dict[uuid.UUID, int] = {}
        author_sections: set[uuid.UUID] = set()

        for role, permission in candidates:
            # Без привязки к конкретному документу уровень автора не присваиваем
            base_level: int = self._role_level(permission, is_author=False)

            for section_id in role.section_ids or []:
                section_levels[section_id] = max(
                    section_levels.get(section_id, ACCESS_LEVEL_NONE), base_level
                )
                if permission.author:
                    author_sections.add(section_id)

        readable_sections: list[uuid.UUID] = [
            sid
            for sid, level in section_levels.items()
            if level >= ACCESS_LEVEL_READER
        ]
        full_sections: list[uuid.UUID] = [
            sid
            for sid, level in section_levels.items()
            if level >= ACCESS_LEVEL_FULL
        ]

        if not readable_sections and not author_sections:
            return None

        # --- Видимость по Разделам + уровню чтения -----------------------------
        visibility_parts: list[ColumnElement[bool]] = []

        if readable_sections:
            visibility_parts.append(document_model.section_id.in_(readable_sections))

        if author_sections:
            # Уровень «Автор» даёт видимость ТОЛЬКО своих документов
            visibility_parts.append(
                and_(
                    document_model.section_id.in_(sorted(author_sections)),
                    document_model.author_id == user.id,
                )
            )

        visibility: ColumnElement[bool] = or_(*visibility_parts)

        # --- ТЕНАНТ с исключением platform -----------------------------------
        tenant_condition: ColumnElement[bool] = true()

        if not user.is_superadmin:
            platform_sections = select(SectionModel.id).where(
                SectionModel.section_type == SectionType.PLATFORM
            )
            tenant_condition = or_(
                document_model.tenant_id == user.tenant_id,
                document_model.section_id.in_(platform_sections),
            )

        # --- ПЕРЕКЛЮЧАТЕЛИ ТИПА ДОКУМЕНТА --------------------------------------
        doctype_model: DoctypeModel | None = await self._get_doctype_model(doctype)
        if doctype_model is None:
            return None

        or_enforced: bool = doctype_model.apply_or_tags
        and_enforced: bool = doctype_model.apply_and_tags

        if not or_enforced and not and_enforced:
            return and_(tenant_condition, visibility)

        # --- ТЕГИ на уровне SQL ------------------------------------------------
        or_empty: ColumnElement[bool] = self._is_empty_tags(document_model.or_tags)
        and_empty: ColumnElement[bool] = self._is_empty_tags(document_model.and_tags)

        untagged_parts: list[ColumnElement[bool]] = []
        if or_enforced:
            untagged_parts.append(or_empty)
        if and_enforced:
            untagged_parts.append(and_empty)

        untagged: ColumnElement[bool] = (
            or_(*untagged_parts) if untagged_parts else false()
        )

        user_tags: list[str] = list(user.tags or [])
        tags_pass_parts: list[ColumnElement[bool]] = []

        if user_tags:
            # ✅ Аннотация изменена на ColumnElement[Sequence[str]].
            # literal() возвращает BindParameter[Sequence[str]], потому что
            # в тайп-стабах SQLAlchemy тип ARRAY имеет параметр Sequence.
            # ColumnElement инвариантен — типы должны совпадать точно.
            user_tags_sql: ColumnElement[Sequence[str]] = literal(
                user_tags, type_=ARRAY(String)
            )

            if or_enforced:
                # document.or_tags ∩ user.tags ≠ ∅
                tags_pass_parts.append(
                    or_(or_empty, document_model.or_tags.op("&&")(user_tags_sql))
                )
            if and_enforced:
                # document.and_tags ⊆ user.tags
                tags_pass_parts.append(
                    or_(and_empty, document_model.and_tags.op("<@")(user_tags_sql))
                )
        else:
            # Тегов у пользователя нет → прошли только документы без соответствующих тегов
            if or_enforced:
                tags_pass_parts.append(or_empty)
            if and_enforced:
                tags_pass_parts.append(and_empty)

        tags_pass: ColumnElement[bool] = (
            and_(*tags_pass_parts) if tags_pass_parts else true()
        )

        full_condition: ColumnElement[bool] = (
            document_model.section_id.in_(full_sections)
            if full_sections
            else false()
        )

        # --- СБОРКА -------------------------------------------------------------
        # Безтеговый документ виден только при ролевом уровне 4 (§6.6).
        # Заполненный — только при пройденной тег-проверке (§6.7).
        return and_(
            tenant_condition,
            visibility,
            or_(
                and_(untagged, full_condition),
                and_(not_(untagged), tags_pass),
            ),
        )

    async def _get_section(self, section_id: uuid.UUID) -> SectionModel | None:
        """Загружает раздел документа (нужен его section_type)."""
        stmt = select(SectionModel).where(SectionModel.id == section_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _load_candidates(
        self,
        user: UserProtocol,
        doctype: str,
    ) -> list[tuple[RoleModel, PermissionModel]]:
        """
        ШАГ 2–3: активные роли с явными Разделами и Permission для типа.

        Permission всегда принадлежит Организации РОЛИ (§43),
        поэтому сравниваем perm.tenant_id с user.tenant_id,
        а НЕ с tenant_id документа. Это позволяет роли Организации Б
        давать чтение документов Организации А в разделе «Общий».
        """
        role_ids: list[uuid.UUID] = list(user.role_ids or [])
        if not role_ids:
            return []

        stmt = (
            select(RoleModel)
            .where(RoleModel.id.in_(role_ids))
            .options(selectinload(RoleModel.permissions))
        )
        roles = (await self.db.execute(stmt)).scalars().all()

        candidates: list[tuple[RoleModel, PermissionModel]] = []

        for role in roles:
            if not role.section_ids:
                continue  # §4.2.1: роль без Разделов недействующая

            permissions: list[PermissionModel] = list(role.permissions)
            permission: PermissionModel | None = None

            for perm in permissions:
                if perm.doctype == doctype and perm.tenant_id == user.tenant_id:
                    permission = perm
                    break

            if permission is None:
                continue  # §3.4.2

            candidates.append((role, permission))

        return candidates

    @staticmethod
    def _role_level(permission: PermissionModel, is_author: bool) -> int:
        """
        Уровень роли. Автор (3) учитывается только для собственных документов.
        """
        if permission.full_access:
            return ACCESS_LEVEL_FULL
        if is_author and permission.author:
            return ACCESS_LEVEL_AUTHOR
        if permission.editor:
            return ACCESS_LEVEL_EDITOR
        if permission.reader:
            return ACCESS_LEVEL_READER
        return ACCESS_LEVEL_NONE

    @staticmethod
    def _is_empty_tags(
        column: InstrumentedAttribute[list[str] | None],
    ) -> ColumnElement[bool]:
        """
        NULL и пустой массив трактуются одинаково: тегов нет.

        Используется в SQL-фильтре для проверки правила «нет тегов» (§6.6).
        """
        empty_tags: list[str] = []
        # ✅ Аннотация изменена на ColumnElement[Sequence[str]]
        # sql_cast возвращает Cast[Sequence[str]], потому что в тайп-стабах
        # SQLAlchemy тип ARRAY имеет параметр Sequence, а не list.
        # ColumnElement инвариантен, поэтому типы должны совпадать точно.
        empty_array: ColumnElement[Sequence[str]] = sql_cast(
            empty_tags,
            ARRAY(String),
        )
        return or_(
            column.is_(None),            # массив равен NULL
            column.op("=")(empty_array), # массив равен []
        )
# ====================================


def get_access_service(db: AsyncSession) -> AccessService:
    """Фабрика для создания AccessService."""
    return AccessService(db)

