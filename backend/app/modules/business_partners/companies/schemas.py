"""Pydantic-схемы для компаний (Правило №21)."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class BpCompanyCreateSchema(BaseModel):
    """Схема создания компании."""

    # Специфичные поля
    name: str = Field(..., min_length=1, max_length=255)
    fullname: str | None = None
    inn: str | None = None
    address_legal: str | None = None
    address_fact: str | None = None
    phone: str | None = None
    email: str | None = None
    contact: str | None = None
    is_customer: bool | None = None
    is_supplier: bool | None = None
    kpp: str | None = None
    region_id: uuid.UUID | None = None

    # Контракт доступа (ТЗ §3.3)
    tenant_id: uuid.UUID | None = None  # None → использовать текущий тенант
    section_id: uuid.UUID
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None

    # Жизненный цикл
    doc_status: str | None = None
    doc_number: str | None = Field(default=None, max_length=64)
    doc_date: date | None = None


class BpCompanyUpdateSchema(BaseModel):
    """Схема обновления компании."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    fullname: str | None = None
    inn: str | None = None
    address_legal: str | None = None
    address_fact: str | None = None
    phone: str | None = None
    email: str | None = None
    contact: str | None = None
    is_customer: bool | None = None
    is_supplier: bool | None = None
    kpp: str | None = None
    region_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None
    doc_status: str | None = None
    doc_number: str | None = None
    doc_date: date | None = None

    # ✅ Правило №40, часть 2.1: обязательная ожидаемая версия
    version: int = Field(..., ge=1)


class BpCompanyResponseSchema(BaseModel):
    """Схема ответа."""

    # ✅ Правило №1: чтение из ORM-атрибутов, включая @property
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    # Специфичные поля
    name: str
    fullname: str | None = None
    inn: str | None = None
    address_legal: str | None = None
    address_fact: str | None = None
    phone: str | None = None
    email: str | None = None
    contact: str | None = None
    is_customer: bool | None = None
    is_supplier: bool | None = None
    kpp: str | None = None
    region_id: uuid.UUID | None = None

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