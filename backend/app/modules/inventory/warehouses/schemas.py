"""Pydantic-схемы для складов."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class InvWarehouseCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    # Контракт доступа (ТЗ §3.3)
    tenant_id: uuid.UUID
    section_id: uuid.UUID
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None
    # Жизненный цикл
    doc_status: str | None = None
    doc_number: str | None = Field(default=None, max_length=64)
    doc_date: date | None = None


class InvWarehouseUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    section_id: uuid.UUID | None = None
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None
    doc_status: str | None = None
    doc_number: str | None = None
    doc_date: date | None = None
    # ✅ Обязательная ожидаемая версия для оптимистической блокировки
    version: int = Field(..., ge=1)


class InvWarehouseResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    # Контракт доступа
    tenant_id: uuid.UUID
    section_id: uuid.UUID
    author_id: uuid.UUID
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None
    # Денормализованные имена (Правило №42)
    tenant_name: str | None = None
    section_name: str | None = None
    author_name: str | None = None
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