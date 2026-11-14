# backend/app/modules/sales/item_types/models.py
"""
Модуль: Типы номенклатуры (ItemTypes), домен sales.
Документный модуль: наследует оба миксина контракта (ТЗ §3.3 + жизненный цикл).
Таблица: sales_item_types. Код типа документа = имя таблицы (ТЗ §18.7).
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.doctypes.document_base import (
    EDITING_LOCK_TIMEOUT_MINUTES,
    DocumentAccessMixin,
    DocumentLifecycleMixin,
)

if TYPE_CHECKING:
    from app.core.sections.models import SectionModel
    from app.core.tenants.models import TenantModel
    from app.core.users.models import UserModel


class ItemClass:
    """Допустимые значения поля item_class (VARCHAR(32))."""

    GOODS: str = "GOODS"
    SERVICE: str = "SERVICE"
    LABOR: str = "LABOR"
    SEMI_FINISHED: str = "SEMI_FINISHED"
    RAW_MATERIAL: str = "RAW_MATERIAL"
    BUNDLE: str = "BUNDLE"
    PACKAGING: str = "PACKAGING"
    ALL: frozenset[str] = frozenset(
        {GOODS, SERVICE, LABOR, SEMI_FINISHED, RAW_MATERIAL, BUNDLE, PACKAGING}
    )


class SalesItemTypeModel(DocumentAccessMixin, DocumentLifecycleMixin, Base):
    """Тип номенклатуры — документный модуль домена sales."""

    __tablename__ = "sales_item_types"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    # ── Бизнес-поля карточки ───────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Наименование типа номенклатуры"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Описание"
    )
    item_class: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="Тип номенклатуры (см. ItemClass)"
    )
    serial_tracking: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="Ведение серийных номеров",
    )
    expiration_tracking: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="Ведение сроков годности",
    )
    vat_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
        comment="Ставка НДС, %",
    )
    base_uom: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Базовая единица измерения"
    )
    price_group: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Ценовая группа"
    )
    supply_type: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Схема обеспечения"
    )
    has_variants: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="Вариации товара (Item Variants)",
    )

    # ── Связи для денормализованных имён (Правило №42) ──────────
    tenant: Mapped["TenantModel"] = relationship(
        "TenantModel",
        foreign_keys="SalesItemTypeModel.tenant_id",
        lazy="selectin",
    )
    section: Mapped["SectionModel"] = relationship(
        "SectionModel",
        foreign_keys="SalesItemTypeModel.section_id",
        lazy="selectin",
    )
    author: Mapped["UserModel"] = relationship(
        "UserModel",
        foreign_keys="SalesItemTypeModel.author_id",
        lazy="selectin",
    )

    @property
    def tenant_name(self) -> str | None:
        return self.tenant.name if self.tenant else None

    @property
    def section_name(self) -> str | None:
        return self.section.name if self.section else None

    @property
    def author_name(self) -> str | None:
        return self.author.name if self.author else None

    @property
    def is_editing_locked(self) -> bool:
        """Активна ли пессимистическая блокировка с учётом таймаута."""
        if self.editing_by_user_id is None or self.editing_since is None:
            return False
        cutoff: datetime = datetime.now(timezone.utc) - timedelta(
            minutes=EDITING_LOCK_TIMEOUT_MINUTES
        )
        return self.editing_since > cutoff