import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AccessAuditLog(Base):
    """Журнал аудита событий доступа (login, logout, access_denied)."""

    __tablename__ = "access_audit_log"
    __table_args__ = (
        Index("ix_access_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_access_audit_user_created", "user_id", "created_at"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # "login", "logout", "access_denied"
    resource: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )  # "auth", "warehouse", "user", "good", etc.
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # "success", "fail"
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )  # IPv4 or IPv6
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AccessAuditLog id={self.id} action={self.action} tenant={self.tenant_id}>"


class DataAuditLog(Base):
    """Журнал аудита изменений данных (create, update, delete)."""

    __tablename__ = "data_audit_log"
    __table_args__ = (
        Index("ix_data_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_data_audit_entity_entityid", "entity_type", "entity_id"),
        Index("ix_data_audit_user_created", "user_id", "created_at"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # "document", "user", "warehouse", "good", etc.
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    entity_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # "create", "update", "delete"
    changes: Mapped[dict[str, Any] | None] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        comment='{"field_name": {"old": ..., "new": ...}} или {"new": {...}}',
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DataAuditLog id={self.id} entity={self.entity_type}:{self.entity_id} action={self.action}>"