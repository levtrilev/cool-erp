"""Модель склада — мастер-таблица домена inventory."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, text
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


class InvWarehouseModel(DocumentAccessMixin, DocumentLifecycleMixin, Base):
    """
    Склад — домен Inventory.
    Наследует:
    - DocumentAccessMixin   → контракт доступа (ТЗ §3.3)
    - DocumentLifecycleMixin → состояние, блокировки, аудит времени
    """

    __tablename__ = "inv_warehouses"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    # Специфичные поля
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Связи для денормализации (Правило №42)
    tenant: Mapped["TenantModel"] = relationship(
        "TenantModel", lazy="selectin"
    )
    section: Mapped["SectionModel"] = relationship(
        "SectionModel",
        foreign_keys="InvWarehouseModel.section_id",
        lazy="selectin",
    )
    author: Mapped["UserModel"] = relationship(
        "UserModel",
        foreign_keys="InvWarehouseModel.author_id",
        lazy="selectin",
    )

    # Денормализованные имена (Правило №42)
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