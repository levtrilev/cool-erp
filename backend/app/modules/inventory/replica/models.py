"""Реплики из других доменов для домена inventory."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InvSalesGoodsReplicaModel(Base):
    """
    Реплика товаров из домена sales.

    НЕ наследует миксины документов (DocumentAccessMixin, DocumentLifecycleMixin),
    так как это реплика данных, а не самостоятельный документ.

    Обновляется фоновым репликатором (см. core/events/replicator.py)
    через обработчик в handlers.py.
    """

    __tablename__ = "inv_sales_goods_replica"
    __table_args__ = {"schema": "public"}

    # ID оригинала из домена sales
    # ⚠️ БЕЗ ForeignKey на sales_goods.id — изоляция доменов
    goods_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    # Скопированные данные
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Организация (для мультивенантной фильтрации)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Метаданные синхронизации
    replica_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    replica_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )