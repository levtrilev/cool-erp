from typing import cast
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from app.core.database import Base
from datetime import datetime, timezone

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
        nullable=False,
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
