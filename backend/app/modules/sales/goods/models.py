"""Модель товара — мастер-таблица домена sales."""
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

# ✅ TYPE_CHECKING для избежания циклических импортов (Правило №42)
if TYPE_CHECKING:
    from app.core.sections.models import SectionModel
    from app.core.tenants.models import TenantModel
    from app.core.users.models import UserModel


class SalesGoodsModel(DocumentAccessMixin, DocumentLifecycleMixin, Base):
    """
    Товар — домен Sales.
    Наследует:
    - DocumentAccessMixin   → контракт доступа (ТЗ §3.3)
    - DocumentLifecycleMixin → состояние, блокировки, аудит времени
    """

    __tablename__ = "sales_goods"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    # Специфичные поля типа документа
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ✅ Связи для денормализации (Правило №42, часть 1.1-1.3)
    # Иностранные ключи определены в миксине → строковая форма
    tenant: Mapped["TenantModel"] = relationship(
        "TenantModel", lazy="selectin"
    )
    section: Mapped["SectionModel"] = relationship(
        "SectionModel",
        foreign_keys="SalesGoodsModel.section_id",
        lazy="selectin",
    )
    author: Mapped["UserModel"] = relationship(
        "UserModel",
        foreign_keys="SalesGoodsModel.author_id",
        lazy="selectin",
    )

    # ✅ Денормализованные имена (Правило №42, часть 1.4-1.5)
    @property
    def tenant_name(self) -> str | None:
        """Название организации для отображения в интерфейсе."""
        return self.tenant.name if self.tenant else None

    @property
    def section_name(self) -> str | None:
        """Название раздела для ReferenceSelect и списков."""
        return self.section.name if self.section else None

    @property
    def author_name(self) -> str | None:
        """Имя автора документа."""
        return self.author.name if self.author else None

    # ✅ Правило №40, часть 1.2: обязательное вычисляемое поле
    @property
    def is_editing_locked(self) -> bool:
        """Активна ли пессимистическая блокировка с учётом таймаута."""
        if self.editing_by_user_id is None or self.editing_since is None:
            return False
        cutoff: datetime = datetime.now(timezone.utc) - timedelta(
            minutes=EDITING_LOCK_TIMEOUT_MINUTES
        )
        return self.editing_since > cutoff