import uuid
from sqlalchemy import String, Boolean, UniqueConstraint, text, Column, Table, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ✅ Правило №28: Association table с явной схемой public
doctype_tenants = Table(
    "doctype_tenants",
    Base.metadata,
    Column("doctype_id", UUID(as_uuid=True), ForeignKey("public.doctypes.id", ondelete="CASCADE"), primary_key=True),
    Column("tenant_id", UUID(as_uuid=True), ForeignKey("public.tenants.id", ondelete="CASCADE"), primary_key=True),
    schema="public"
)


class DoctypeModel(Base):
    __tablename__ = "doctypes"
    __table_args__ = (
        UniqueConstraint("doctype", name="uq_doctypes_doctype"),
        {"schema": "public"},  # ✅ Правило №28
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()")
    )
    domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.domains.id", ondelete="CASCADE"),  # ✅ Правило №28
        nullable=False
    )

    doctype: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    doctype_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    # ✅ Правило №1: back_populates и lazy="selectin"
    domain = relationship("DomainModel", back_populates="doctypes", lazy="selectin")
    tenants = relationship("TenantModel", secondary=doctype_tenants, lazy="selectin")

    # ✅ Правило №33: Вычисляемые поля через @property (read-only)
    @property
    def domain_name(self) -> str | None:
        """Имя домена — вычисляется из связанной модели."""
        return self.domain.name if self.domain else None

    @property
    def tenant_ids(self) -> list[uuid.UUID]:
        """ID тенантов — вычисляется из M2M relationship."""
        return [t.id for t in self.tenants] if self.tenants else []