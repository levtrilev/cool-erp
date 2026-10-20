import uuid
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from sqlalchemy import ColumnElement, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, selectinload

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
    
    async def resolve_access(
        self,
        user: UserProtocol,
        document: DocumentProtocol,  # ✅ Protocol вместо Base
        now: datetime | None = None,
    ) -> AccessResult:
        """
        Вычисляет доступ пользователя к документу (ТЗ §8.2).
        
        Args:
            user: Пользователь, запрашивающий доступ
            document: Документ, соответствующий DocumentProtocol
            now: Текущее время (UTC). Если None, используется datetime.now(timezone.utc)
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        # ШАГ 1. ТЕНАНТ (ТЗ §3.1)
        if document.tenant_id != user.tenant_id and not user.is_superadmin:
            return AccessResult(
                visible=False,
                level=ACCESS_LEVEL_NONE,
                can_delete=False,
                source=AccessSource.NONE,
            )
        
        # ШАГ 2. ДЕЙСТВУЮЩИЕ НАЗНАЧЕНИЯ РОЛЕЙ (ТЗ §10)
        role_ids = user.role_ids or []
        
        if not role_ids:
            return AccessResult(
                visible=False,
                level=ACCESS_LEVEL_NONE,
                can_delete=False,
                source=AccessSource.NONE,
            )
        
        # Загружаем роли с permissions
        roles_query = (
            select(RoleModel)
            .where(RoleModel.id.in_(role_ids))
            .options(selectinload(RoleModel.permissions))
        )
        roles_result = await self.db.execute(roles_query)
        roles = roles_result.scalars().all()
        
        # ШАГ 3. КАНДИДАТЫ-РОЛИ
        candidates: list[tuple[RoleModel, PermissionModel]] = []
        doctype = self._get_doctype(document)
        
        for role in roles:
            if not role.section_ids:
                continue
            if document.section_id not in role.section_ids:
                continue
            
            permission: PermissionModel | None = None
            for perm in role.permissions:
                if perm.doctype == doctype and perm.tenant_id == user.tenant_id:
                    permission = perm
                    break
            
            if permission is None:
                continue
            
            candidates.append((role, permission))
        
        if not candidates:
            return AccessResult(
                visible=False,
                level=ACCESS_LEVEL_NONE,
                can_delete=False,
                source=AccessSource.NONE,
            )
        
        # ШАГ 4. МАКСИМАЛЬНЫЙ УРОВЕНЬ
        max_level = ACCESS_LEVEL_NONE
        can_delete = False
        
        for role, permission in candidates:
            level = ACCESS_LEVEL_NONE
            
            if permission.full_access:
                level = ACCESS_LEVEL_FULL
            elif permission.author and document.author_id == user.id:
                level = ACCESS_LEVEL_AUTHOR
            elif permission.editor:
                level = ACCESS_LEVEL_EDITOR
            elif permission.reader:
                level = ACCESS_LEVEL_READER
            
            max_level = max(max_level, level)
            can_delete = can_delete or permission.can_delete
        
        # ШАГ 5. ПЕРЕКЛЮЧАТЕЛИ ТИПА ДОКУМЕНТА
        doctype_model = await self._get_doctype_model(doctype)
        
        if doctype_model is None:
            return AccessResult(
                visible=False,
                level=ACCESS_LEVEL_NONE,
                can_delete=False,
                source=AccessSource.NONE,
            )
        
        or_enforced = doctype_model.apply_or_tags
        and_enforced = doctype_model.apply_and_tags
        
        # ШАГ 6. ПРАВИЛО "НЕТ ТЕГОВ"
        doc_or_tags = document.or_tags or []
        doc_and_tags = document.and_tags or []
        
        untagged = (
            (or_enforced and len(doc_or_tags) == 0) or
            (and_enforced and len(doc_and_tags) == 0)
        )
        
        if untagged:
            if max_level == ACCESS_LEVEL_FULL:
                return AccessResult(
                    visible=True,
                    level=ACCESS_LEVEL_FULL,
                    can_delete=can_delete,
                    source=AccessSource.ROLE,
                )
            else:
                return AccessResult(
                    visible=False,
                    level=ACCESS_LEVEL_NONE,
                    can_delete=False,
                    source=AccessSource.NONE,
                )
        
        # ШАГ 7. ТЕГ-ПРОВЕРКА
        max_level_via_roles = False
        
        if max_level >= ACCESS_LEVEL_READER:
            user_tags = user.tags or []
            if self._check_tags(user_tags, doc_or_tags, doc_and_tags, or_enforced, and_enforced):
                max_level_via_roles = True
        
        # ШАГ 8. ДЕЛЕГИРОВАНИЕ (TODO)
        # Пока пропускаем
        
        # ШАГ 9. ФИНАЛ
        if max_level_via_roles:
            return AccessResult(
                visible=True,
                level=max_level,
                can_delete=can_delete,
                source=AccessSource.ROLE,
            )
        
        return AccessResult(
            visible=False,
            level=ACCESS_LEVEL_NONE,
            can_delete=False,
            source=AccessSource.NONE,
        )
    
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

    
    async def build_access_filter(
        self,
        user: UserProtocol,
        document_model: type[DocumentClassProtocol],
        now: datetime | None = None,
    ) -> ColumnElement[bool] | None:
        """
        Строит SQL-условие для фильтрации списка документов по доступу.
        
        Используется в list_for_user для эффективной фильтрации на уровне БД
        без итерирования в Python.
        
        Args:
            user: Пользователь, запрашивающий доступ
            document_model: Класс модели документа (например, NotesModel)
            now: Текущее время (UTC)
        
        Returns:
            SQL-условие WHERE или None (если доступа нет вообще)
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        # ШАГ 1: ТЕНАНТ
        tenant_conditions: list[ColumnElement[bool]] = []
        
        if not user.is_superadmin:
            tenant_conditions.append(document_model.tenant_id == user.tenant_id)
        else:
            # Суперадмин видит все тенанты — условие не добавляется
            return None  # Нет ограничений по тенанту
        
        # ШАГ 2: ДЕЙСТВУЮЩИЕ НАЗНАЧЕНИЯ РОЛЕЙ
        role_ids = user.role_ids or []
        
        if not role_ids:
            # Нет ролей — доступа нет
            return None
        
        # Загружаем роли с permissions
        roles_query = (
            select(RoleModel)
            .where(RoleModel.id.in_(role_ids))
            .options(selectinload(RoleModel.permissions))
        )
        roles_result = await self.db.execute(roles_query)
        roles = roles_result.scalars().all()
        
        # ШАГ 3: КАНДИДАТЫ-РОЛИ
        valid_section_ids: list[uuid.UUID] = []
        valid_doctypes: list[str] = []
        
        doctype = document_model.__tablename__
        
        for role in roles:
            if not role.section_ids:
                continue
            
            # Проверяем наличие Permission для данного doctype
            has_permission = False
            for perm in role.permissions:
                if perm.doctype == doctype and perm.tenant_id == user.tenant_id:
                    has_permission = True
                    break
            
            if not has_permission:
                continue
            
            # Роль валидна — добавляем её section_ids
            valid_section_ids.extend(role.section_ids)
            valid_doctypes.append(doctype)
        
        if not valid_section_ids:
            # Нет валидных ролей — доступа нет
            return None
        
        # Удаляем дубликаты
        valid_section_ids = list(set(valid_section_ids))
        
        # ШАГ 4: Построение SQL-условия
        # Документ доступен, если:
        # 1. tenant_id совпадает (уже добавлено в tenant_conditions)
        # 2. section_id в списке доступных разделов
        section_condition = document_model.section_id.in_(valid_section_ids)
        
        # ШАГ 5: ПЕРЕКЛЮЧАТЕЛИ ТИПА ДОКУМЕНТА и ТЕГИ
        doctype_model = await self._get_doctype_model(doctype)
        
        if doctype_model is None:
            return None
        
        or_enforced = doctype_model.apply_or_tags
        and_enforced = doctype_model.apply_and_tags
        
        # Если теги не применяются — простая фильтрация
        if not or_enforced and not and_enforced:
            return and_(*tenant_conditions, section_condition)
        
        # Если теги применяются — добавляем условия для тегов
        # Правило 6.6: документ без тегов виден только уровню 4
        # Правило 6.7: проверка тегов для заполненных значений
        
        user_tags = user.tags or []
        
        # Условие для документов с заполненными тегами
        tags_conditions: list[ColumnElement[bool]] = []
        
        # AND-теги: пользователь должен иметь ВСЕ теги
        if and_enforced:
            # document.and_tags ⊆ user_tags
            # SQL: array_length(document.and_tags - user_tags, 1) IS NULL
            # или: document.and_tags <@ user_tags (оператор containment)
            if user_tags:
                # Пользователь имеет теги — проверяем containment
                from sqlalchemy.dialects.postgresql import array
                user_tags_array = array(user_tags)
                and_tags_condition = document_model.and_tags.op("<@")(user_tags_array)
                tags_conditions.append(
                    or_(
                        document_model.and_tags.is_(None),
                        document_model.and_tags == [],
                        and_tags_condition,
                    )
                )
            else:
                # Пользователь без тегов — видит только документы без and_tags
                tags_conditions.append(
                    or_(
                        document_model.and_tags.is_(None),
                        document_model.and_tags == [],
                    )
                )
        
        # OR-теги: пользователь должен иметь ХОТЯ БЫ ОДИН тег
        if or_enforced:
            # document.or_tags ∩ user_tags ≠ ∅
            # SQL: document.or_tags && user_tags (оператор overlap)
            if user_tags:
                from sqlalchemy.dialects.postgresql import array
                user_tags_array = array(user_tags)
                or_tags_condition = document_model.or_tags.op("&&")(user_tags_array)
                tags_conditions.append(
                    or_(
                        document_model.or_tags.is_(None),
                        document_model.or_tags == [],
                        or_tags_condition,
                    )
                )
            else:
                # Пользователь без тегов — видит только документы без or_tags
                tags_conditions.append(
                    or_(
                        document_model.or_tags.is_(None),
                        document_model.or_tags == [],
                    )
                )
        
        # Комбинируем все условия
        all_conditions = tenant_conditions + [section_condition] + tags_conditions
        
        return and_(*all_conditions)



def get_access_service(db: AsyncSession) -> AccessService:
    """Фабрика для создания AccessService."""
    return AccessService(db)

