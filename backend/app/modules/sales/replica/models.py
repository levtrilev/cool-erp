"""Реплики из других доменов для домена sales."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SalesInvWarehousesReplicaModel(Base):
    """
    Реплика складов из домена inventory.
    НЕ наследует миксины документов — это реплика, а не документ.
    """

    __tablename__ = "sales_inv_warehouses_replica"
    __table_args__ = {"schema": "public"}

    # ID оригинала из домена inventory (БЕЗ ForeignKey на чужой домен!)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )

    # Скопированные данные
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Метаданные синхронизации
    replica_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    replica_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )