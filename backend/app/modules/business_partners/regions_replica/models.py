"""Реплики из других доменов для домена business_partners.

✅ Реплика хранит ПОЛНЫЙ КОНТРАКТ ДОСТУПА (§3.3):
   tenant_id, section_id, author_id, or_tags, and_tags.
   Это позволяет домену-получателю вычислять доступ через
   AccessService по правилам ТЗ RBAC/ABAC.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BpSalesRegionsReplicaModel(Base):
    """
    Реплика регионов из домена sales.

    НЕ наследует миксины документов (DocumentAccessMixin, DocumentLifecycleMixin)
    как классы модели — реплика не является документом в своём домене.
    Однако хранит ВСЕ поля контракта доступа как обычные колонки.

    Обновляется фоновым репликатором (см. core/events/replicator.py)
    через обработчик в handlers.py.
    """

    __tablename__ = "bp_sales_regions_replica"
    __table_args__ = {"schema": "public"}

    # ──────────────────────────────────────────────
    # ID оригинала из домена sales
    # ⚠️ БЕЗ ForeignKey на sales_regions.id — изоляция доменов
    # ──────────────────────────────────────────────
    region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    # ──────────────────────────────────────────────
    # Скопированные бизнес-данные
    # ──────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    capital: Mapped[str | None] = mapped_column(String(128), nullable=True)
    code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    area: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ──────────────────────────────────────────────
    # ✅ КОНТРАКТ ДОСТУПА (§3.3) — все 5 полей обязательны
    # Ссылки на таблицы ЯДРА (разрешены матрицей доступа)
    # ──────────────────────────────────────────────
    # Слой 1: Тенант
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id"),
        nullable=False,
        index=True,
    )
    # Слой 2: Раздел (видимость)
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.sections.id"),
        nullable=False,
        index=True,
    )
    # Слой 5: Автор (уровень «автор»)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id"),
        nullable=False,
    )
    # Слой 4: Теги (ИЛИ / И)
    or_tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(128)),
        nullable=True,
    )
    and_tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(128)),
        nullable=True,
    )

    # ──────────────────────────────────────────────
    # Метаданные синхронизации
    # ──────────────────────────────────────────────
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