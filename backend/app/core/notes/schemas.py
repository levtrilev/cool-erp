import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# ✅ Формат тега из ТЗ §6.2: <пространство>:<значение>, без пробелов
TagValue = Annotated[
    str,
    StringConstraints(pattern=r"^[^\s:]+:[^\s:]+$", max_length=128),
]

DocStatusLiteral = Literal[
    "draft", "pending", "approved", "active", "archived"
]


class NoteBaseSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str | None = None


class NoteCreateSchema(NoteBaseSchema):
    section_id: uuid.UUID
    doc_status: DocStatusLiteral = "draft"
    doc_number: str | None = Field(default=None, max_length=64)
    doc_date: date | None = None
    or_tags: list[TagValue] | None = None
    and_tags: list[TagValue] | None = None


class NoteUpdateSchema(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = None
    section_id: uuid.UUID | None = None
    doc_status: DocStatusLiteral | None = None
    doc_number: str | None = Field(default=None, max_length=64)
    doc_date: date | None = None
    or_tags: list[TagValue] | None = None
    and_tags: list[TagValue] | None = None
    # ✅ Обязательная ожидаемая версия для оптимистической блокировки
    version: int = Field(..., ge=1)


class NoteResponseSchema(BaseModel):
    # ✅ Правило №1: чтение из ORM-атрибутов, включая @property
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content: str | None = None

    # Контракт доступа (§3.3)
    tenant_id: uuid.UUID
    section_id: uuid.UUID
    author_id: uuid.UUID
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None

    # Жизненный цикл
    doc_status: str
    doc_number: str | None = None
    doc_date: date | None = None
    version: int

    editing_by_user_id: uuid.UUID | None = None
    editing_since: datetime | None = None
    is_editing_locked: bool = False

    created_at: datetime
    created_by_user_id: uuid.UUID | None = None
    updated_at: datetime
    updated_by_user_id: uuid.UUID | None = None

    deleted_at: datetime | None = None
    deleted_by_user_id: uuid.UUID | None = None