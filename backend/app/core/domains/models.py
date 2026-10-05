import uuid
from sqlalchemy import String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DomainModel(Base):
    __tablename__ = "domains"
    __table_args__ = (
        UniqueConstraint("name", name="uq_domains_name"),
        {"schema": "public"},  # ✅ Правило №28
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()")
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ✅ Правило №1: back_populates и lazy="selectin", каскадное удаление doctypes
    doctypes = relationship(
        "DoctypeModel",
        back_populates="domain",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # ✅ Правило №33: Вычисляемое поле через @property (read-only)
    @property
    def doctypes_count(self) -> int:
        """Количество типов документов в домене — вычисляется из relationship."""
        return len(self.doctypes) if self.doctypes else 0