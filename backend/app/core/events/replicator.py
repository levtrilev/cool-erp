"""
Фоновый процесс репликации между доменами.

Запускается через lifespan в main.py.
Читает core_outbox, создаёт задачи, применяет их со строгим порядком
внутри групп (ordering_key).
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, text, update # pyright: ignore[reportUnusedImport]
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.events.models import (
    CoreInboxModel,
    CoreOutboxModel,
    CoreReplicationProgressModel,
    CoreReplicationTaskModel,
)
from app.core.events.handlers import (
    REPLICATION_HANDLERS, # pyright: ignore[reportUnusedImport]
    SequenceGapError,
    get_handler,
    get_subscribed_domains,
)

logger = logging.getLogger(__name__)


class Replicator:
    """Фоновый процесс репликации."""

    POLL_INTERVAL: float = 2.0      # Секунды между опросами
    BATCH_SIZE: int = 50            # Размер батча событий/задач
    MAX_ATTEMPTS: int = 5           # Максимум попыток обработки задачи
    MAX_RETRY_DELAY: int = 60       # Максимальная задержка (секунды)

    async def run(self) -> None:
        """Главный цикл репликатора."""
        logger.info("[Replicator] Запуск фонового процесса репликации")
        while True:
            try:
                await self._process_outbox()
                await self._process_tasks()
            except asyncio.CancelledError:
                logger.info("[Replicator] Остановка по запросу")
                raise
            except Exception as e:
                logger.exception("[Replicator] Ошибка цикла: %s", str(e))
            await asyncio.sleep(self.POLL_INTERVAL)

    # ================================================================
    # ФАЗА 1: Чтение outbox → создание задач
    # ================================================================

    async def _process_outbox(self) -> None:
        """Обработка необработанных событий из core_outbox."""
        async with async_session() as db:
            stmt = (
                select(CoreOutboxModel)
                .where(CoreOutboxModel.processed == False)  # noqa: E712
                .order_by(CoreOutboxModel.occurred_at.asc())
                .limit(self.BATCH_SIZE)
            )
            result = await db.execute(stmt)
            events = list(result.scalars().all())

            if not events:
                return

            logger.info("[Replicator] Обработка %d событий", len(events))

            for event in events:
                await self._create_replication_tasks(db, event)
                event.processed = True
                event.processed_at = datetime.now(timezone.utc)

            await db.commit()

    async def _create_replication_tasks(
        self,
        db: AsyncSession,
        event: CoreOutboxModel,
    ) -> None:
        """Создание задач репликации для подписанных доменов."""
        subscribed_domains = get_subscribed_domains(event.aggregate_type)

        for target_domain in subscribed_domains:
            # Проверка идемпотентности
            inbox_stmt = select(CoreInboxModel).where(
                CoreInboxModel.event_id == event.id,
                CoreInboxModel.consumer_domain == target_domain,
            )
            inbox_result = await db.execute(inbox_stmt)
            if inbox_result.scalar_one_or_none() is not None:
                continue  # Уже обработано этим доменом

            handler = get_handler(target_domain, event.aggregate_type)
            if handler is None:
                continue

            # Проверка, что задача ещё не создана
            existing_stmt = select(CoreReplicationTaskModel).where(
                CoreReplicationTaskModel.event_id == event.id,
                CoreReplicationTaskModel.target_domain == target_domain,
            )
            existing_result = await db.execute(existing_stmt)
            if existing_result.scalar_one_or_none() is not None:
                continue

            is_deleted = event.payload.get("is_deleted", False)
            operation = "delete" if is_deleted else "upsert"

            task = CoreReplicationTaskModel(
                event_id=event.id,
                target_domain=target_domain,
                target_table=handler.get_target_table(),
                aggregate_type=event.aggregate_type,
                operation=operation,
                payload=event.payload,
                ordering_key=event.ordering_key or "",
                sequence_no=event.sequence_no or 0,
                status="pending",
            )
            db.add(task)

    # ================================================================
    # ФАЗА 2: Применение задач со строгим порядком
    # ================================================================

    async def _process_tasks(self) -> None:
        """Применение задач из очереди со строгим порядком."""
        async with async_session() as db:
            # Выборка задач, готовых к применению:
            # sequence_no = last_applied_sequence + 1
            stmt = text("""
                SELECT t.*
                FROM core_replication_tasks t
                LEFT JOIN core_replication_progress p
                    ON  p.consumer_domain = t.target_domain
                    AND p.ordering_key    = t.ordering_key
                WHERE t.status IN ('pending', 'waiting')
                  AND (t.next_retry_at IS NULL OR t.next_retry_at <= now())
                  AND (
                      -- Нет записи в progress и это первая задача (sequence_no = 1 или 0)
                      (p.last_applied_sequence IS NULL AND t.sequence_no <= 1)
                      OR
                      -- Есть запись и это следующая задача
                      (p.last_applied_sequence IS NOT NULL
                       AND t.sequence_no = p.last_applied_sequence + 1)
                  )
                ORDER BY t.created_at ASC
                LIMIT :batch_size
                -- FOR UPDATE SKIP LOCKED
            """)
            result = await db.execute(stmt, {"batch_size": self.BATCH_SIZE})
            rows = result.fetchall()

            if not rows:
                # Обновляем статус "ожидающих" задач (у которых предыдущая ещё не применена)
                await self._mark_waiting_tasks(db)
                return

            for row in rows:
                task_id = row.id
                await self._apply_task_by_id(db, task_id)

            await db.commit()

    async def _mark_waiting_tasks(self, db: AsyncSession) -> None:
        """Пометить задачи как waiting, если их предыдущая ещё не применена."""
        # Упрощённо: помечаем waiting те pending задачи, у которых
        # sequence_no > last_applied + 1 и они старше 10 секунд
        stmt = text("""
            UPDATE core_replication_tasks t
            SET status = 'waiting',
                next_retry_at = now() + interval '30 seconds'
            WHERE t.status = 'pending'
              AND t.created_at < now() - interval '10 seconds'
              AND NOT EXISTS (
                  SELECT 1 FROM core_replication_progress p
                  WHERE p.consumer_domain = t.target_domain
                    AND p.ordering_key = t.ordering_key
                    AND t.sequence_no = p.last_applied_sequence + 1
              )
              AND NOT EXISTS (
                  SELECT 1 FROM core_replication_progress p
                  WHERE p.consumer_domain = t.target_domain
                    AND p.ordering_key = t.ordering_key
                    AND p.last_applied_sequence IS NULL
                    AND t.sequence_no <= 1
              )
        """)
        await db.execute(stmt)

    async def _apply_task_by_id(
        self,
        db: AsyncSession,
        task_id: Any,
    ) -> None:
        """Применение одной задачи по ID."""
        # Загружаем задачу
        task = await db.get(CoreReplicationTaskModel, task_id)
        if task is None:
            return

        handler = get_handler(task.target_domain, task.aggregate_type)
        if handler is None:
            logger.warning(
                "[Replicator] Обработчик не найден для (%s, %s)",
                task.target_domain, task.aggregate_type,
            )
            task.status = "failed"
            task.last_error = "Handler not found"
            return

        # Адвайзорная блокировка по ключу группы
        if task.ordering_key:
            lock_stmt = text("SELECT pg_advisory_xact_lock(hashtext(:key))")
            await db.execute(lock_stmt, {"key": task.ordering_key})

        # Повторная проверка прогресса под блокировкой
        progress_stmt = select(CoreReplicationProgressModel).where(
            CoreReplicationProgressModel.consumer_domain == task.target_domain,
            CoreReplicationProgressModel.ordering_key == task.ordering_key,
        )
        progress_result = await db.execute(progress_stmt)
        progress = progress_result.scalar_one_or_none()

        last_applied = progress.last_applied_sequence if progress else 0
        expected_seq = last_applied + 1

        # Идемпотентность: задача уже применена
        if task.sequence_no < expected_seq:
            task.status = "completed"
            task.processed_at = datetime.now(timezone.utc)
            return

        # Задача ещё не готова (предыдущая не применена)
        if task.sequence_no > expected_seq:
            task.status = "waiting"
            task.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
            return

        # Применяем
        task.status = "processing"
        task.attempts += 1

        try:
            await handler.apply(db, task.payload, task.operation)

            # Обновляем/создаём прогресс группы
            if progress is None:
                progress = CoreReplicationProgressModel(
                    consumer_domain=task.target_domain,
                    ordering_key=task.ordering_key,
                    last_applied_sequence=task.sequence_no,
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(progress)
            else:
                progress.last_applied_sequence = task.sequence_no
                progress.updated_at = datetime.now(timezone.utc)

            # Записываем в inbox (идемпотентность)
            inbox = CoreInboxModel(
                event_id=task.event_id,
                consumer_domain=task.target_domain,
                processed_at=datetime.now(timezone.utc),
            )
            db.add(inbox)

            task.status = "completed"
            task.processed_at = datetime.now(timezone.utc)
            task.last_error = None

            logger.info(
                "[Replicator] ✓ %s → %s (seq=%d)",
                task.target_table, task.operation, task.sequence_no,
            )

        except SequenceGapError as e:
            # Пропуск в последовательности состояний — ждём
            task.last_error = str(e)
            task.status = "waiting"
            task.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
            logger.warning("[Replicator] SequenceGap: %s", str(e))

        except Exception as e:
            task.last_error = str(e)
            logger.error(
                "[Replicator] Ошибка применения задачи %s: %s",
                task.id, str(e),
            )

            if task.attempts >= self.MAX_ATTEMPTS:
                task.status = "failed"
                logger.error(
                    "[Replicator] Задача %s провалилась после %d попыток",
                    task.id, task.attempts,
                )
            else:
                task.status = "pending"
                retry_delay = min(self.MAX_RETRY_DELAY, 2 ** task.attempts)
                task.next_retry_at = datetime.now(timezone.utc) + timedelta(
                    seconds=retry_delay
                )


replicator = Replicator()