# backend/app/modules/sales/goods/schemas.py (замена файла целиком)
"""Pydantic-схемы для товаров (Правило №21)."""
from typing import Literal
import uuid
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

DocStatusValue = Literal["draft", "pending", "approved", "active", "archived"]

class SalesGoodsCreateSchema(BaseModel):
    """Схема создания товара (Правило №21)."""

    # Специфичные поля
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    item_type_id: uuid.UUID | None = None
    base_uom: str | None = Field(default=None, max_length=64)
    # Контракт доступа (ТЗ §3.3)
    tenant_id: uuid.UUID | None = None  # None → использовать текущий тенант
    section_id: uuid.UUID
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None
    # Жизненный цикл
    doc_status: DocStatusValue = "draft"
    doc_number: str | None = Field(default=None, max_length=64)
    doc_date: date | None = None


class SalesGoodsUpdateSchema(BaseModel):
    """Схема обновления товара (Правило №21)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    item_type_id: uuid.UUID | None = None
    base_uom: str | None = Field(default=None, max_length=64)
    section_id: uuid.UUID | None = None
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None
    doc_status: DocStatusValue | None = None
    doc_number: str | None = None
    doc_date: date | None = None
    version: int = Field(..., ge=1)


class SalesGoodsResponseSchema(BaseModel):
    """Схема ответа (Правило №21 + Правило №40, часть 2.2)."""

    # ✅ Правило №1: чтение из ORM-атрибутов, включая @property
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # Специфичные поля
    name: str
    description: str | None = None
    item_type_id: uuid.UUID | None = None
    base_uom: str | None = None
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
    item_type_name: str | None = None
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


class SalesGoodsSortField(str, Enum):
    """Whitelist полей сортировки списка товаров."""

    item_name = "name"
    item_type_name = "item_type_name"
    updated_at = "updated_at"