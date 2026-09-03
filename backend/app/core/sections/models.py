''' -- Table: public.sections

-- DROP TABLE IF EXISTS public.sections;

CREATE TABLE IF NOT EXISTS public.sections
(
    id uuid NOT NULL DEFAULT uuid_generate_v4(),
    name character varying(128) COLLATE pg_catalog."default" NOT NULL,
    tenant_id uuid NOT NULL,
    CONSTRAINT sections_pkey PRIMARY KEY (id),
    CONSTRAINT sections_uc UNIQUE (tenant_id, name),
    CONSTRAINT tenant_fkey FOREIGN KEY (tenant_id)
        REFERENCES public.tenants (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
'''
import uuid

from sqlalchemy import String, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tenants.models import TenantModel


class SectionModel(Base):
    """Модель разделов (sections) организации."""
    
    __tablename__ = "sections"

    # Уникальный constraint: (tenant_id, name)
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="sections_uc"),
    )

    # --- Колонки ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("uuid_generate_v4()")
    )
    
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.tenants.id", ondelete="NO ACTION"), 
        nullable=False
    )


    # --- Связи (Rule №1) ---
    # Связь с тенантом. 
    # back_populates="sections" требует, чтобы в TenantModel было добавлено поле sections.
    tenant: Mapped["TenantModel"] = relationship(
        back_populates="sections", 
        lazy="selectin"
    )

    # ✅ Property для автоматического извлечения tenant_name
    @property
    def tenant_name(self) -> str | None:
        """Название организации (автоматически извлекается из relationship)"""
        return self.tenant.name if self.tenant else None