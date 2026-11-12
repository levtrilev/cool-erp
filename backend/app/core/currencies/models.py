"""
Справочник валют (ядро).
Глобальный справочник ISO 4217, доступен всем доменам и организациям.
Мультиарендность не применяется: валюта общая для всех тенантов.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CurrencyModel(Base):
    """
    Валюта (ISO 4217). Глобальный справочник ядра.
    Имя таблицы: currencies.
    Ссылка из документов через currency_id (например, заказы продаж).
    """
    __tablename__ = "currencies"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        unique=True,
        comment="Буквенный код валюты по ISO 4217 (например, RUB)",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Название валюты",
    )
    symbol: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="Символ валюты (например, ₽, $, €)",
    )
    numeric_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Числовой код валюты по ISO 4217 (например, 643)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Активна ли валюта (мягкое отключение)",
    )
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