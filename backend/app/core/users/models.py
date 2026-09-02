import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import ForeignKey, text
from app.core.database import Base

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
        UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False, index=True
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
    # ✅ Связь с организацией
    tenant = relationship(
        "TenantModel",
        back_populates="users",
        lazy="selectin",
    )

    # ✅ Property для автоматического извлечения tenant_name
    @property
    def tenant_name(self) -> str | None:
        """Название организации (автоматически извлекается из relationship)"""
        return self.tenant.name if self.tenant else None