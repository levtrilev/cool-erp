"""Публикация событий в транзакционный outbox."""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.models import CoreOutboxModel


class OutboxPublisher:
    """
    Публикация событий в транзакционный outbox.

    Вызывать в той же транзакции, что и основное изменение.
    Commit выполняется в роутере (Бэкенд Правило №31).
    """

    async def publish(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        source_domain: str,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        payload: dict[str, Any],
        ordering_key: str | None = None,
    ) -> None:
        """
        Публикация события.

        Если указан ordering_key — атомарно увеличивает счётчик
        и присваивает монотонный sequence_no.
        """
        sequence_no: int | None = None

        if ordering_key:
            seq_stmt = text("""
                INSERT INTO core_sequence_counters (ordering_key, counter, updated_at)
                VALUES (:key, 1, now())
                ON CONFLICT (ordering_key)
                DO UPDATE SET counter = core_sequence_counters.counter + 1,
                              updated_at = now()
                RETURNING counter
            """)
            result = await db.execute(seq_stmt, {"key": ordering_key})
            sequence_no = result.scalar_one()

        stmt = insert(CoreOutboxModel).values(
            event_type=event_type,
            source_domain=source_domain,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            ordering_key=ordering_key or "",
            sequence_no=sequence_no,
            occurred_at=datetime.now(timezone.utc),
            processed=False,
        )
        await db.execute(stmt)


outbox = OutboxPublisher()