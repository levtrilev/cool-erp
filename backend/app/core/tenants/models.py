# backend/app/core/tenant/models.py
import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String, Boolean, text
from app.core.database import Base

class TenantModel(Base):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ✅  связь с пользователями
    users = relationship(
        "UserModel",
        back_populates="tenant",
        lazy="selectin",
    )

    # ✅  связь с разделами
    sections = relationship(
        "SectionModel",
        back_populates="tenant", 
        lazy="selectin"
    )