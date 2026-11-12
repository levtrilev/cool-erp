"""
Модуль: Заказы продаж (пилот сложной формы).
Документный модуль: наследует оба миксина контракта.
Таблица: sales_orders + sales_order_lines (строки спецификации).
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.doctypes.document_base import (
    DocumentAccessMixin,
    DocumentLifecycleMixin,
)

if TYPE_CHECKING:
    from app.modules.business_partners.companies.models import BpCompanyModel
    from app.core.currencies.models import CurrencyModel
    from app.core.users.models import UserModel


class DeliveryMethod:
    """Допустимые значения поля delivery_method (VARCHAR(32))."""
    PICKUP: str = "pickup"
    OWN_TRANSPORT: str = "own_transport"
    THIRD_PARTY: str = "third_party"

    ALL: frozenset[str] = frozenset({PICKUP, OWN_TRANSPORT, THIRD_PARTY})


class SalesOrderModel(DocumentAccessMixin, DocumentLifecycleMixin, Base):
    """
    Заказ продажи — документный модуль (ТЗ §3.3 + жизненный цикл).
    Имя таблицы: sales_orders.
    Наследует:
    - DocumentAccessMixin   → контракт доступа (§3.3)
    - DocumentLifecycleMixin → состояние, блокировки, аудит времени
    """
    __tablename__ = "sales_orders"
    __table_args__ = (
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    # ── Специфичные поля заказа ──────────────────────────────────
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.bp_companies.id"),
        nullable=False,
        index=True,
        comment="Поставщик (наша компания)",
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.bp_companies.id"),
        nullable=False,
        index=True,
        comment="Заказчик (клиент)",
    )
    contact: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Контактное лицо (из заказчика, можно исправить)",
    )
    manager_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id"),
        nullable=False,
        index=True,
        comment="Менеджер (сотрудник, принявший заказ)",
    )
    delivery_due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Дата исполнения заказа",
    )
    payment_scheme: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="Схема оплаты (свободный текст для пилота)",
    )
    currency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.currencies.id"),
        nullable=False,
        comment="Валюта заказа",
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
        comment="Сумма заказа (вычисляется из строк спецификации)",
    )
    delivery_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Адрес доставки",
    )
    delivery_method: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="Способ доставки (см. DeliveryMethod)",
    )

    # ── Связи ────────────────────────────────────────────────────
    lines: Mapped[list["SalesOrderLineModel"]] = relationship(
        "SalesOrderLineModel",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="SalesOrderLineModel.line_no",
    )
    supplier: Mapped["BpCompanyModel"] = relationship(
        "BpCompanyModel",
        foreign_keys="SalesOrderModel.supplier_id",
        lazy="selectin",
    )
    customer: Mapped["BpCompanyModel"] = relationship(
        "BpCompanyModel",
        foreign_keys="SalesOrderModel.customer_id",
        lazy="selectin",
    )
    manager: Mapped["UserModel"] = relationship(
        "UserModel",
        foreign_keys="SalesOrderModel.manager_id",
        lazy="selectin",
    )
    currency: Mapped["CurrencyModel"] = relationship(
        "CurrencyModel",
        foreign_keys="SalesOrderModel.currency_id",
        lazy="selectin",
    )

    # ── Денормализованные имена (Правило №42) ────────────────────
    @property
    def supplier_name(self) -> str | None:
        return self.supplier.name if self.supplier else None

    @property
    def customer_name(self) -> str | None:
        return self.customer.name if self.customer else None

    @property
    def manager_name(self) -> str | None:
        return self.manager.name if self.manager else None

    @property
    def currency_name(self) -> str | None:
        return self.currency.name if self.currency else None


class SalesOrderLineModel(Base):
    """
    Строка спецификации заказа продажи.
    Связана с заказом через order_id (cascade delete-orphan).
    Вычисляемые поля (line_total, amount_with_discount, vat_amount)
    реализованы через @property (Правило №1, №33).
    """
    __tablename__ = "sales_order_lines"
    __table_args__ = (
        UniqueConstraint(
            "order_id", "line_no",
            name="uq_sales_order_line_order_line_no",
        ),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.sales_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Номер строки в спецификации",
    )
    goods_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Товар (реплика из operations; FK добавляется при готовности реплики)",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Количество",
    )
    price_with_vat: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        comment="Цена по прайсу с НДС",
    )
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
        comment="Скидка, %",
    )
    vat_rate_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
        comment="Ставка НДС, %",
    )

    # Временные метки строки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )

    # Связь с заказом
    order: Mapped["SalesOrderModel"] = relationship(
        "SalesOrderModel",
        back_populates="lines",
    )

    # ── Вычисляемые поля (Правило №1, №33) ───────────────────────
    @property
    def line_total(self) -> Decimal:
        """Сумма = количество × цена с НДС."""
        return self.quantity * self.price_with_vat

    @property
    def amount_with_discount(self) -> Decimal:
        """Сумма со скидкой = сумма × (1 − скидка/100)."""
        return self.line_total * (Decimal("1") - self.discount_percent / Decimal("100"))

    @property
    def vat_amount(self) -> Decimal:
        """НДС (в том числе) = сумма со скидкой × ставка / (100 + ставка)."""
        if self.vat_rate_percent == 0:
            return Decimal("0")
        return self.amount_with_discount * self.vat_rate_percent / (
            Decimal("100") + self.vat_rate_percent
        )