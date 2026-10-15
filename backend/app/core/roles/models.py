import uuid
from sqlalchemy import String, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from app.core.database import Base
from app.core.users.models import UserModel

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

    # ✅ Обратная связь с пользователями через ARRAY role_ids.
    # Генерирует SQL: WHERE roles.id = ANY(users.role_ids)
    # viewonly=True — связь только для чтения, не участвует в каскадах
    users = relationship(
        "UserModel",
        primaryjoin=lambda: RoleModel.id == func.any(foreign(UserModel.role_ids)),
        lazy="selectin",
        viewonly=True,
    )

    # ✅ Вычисляемое поле: количество полномочий
    @property
    def permissions_count(self) -> int:
        """Количество полномочий роли."""
        return len(self.permissions) if self.permissions else 0

    # ✅ Property для автоматического извлечения tenant_name
    @property
    def tenant_name(self) -> str | None:
        """Название организации (автоматически извлекается из relationship)"""
        return self.tenant.name if self.tenant else None

    # ✅ Имена пользователей для чипсов в списке ролей
    # Правило №33: @property только для чтения
    # Правило №1: читается из relationship users с lazy="selectin"
    @property
    def user_names(self) -> list[str]:
        """Имена пользователей, которым назначена роль."""
        return [u.name for u in self.users] if self.users else []