# backend/app/modules/sales/item_types/schemas.py
"""Pydantic-схемы модуля типов номенклатуры (Правило №21)."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DocStatusValue = Literal["draft", "pending", "approved", "active", "archived"]
ItemClassValue = Literal[
    "GOODS",
    "SERVICE",
    "LABOR",
    "SEMI_FINISHED",
    "RAW_MATERIAL",
    "BUNDLE",
    "PACKAGING",
]


class SalesItemTypeBaseSchema(BaseModel):
    """Бизнес-поля карточки."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    item_class: ItemClassValue
    serial_tracking: bool = False
    expiration_tracking: bool = False
    vat_rate: Decimal = Field(
        default=Decimal("0.00"), ge=0, le=100, decimal_places=2
    )
    base_uom: str | None = Field(default=None, max_length=64)
    price_group: str | None = Field(default=None, max_length=128)
    supply_type: str | None = Field(default=None, max_length=128)
    has_variants: bool = False


class SalesItemTypeCreateSchema(SalesItemTypeBaseSchema):
    """Создание (контракт доступа + жизненный цикл)."""

    section_id: uuid.UUID
    doc_status: DocStatusValue = "draft"
    doc_number: str | None = Field(default=None, max_length=64)
    doc_date: date | None = None
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None


class SalesItemTypeUpdateSchema(BaseModel):
    """Обновление (version обязателен — оптимистическая блокировка)."""

    section_id: uuid.UUID | None = None
    doc_status: DocStatusValue | None = None
    doc_number: str | None = Field(default=None, max_length=64)
    doc_date: date | None = None
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    item_class: ItemClassValue | None = None
    serial_tracking: bool | None = None
    expiration_tracking: bool | None = None
    vat_rate: Decimal | None = Field(
        default=None, ge=0, le=100, decimal_places=2
    )
    base_uom: str | None = Field(default=None, max_length=64)
    price_group: str | None = Field(default=None, max_length=128)
    supply_type: str | None = Field(default=None, max_length=128)
    has_variants: bool | None = None
    version: int = Field(..., ge=1)


class SalesItemTypeResponseSchema(BaseModel):
    """Ответ: карточка + денормализованные имена + блокировки."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    section_id: uuid.UUID
    author_id: uuid.UUID
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None
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
    name: str
    description: str | None = None
    item_class: str
    serial_tracking: bool
    expiration_tracking: bool
    vat_rate: Decimal
    base_uom: str | None = None
    price_group: str | None = None
    supply_type: str | None = None
    has_variants: bool
    tenant_name: str | None = None
    section_name: str | None = None
    author_name: str | None = None


class SalesItemTypeSortField(str, Enum):
    """Whitelist полей сортировки списка."""

    item_name = "name"
    item_class = "item_class"
    vat_rate = "vat_rate"
    doc_number = "doc_number"
    updated_at = "updated_at"