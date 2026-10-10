import uuid
from sqlalchemy import String, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class RoleModel(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # ✅ ИСПРАВЛЕНИЕ: Убрали "public." из ForeignKey
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False)
    
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Массивы для разделов
    section_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    section_names: Mapped[list[str] | None] = mapped_column(ARRAY(String(128)), nullable=True)

    # Relationships
    tenant = relationship(
        "TenantModel",
        back_populates="roles", 
        lazy="selectin"
    )

    # ✅ Связь с полномочиями (one-to-many)
    permissions = relationship(
        "PermissionModel",
        back_populates="role",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # ✅ Вычисляемое поле: количество полномочий
    @property
    def permissions_count(self) -> int:
        """Количество полномочий роли."""
        return len(self.permissions) if self.permissions else 0