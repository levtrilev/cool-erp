# backend/app/core/user_preferences/models.py
"""Модель персональных настроек интерфейса."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, PrimaryKeyConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.user_preferences.schemas import JsonValue


class UserUiPreferencesModel(Base):
    """
    Одна строка на пользователя.
    preferences — расширяемый JSONB-документ (тема, навигация, таблицы, ...).
    Хранение в БД даёт синхронизацию между устройствами и сохранность после logout.
    """

    __tablename__ = "user_ui_preferences"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", name="pk_user_ui_preferences"),
        {"schema": "public"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Пользователь — владелец настроек",
    )
    preferences: Mapped[dict[str, JsonValue]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Документ настроек интерфейса",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Момент последнего изменения настроек",
    )