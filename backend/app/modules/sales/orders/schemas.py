"""Pydantic-схемы модуля заказов продаж (Правило №21)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from enum import Enum


DocStatusValue = Literal["draft", "pending", "approved", "active", "archived"]

# ── Строки спецификации ──────────────────────────────────────────


class SalesOrderLineBaseSchema(BaseModel):
    """Базовые поля строки."""

    line_no: int = Field(..., ge=1)
    goods_id: uuid.UUID
    quantity: Decimal = Field(..., ge=0)
    price_with_vat: Decimal = Field(..., ge=0)
    discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    vat_rate_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class SalesOrderLineCreateSchema(SalesOrderLineBaseSchema):
    """Создание строки (без id)."""

    pass


class SalesOrderLineUpdateSchema(SalesOrderLineBaseSchema):
    """Обновление строки (с опциональным id для существующих)."""

    id: uuid.UUID | None = None


class SalesOrderLineResponseSchema(SalesOrderLineBaseSchema):
    """Ответ: строка с вычисляемыми полями."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    # Вычисляемые поля (из @property модели)
    line_total: Decimal
    amount_with_discount: Decimal
    vat_amount: Decimal
    created_at: datetime
    updated_at: datetime


# ── Заказ ────────────────────────────────────────────────────────


class SalesOrderCreateSchema(BaseModel):
    """Создание заказа (без id, version, блокировок)."""

    # Контракт доступа (§3.3)
    section_id: uuid.UUID
    doc_status: DocStatusValue = "draft"
    doc_number: str | None = Field(default=None, max_length=64)
    doc_date: date | None = None
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None

    # Бизнес-поля
    supplier_id: uuid.UUID
    customer_id: uuid.UUID
    contact: str = Field(..., min_length=1, max_length=255)
    manager_id: uuid.UUID
    delivery_due_date: date
    payment_scheme: str | None = Field(default=None, max_length=512)
    currency_id: uuid.UUID
    delivery_address: str | None = None
    delivery_method: str | None = None

    # Спецификация
    lines: list[SalesOrderLineCreateSchema] = Field(
        default_factory=list[SalesOrderLineCreateSchema]
    )


class SalesOrderUpdateSchema(BaseModel):
    """Обновление заказа (с version для оптимистической блокировки)."""

    # Контракт доступа
    section_id: uuid.UUID | None = None
    doc_status: DocStatusValue | None = None
    doc_number: str | None = Field(default=None, max_length=64)
    doc_date: date | None = None
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None

    # Бизнес-поля
    supplier_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    contact: str | None = Field(default=None, min_length=1, max_length=255)
    manager_id: uuid.UUID | None = None
    delivery_due_date: date | None = None
    payment_scheme: str | None = Field(default=None, max_length=512)
    currency_id: uuid.UUID | None = None
    delivery_address: str | None = None
    delivery_method: str | None = None

    # Спецификация (полная замена строк)
    lines: list[SalesOrderLineUpdateSchema] | None = None

    # Оптимистическая блокировка (Правило №40)
    version: int = Field(..., ge=1)

class SalesOrderResponseSchema(BaseModel):
    """Ответ: заказ с денормализованными именами и строками."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # Контракт доступа
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

    # Бизнес-поля
    supplier_id: uuid.UUID
    customer_id: uuid.UUID
    contact: str
    manager_id: uuid.UUID
    delivery_due_date: date
    payment_scheme: str | None = None
    currency_id: uuid.UUID
    total_amount: Decimal
    delivery_address: str | None = None
    delivery_method: str | None = None

    # Денормализованные имена (Правило №42)
    supplier_name: str | None = None
    customer_name: str | None = None
    manager_name: str | None = None
    currency_name: str | None = None
    section_name: str | None = None

    # Строки спецификации
    # lines: list[SalesOrderLineResponseSchema] = Field(default_factory=list)
    lines: list[SalesOrderLineResponseSchema] = Field(
        default_factory=list[SalesOrderLineResponseSchema]
    )

class SalesOrderSortField(str, Enum):
    """Допустимые поля сортировки списка заказов."""
    doc_number = "doc_number"
    doc_date = "doc_date"
    customer_name = "customer_name"
    supplier_name = "supplier_name"
    doc_status = "doc_status"
    total_amount = "total_amount"
    updated_at = "updated_at"
