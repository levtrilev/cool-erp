"""Реестр обработчиков репликации и базовый класс."""
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class ReplicaHandler(Protocol):
    """Протокол обработчика репликации для домена-получателя."""

    def get_target_table(self) -> str:
        """Имя таблицы реплики в целевом домене."""
        ...

    def get_target_domain(self) -> str:
        """Имя целевого домена."""
        ...

    async def apply(
        self,
        db: AsyncSession,
        payload: dict[str, Any],
        operation: str,
    ) -> None:
        """Применить изменение к реплике."""
        ...


# Глобальный реестр обработчиков
# Ключ: (target_domain, aggregate_type) → ReplicaHandler
REPLICATION_HANDLERS: dict[tuple[str, str], ReplicaHandler] = {}


def register_handler(
    target_domain: str,
    aggregate_type: str,
    handler: ReplicaHandler,
) -> None:
    """Зарегистрировать обработчик репликации."""
    key = (target_domain, aggregate_type)
    if key in REPLICATION_HANDLERS:
        raise ValueError(f"Обработчик для {key} уже зарегистрирован")
    REPLICATION_HANDLERS[key] = handler


def get_handler(
    target_domain: str,
    aggregate_type: str,
) -> ReplicaHandler | None:
    """Получить обработчик по ключу."""
    return REPLICATION_HANDLERS.get((target_domain, aggregate_type))


def get_subscribed_domains(aggregate_type: str) -> list[str]:
    """Получить список доменов, подписанных на данный aggregate_type."""
    return [
        domain
        for (domain, agg_type) in REPLICATION_HANDLERS.keys()
        if agg_type == aggregate_type
    ]


class SequenceGapError(Exception):
    """Обнаружен пропуск в последовательности событий (для конечных автоматов)."""
    pass