"""
Контракт атрибутов документов (ТЗ §3.3 + жизненный цикл).

Архитектура:
- Реестр типов документов — таблица `doctypes` (модуль app/core/doctypes).
- Имя таблицы документа совпадает с кодом типа (поле `doctype`).
- Каждая модель документа наследует ДВА миксина:
  * DocumentAccessMixin   — контракт атрибутов доступа (ТЗ §3.3)
  * DocumentLifecycleMixin — управление состоянием, блокировки, аудит времени

Отдельный реестр моделей НЕ создаётся: сопоставление выполняется
динамически через Base.registry.mappers (SQLAlchemy 2.0).
"""
from datetime import date, datetime
import uuid
from typing import Type, cast

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# ============================================================
# Константы состояний документа (поле doc_status)
# ============================================================
class DocStatus:
    """Допустимые значения поля `doc_status` (VARCHAR(32))."""
    DRAFT: str = "draft"          # черновик
    PENDING: str = "pending"      # на утверждении
    APPROVED: str = "approved"    # утверждён
    ACTIVE: str = "active"        # действует
    ARCHIVED: str = "archived"    # архив


# ✅ Таймаут пессимистической блокировки редактирования (минуты)
EDITING_LOCK_TIMEOUT_MINUTES: int = 30


# ============================================================
# МИКСИН 1: Контракт атрибутов доступа (ТЗ §3.3)
# ============================================================
class DocumentAccessMixin:
    """
    Обязательный контракт атрибутов доступа (ТЗ §3.3).

    Слои доступа:
    - Слой 1 (Тенант):  tenant_id
    - Слой 2 (Раздел):  section_id
    - Слой 5 (Автор):   author_id
    - Слой 4 (Теги):    or_tags, and_tags
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id"),
        nullable=False,
        index=True,
        comment="Слой 1: Организация-владелец документа",
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.sections.id"),
        nullable=False,
        index=True,
        comment="Слой 2: Логическое пространство доступа",
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id"),
        nullable=False,
        index=True,
        comment="Слой 5: Автор документа (уровень 'автор')",
    )
    or_tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(128)),
        nullable=True,
        comment="Слой 4: Разрешающие теги (ИЛИ)",
    )
    and_tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(128)),
        nullable=True,
        comment="Слой 4: Обязательные теги (И)",
    )


# ============================================================
# МИКСИН 2: Жизненный цикл документа
# ============================================================
class DocumentLifecycleMixin:
    """
    Управление состоянием, блокировками и аудит времени документа.

    Группы полей:
    - Управление состоянием:   doc_status, doc_number, doc_date
    - Оптимистическая блокировка: version
    - Пессимистическая блокировка: editing_by_user_id, editing_since
    - Временные метки и аудит «кто»: created_at, created_by_user_id,
      updated_at, updated_by_user_id
    - Логическое удаление:     deleted_at, deleted_by_user_id
    """

    # -------- Управление состоянием --------
    doc_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DocStatus.DRAFT,
        server_default=text("'draft'"),
        comment="Состояние документа (см. DocStatus)",
    )
    doc_number: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Человекочитаемый номер документа",
    )
    doc_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Бизнес-дата документа",
    )

    # -------- Оптимистическая блокировка --------
    # ✅ Увеличивается при каждом сохранении. Клиент отправляет
    # ожидаемую версию; при несовпадении — конфликт (409).
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="Версия записи для оптимистической блокировки",
    )

    # -------- Пессимистическая блокировка (редактирование) --------
    # ✅ Блокировка считается истёкшей, если
    # editing_since < now() - interval 'EDITING_LOCK_TIMEOUT_MINUTES minutes'.
    editing_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id"),
        nullable=True,
        comment="Пользователь, редактирующий документ",
    )
    editing_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Момент начала редактирования (для таймаута блокировки)",
    )

    # -------- Временные метки и аудит «кто» --------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Момент создания записи",
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id"),
        nullable=True,
        comment="Кто создал документ (аудит, ТЗ §12.2)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Момент последнего изменения",
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id"),
        nullable=True,
        comment="Кто последний изменил документ (аудит, ТЗ §12.2)",
    )

    # -------- Логическое удаление --------
    # ✅ Документ считается активным при deleted_at IS NULL.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Момент логического удаления (мягкое удаление)",
    )
    deleted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id"),
        nullable=True,
        comment="Кто выполнил удаление (аудит, ТЗ §12.2)",
    )


# ============================================================
# Валидация контракта
# ============================================================
# ✅ Атрибуты миксина доступа (ТЗ §3.3)
REQUIRED_ACCESS_COLUMNS: frozenset[str] = frozenset({
    "tenant_id",
    "section_id",
    "author_id",
    "or_tags",
    "and_tags",
})

# ✅ Атрибуты миксина жизненного цикла
REQUIRED_LIFECYCLE_COLUMNS: frozenset[str] = frozenset({
    "doc_status",
    "doc_number",
    "doc_date",
    "version",
    "editing_by_user_id",
    "editing_since",
    "created_at",
    "created_by_user_id",
    "updated_at",
    "updated_by_user_id",
    "deleted_at",
    "deleted_by_user_id",
})

# ✅ Полный контракт = доступ + жизненный цикл
REQUIRED_CONTRACT_COLUMNS: frozenset[str] = (
    REQUIRED_ACCESS_COLUMNS | REQUIRED_LIFECYCLE_COLUMNS
)


def get_document_model(doctype: str) -> Type[Base] | None:
    """
    Возвращает модель документа по коду типа документа.

    Имя таблицы документа совпадает с кодом `doctype`.
    Поиск выполняется по реестру мапперов SQLAlchemy — отдельный
    реестр не требуется.

    Параметры:
        doctype: код типа документа (имя таблицы), например "invoices".

    Возвращает:
        Класс модели документа или None, если таблица не зарегистрирована.
    """
    for mapper in Base.registry.mappers:
        cls: Type[Base] = cast(Type[Base], mapper.class_)
        table_name: str = getattr(cls, "__tablename__", "")
        if table_name == doctype:
            return cls
    return None


def validate_document_contract(doctype: str) -> tuple[bool, list[str]]:
    """
    Проверяет соответствие таблицы документа полному контракту
    (доступ + жизненный цикл).

    Параметры:
        doctype: код типа документа (имя таблицы).

    Возвращает:
        (валидно, список отсутствующих колонок).
    """
    model: Type[Base] | None = get_document_model(doctype)
    if model is None:
        return False, sorted(REQUIRED_CONTRACT_COLUMNS)

    table: Table | None = cast(Table | None, getattr(model, "__table__", None))
    if table is None:
        return False, sorted(REQUIRED_CONTRACT_COLUMNS)

    existing: set[str] = {c.name for c in table.columns}
    missing: list[str] = sorted(REQUIRED_CONTRACT_COLUMNS - existing)
    return len(missing) == 0, missing