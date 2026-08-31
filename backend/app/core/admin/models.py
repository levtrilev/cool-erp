from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
# from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
# from datetime import datetime
import uuid

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    # ✅ Используем Mapped и mapped_column (SQLAlchemy 2.0)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(128), 
        nullable=False, 
        unique=True, 
        index=True
    )
    active: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=True
    )
    description: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True
    )
    
    # Стандартные поля аудита
    # created_at: Mapped[datetime] = mapped_column(
    #     server_default=func.now(), 
    #     nullable=False
    # )
    # updated_at: Mapped[datetime] = mapped_column(
    #     server_default=func.now(), 
    #     onupdate=func.now(), 
    #     nullable=False
    # )

    # def __repr__(self):
    #     return f"<Tenant(name='{self.name}', active={self.active})>"