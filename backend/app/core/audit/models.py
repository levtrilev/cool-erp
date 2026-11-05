import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, Text, Boolean, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class AccessAuditLog(Base):
    """Журнал аудита событий доступа (login, logout, access_denied)."""

    __tablename__ = "access_audit_log"
    __table_args__ = (
        Index("ix_access_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_access_audit_user_created", "user_id", "created_at"),
        {"schema": "public"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    action = Column(
        String(50),
        nullable=False,
    )  # "login", "logout", "access_denied"
    resource = Column(
        String(100),
        nullable=False,
    )  # "auth", "warehouse", "user", "good", etc.
    status = Column(
        String(20),
        nullable=False,
    )  # "success", "fail"
    ip_address = Column(
        String(45),
        nullable=True,
    )  # IPv4 or IPv6
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
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

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    entity_type = Column(
        String(50),
        nullable=False,
    )  # "document", "user", "warehouse", "good", etc.
    entity_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    entity_name = Column(
        String(255),
        nullable=True,
    )
    action = Column(
        String(20),
        nullable=False,
    )  # "create", "update", "delete"
    changes = Column(
        JSONB,
        nullable=True,
    )  # JSONB: {"field_name": {"old": ..., "new": ...}} or {"new": {...}}
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<DataAuditLog id={self.id} entity={self.entity_type}:{self.entity_id} action={self.action}>"