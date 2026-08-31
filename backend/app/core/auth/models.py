import uuid
from typing import cast
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, text
from app.core.database import Base
from datetime import datetime, timezone

# ==========================================
# СТРУКТУРА ТАБЛИЦЫ (SQLAlchemy Модель)
# ==========================================


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)

    is_admin: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("tenants.id"), 
        nullable=False, 
        index=True
    )
    role_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    is_superadmin: Mapped[bool | None] = mapped_column(
        default=False, server_default=text("false")
    )

        # Связь с сессиями
    sessions = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

class UserSession(Base):
    __tablename__ = "user_sessions"

    session_token = Column(String(64), primary_key=True, index=True)
    
    # ✅ ИСПРАВЛЕНО: "public.users.id" вместо "users.id"
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # ✅ Используем timezone-aware datetime
    created_at = Column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    is_active = Column(String(1), default="1", nullable=False)

    user = relationship("UserModel", back_populates="sessions", lazy="selectin")

    # ✅ ДОБАВЛЕНО: schema="public" для согласованности с UserModel
    __table_args__ = (
        Index("ix_user_sessions_expires_at", "expires_at"),
        Index("ix_user_sessions_user_active", "user_id", "is_active"),
        {"schema": "public"},  # <-- ЭТО ДОЛЖНО БЫТЬ!
    )

    @property
    def is_expired(self) -> bool:
        # ✅ Сравниваем timezone-aware объекты
        return cast(bool, datetime.now(timezone.utc) > self.expires_at)