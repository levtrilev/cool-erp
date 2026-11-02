# Обновлённый контракт документов: два миксина

Все решения зафиксированы. Подготавливаю обновлённый `app/core/doctypes/document_base.py` с разделением на два миксина.

## 1. `app/core/doctypes/document_base.py` (полная замена)

```python
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
```

---

## 2. Обновлённый пример модели `NotesModel`

**Файл: `app/core/notes/models.py`** — наследует **оба** миксина:

```python
import uuid
from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.doctypes.document_base import (
    DocumentAccessMixin,
    DocumentLifecycleMixin,
)


class NotesModel(DocumentAccessMixin, DocumentLifecycleMixin, Base):
    """
    Заметки — эталонный тип документа (ТЗ §18.7).

    Имя таблицы совпадает с кодом doctype ('notes').
    Наследует:
    - DocumentAccessMixin   → контракт доступа (§3.3)
    - DocumentLifecycleMixin → состояние, блокировки, аудит времени
    """

    __tablename__ = "notes"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    # Специфичные поля типа документа
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(String(4096), nullable=True)

    # ✅ Связи для денормализованных имён (Правило №1)
    tenant = relationship("TenantModel", lazy="selectin")
    section = relationship("SectionModel", lazy="selectin")
    author = relationship("UserModel", foreign_keys=[DocumentAccessMixin.author_id], lazy="selectin")

    @property
    def tenant_name(self) -> str | None:
        return self.tenant.name if self.tenant else None

    @property
    def section_name(self) -> str | None:
        return self.section.name if self.section else None

    @property
    def author_name(self) -> str | None:
        return self.author.name if self.author else None
```

---

## 3. Пояснения по ключевым решениям

| Решение | Реализация |
|---------|------------|
| Два миксина | `DocumentAccessMixin` (доступ) + `DocumentLifecycleMixin` (жизненный цикл) |
| `created_at` / `updated_at` | Стандартные имена, `DateTime(timezone=True)` |
| `deleted_at` | `DateTime(timezone=True) NULL`, фильтр `WHERE deleted_at IS NULL` |
| `version` | `INTEGER NOT NULL DEFAULT 1` |
| `doc_number`, `doc_date` | `VARCHAR(64) NULL`, `DATE NULL` |
| Таймаут блокировки | Константа `EDITING_LOCK_TIMEOUT_MINUTES = 30` |
| `doc_status` | `VARCHAR(32)` с константами `DocStatus` |

---

## 4. Механизм блокировок — как будет работать

### Оптимистическая блокировка (`version`)

Поле добавлено в миксин. Логику проверки реализуем в **сервисе сохранения документа**:

```
1. Клиент получает документ с version = 5
2. При сохранении отправляет expected_version = 5
3. Сервис: UPDATE ... WHERE id = :id AND version = 5, SET version = version + 1
4. Если затронуто 0 строк → конфликт → 409
```

Поле `version` оставлено без встроенного `version_id_col`, чтобы не создавать конфликтов с `__mapper_args__` будущих типов документов. Проверка — в сервисе, с явной ошибкой 409.

### Пессимистическая блокировка (`editing_by_user_id` + `editing_since`)

```
1. Начало редактирования: атомарный захват
   UPDATE ... SET editing_by_user_id = :uid, editing_since = now()
   WHERE id = :id
     AND (editing_by_user_id IS NULL
          OR editing_since < now() - interval '30 minutes')
   RETURNING ...
2. Блокировка истекла, если редактирование длится > 30 минут
3. Освобождение: SET editing_by_user_id = NULL, editing_since = NULL
```

Атомарный захват предотвращает гонку между двумя пользователями. Таймаут защищает от «забытых» блокировок.

---

## 5. Обновлённый SQL-миграция для `notes`

```sql
CREATE TABLE public.notes (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title                  VARCHAR(255) NOT NULL,
    content                VARCHAR(4096),

    -- Контракт доступа (§3.3)
    tenant_id              UUID NOT NULL REFERENCES public.tenants(id),
    section_id             UUID NOT NULL REFERENCES public.sections(id),
    author_id              UUID NOT NULL REFERENCES public.users(id),
    or_tags                VARCHAR(128)[],
    and_tags               VARCHAR(128)[],

    -- Жизненный цикл
    doc_status             VARCHAR(32) NOT NULL DEFAULT 'draft',
    doc_number             VARCHAR(64),
    doc_date               DATE,
    version                INTEGER NOT NULL DEFAULT 1,
    editing_by_user_id     UUID REFERENCES public.users(id),
    editing_since          TIMESTAMPTZ,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by_user_id     UUID REFERENCES public.users(id),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by_user_id     UUID REFERENCES public.users(id),
    deleted_at             TIMESTAMPTZ,
    deleted_by_user_id     UUID REFERENCES public.users(id)
);

-- Индексы (ТЗ §13.3 + расширение)
CREATE INDEX idx_notes_tenant_id      ON public.notes (tenant_id);
CREATE INDEX idx_notes_section_id     ON public.notes (section_id);
CREATE INDEX idx_notes_or_tags        ON public.notes USING GIN (or_tags);
CREATE INDEX idx_notes_and_tags       ON public.notes USING GIN (and_tags);
CREATE INDEX idx_notes_tenant_status  ON public.notes (tenant_id, doc_status);
CREATE INDEX idx_notes_editing_by     ON public.notes (editing_by_user_id);
-- Частичный индекс для активных документов
CREATE INDEX idx_notes_active         ON public.notes (tenant_id) WHERE deleted_at IS NULL;
```

---

## 6. Соответствие правилам проекта

| Правило | Соблюдение |
|---------|------------|
| **Бэкенд №1** | `lazy="selectin"` в `NotesModel`, `@property` для имён |
| **Бэкенд №28** | `{"schema": "public"}`, именованные индексы |
| **Бэкенд №30** | Переиспользование миксинов без создания новых связующих таблиц |
| **Бэкенд №33** | `@property` только для чтения |
| **ТЗ §3.3** | `DocumentAccessMixin` гарантирует 5 полей доступа |
| **ТЗ §13.3** | Индексы на `or_tags`, `and_tags`, `tenant_id`, `section_id` |
| **ТЗ §18.7** | Отдельные таблицы по типам, имя таблицы = `doctype` |

---

Фундамент контракта документов готов. Следующий шаг — подтверждение применения файлов и переход к реализации первого типа документа `notes` (модель, схемы, CRUD, роутер) либо сразу к `AccessService`. Сообщите, с чего продолжить.