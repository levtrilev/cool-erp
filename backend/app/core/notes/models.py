import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.doctypes.document_base import (
    EDITING_LOCK_TIMEOUT_MINUTES,
    DocumentAccessMixin,
    DocumentLifecycleMixin,
)


class NotesModel(DocumentAccessMixin, DocumentLifecycleMixin, Base):
    """
    Заметки — эталонный тип документа.

    Имя таблицы совпадает с кодом doctype ("notes").
    Доступ: DocumentAccessMixin (ТЗ §3.3).
    Жизненный цикл: DocumentLifecycleMixin.
    """

    __tablename__ = "notes"
    __table_args__ = (
        Index("ix_notes_tenant_status", "tenant_id", "doc_status"),
        Index(
            "ix_notes_active",
            "tenant_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ✅ Правило №1 / №33: derived-поле только через @property, без присваиваний
    @property
    def is_editing_locked(self) -> bool:
        """Активна ли пессимистическая блокировка с учётом таймаута."""
        if self.editing_by_user_id is None or self.editing_since is None:
            return False
        cutoff: datetime = datetime.now(timezone.utc) - timedelta(
            minutes=EDITING_LOCK_TIMEOUT_MINUTES
        )
        return self.editing_since > cutoff