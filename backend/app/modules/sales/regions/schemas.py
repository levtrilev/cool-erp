"""Pydantic-схемы для регионов (Правило №21)."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SalesRegionCreateSchema(BaseModel):
    """Схема создания региона."""

    # Специфичные поля
    name: str = Field(..., min_length=1, max_length=128)
    capital: str | None = Field(default=None, max_length=128)
    code: str | None = Field(default=None, max_length=8)
    area: str | None = Field(default=None, max_length=64)

    # Контракт доступа (ТЗ §3.3)
    tenant_id: uuid.UUID | None = None  # None → использовать текущий тенант
    section_id: uuid.UUID
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None

    # Жизненный цикл
    doc_number: str | None = Field(default=None, max_length=64)
    doc_date: date | None = None


class SalesRegionUpdateSchema(BaseModel):
    """Схема обновления региона."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    capital: str | None = Field(default=None, max_length=128)
    code: str | None = Field(default=None, max_length=8)
    area: str | None = Field(default=None, max_length=64)
    section_id: uuid.UUID | None = None
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None
    doc_number: str | None = Field(default=None, max_length=64)
    doc_date: date | None = None

    # ✅ Правило №40, часть 2.1: обязательная ожидаемая версия
    version: int = Field(..., ge=1)


class SalesRegionResponseSchema(BaseModel):
    """Схема ответа."""

    # ✅ Правило №1: чтение из ORM-атрибутов, включая @property
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    # Специфичные поля
    name: str
    capital: str | None = None
    code: str | None = None
    area: str | None = None

    # Контракт доступа
    tenant_id: uuid.UUID
    section_id: uuid.UUID
    author_id: uuid.UUID
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None

    # ✅ Денормализованные имена (Правило №42)
    tenant_name: str | None = None
    section_name: str | None = None
    author_name: str | None = None

    # ✅ НОВОЕ: Признак платформенного раздела
    # Фронтенд использует для определения режима «только чтение» (ТЗ §4.3.3)
    is_platform_section: bool = False

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