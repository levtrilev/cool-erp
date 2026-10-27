"""Pydantic-схемы для товаров (Правило №21)."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SalesGoodsCreateSchema(BaseModel):
    """Схема создания товара (Правило №21)."""

    # Специфичные поля
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

    # Контракт доступа (ТЗ §3.3)
    tenant_id: uuid.UUID | None = None  # None → использовать текущий тенант
    section_id: uuid.UUID
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None

    # Жизненный цикл
    doc_status: str | None = None
    doc_number: str | None = Field(default=None, max_length=64)
    doc_date: date | None = None


class SalesGoodsUpdateSchema(BaseModel):
    """Схема обновления товара (Правило №21)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    section_id: uuid.UUID | None = None
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None
    doc_status: str | None = None
    doc_number: str | None = None
    doc_date: date | None = None

    # ✅ Правило №40, часть 2.1: обязательная ожидаемая версия
    version: int = Field(..., ge=1)


class SalesGoodsResponseSchema(BaseModel):
    """Схема ответа (Правило №21 + Правило №40, часть 2.2)."""

    # ✅ Правило №1: чтение из ORM-атрибутов, включая @property
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    # Специфичные поля
    name: str
    description: str | None = None

    # Контракт доступа
    tenant_id: uuid.UUID
    section_id: uuid.UUID
    author_id: uuid.UUID
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None

    # ✅ Денормализованные имена (Правило №42, часть 2.1)
    tenant_name: str | None = None
    section_name: str | None = None
    author_name: str | None = None

    # Жизненный цикл
    doc_status: str
    doc_number: str | None = None
    doc_date: date | None = None
    version: int

    # ✅ Поля пессимистической блокировки (Правило №40, часть 2.2)
    editing_by_user_id: uuid.UUID | None = None
    editing_since: datetime | None = None
    is_editing_locked: bool = False

    # Аудит
    created_at: datetime
    created_by_user_id: uuid.UUID | None = None
    updated_at: datetime
    updated_by_user_id: uuid.UUID | None = None
    deleted_at: datetime | None = None
    deleted_by_user_id: uuid.UUID | None = None