import uuid
from sqlalchemy import ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class PermissionModel(Base):
    __tablename__ = "permissions"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.roles.id"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False)

    # Тип документа (doctype)
    doctype: Mapped[str] = mapped_column(Text, nullable=False)
    doctype_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Флаги полномочий
    full_access: Mapped[bool] = mapped_column(Boolean, default=False)
    author: Mapped[bool] = mapped_column(Boolean, default=False)
    reader: Mapped[bool] = mapped_column(Boolean, default=False)
    editor: Mapped[bool] = mapped_column(Boolean, default=False)
    can_delete: Mapped[bool] = mapped_column(Boolean, default=False)
    access_by_tags: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # ✅ ИСПРАВЛЕНИЕ: Разрешаем и списки, и словари для JSONB
    or_tags: Mapped[list[str] | dict[str, None] | None] = mapped_column(JSONB, nullable=True)
    and_tags: Mapped[list[str] | dict[str, None] | None] = mapped_column(JSONB, nullable=True)
    no_tags: Mapped[list[str] | dict[str, None] | None] = mapped_column(JSONB, nullable=True)
    
    # Денормализованные имена
    role_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    role = relationship(    # : Mapped["RoleModel"]
        "RoleModel", 
        back_populates="permissions",
        lazy="selectin"
    )
    tenant = relationship("TenantModel", lazy="selectin")
