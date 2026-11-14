"""backend/app/core/audit/service.py

⚠️ ПРАВИЛО №40 ч.8.1: сервис аудита НЕ коммитит.
Он добавляет записи в текущую транзакцию (db.add), а commit/rollback делает роутер.
Это гарантирует атомарность: бизнес-операция + аудит сохраняются вместе.
"""
import uuid
from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit.models import AccessAuditLog, DataAuditLog
from app.core.audit.utils import get_entity_name

# Sentinel для «не передан»
_UNSET: Any = object()


async def log_data_create(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    entity_name: str | None,
    changes: Mapping[str, Any] | None = None,
) -> None:
    """Запись DataAuditLog на создание сущности."""
    db.add(
        DataAuditLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            action="create",
            changes=dict(changes) if changes else None,
        )
    )


async def log_data_update(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    entity_name: str | None,
    old_values: Mapping[str, Any],
    new_values: Mapping[str, Any],
    resolve_fk_names: bool = True,
) -> None:
    """
    Запись DataAuditLog на обновление.

    old_values/new_values — «сырые» значения полей (могут содержать UUID).
    Если resolve_fk_names=True — для полей *_id подтягиваем человекочитаемое имя
    через get_entity_name (то же поведение, что было в users/router.py).
    """
    changes: dict[str, dict[str, Any]] = {}
    for field, new_value in new_values.items():
        if field not in old_values:
            continue
        old_value = old_values[field]
        if old_value == new_value:
            continue

        if resolve_fk_names and field.endswith("_id"):
            old_name = (
                await get_entity_name(db, field[:-3], uuid.UUID(str(old_value)))
                if old_value
                else ""
            )
            new_name = (
                await get_entity_name(db, field[:-3], uuid.UUID(str(new_value)))
                if new_value
                else ""
            )
            changes[field] = {
                "old": old_name or str(old_value),
                "new": new_name or str(new_value),
            }
        else:
            changes[field] = {"old": str(old_value), "new": str(new_value)}

    if not changes:
        return  # нечего писать — не плодим пустые записи

    db.add(
        DataAuditLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            action="update",
            changes=changes,
        )
    )


async def log_data_delete(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    entity_name: str | None,
) -> None:
    """Запись DataAuditLog на удаление сущности."""
    db.add(
        DataAuditLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            action="delete",
            changes={"deleted": True},
        )
    )


async def log_access(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None,
    action: str,
    resource: str,
    status: str = "success",
    ip_address: str | None = None,
) -> None:
    """Запись AccessAuditLog (факт доступа к ресурсу)."""
    db.add(
        AccessAuditLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource=resource,
            status=status,
            ip_address=ip_address,
        )
    )