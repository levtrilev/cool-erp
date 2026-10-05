import uuid
from sqlalchemy import String, Boolean, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DoctypeModel(Base):
    __tablename__ = "doctypes"
    __table_args__ = (
        UniqueConstraint("doctype", name="uq_doctypes_doctype"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("uuid_generate_v4()")
    )
    
    # Системное имя (например, "invoices")
    doctype: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    
    # Отображаемое имя (например, "Счета-фактуры")
    doctype_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))