"""Обработчики репликации для домена sales."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.handlers import register_handler
from app.modules.sales.replica.models import SalesInvWarehousesReplicaModel


class InvWarehousesReplicaHandler:
    """
    Обработчик репликации складов из домена inventory.
    Регистрируется для (target_domain='sales', aggregate_type='inv_warehouses').
    """

    def get_target_table(self) -> str:
        return "sales_inv_warehouses_replica"

    def get_target_domain(self) -> str:
        return "sales"

    async def apply(
        self,
        db: AsyncSession,
        payload: dict[str, Any],
        operation: str,
    ) -> None:
        """Применение изменения склада к реплике."""
        warehouse_id = payload["id"]

        stmt = select(SalesInvWarehousesReplicaModel).where(
            SalesInvWarehousesReplicaModel.warehouse_id == warehouse_id
        )
        result = await db.execute(stmt)
        replica = result.scalar_one_or_none()

        if operation == "delete":
            # ✅ Мягкое удаление реплики
            if replica is not None:
                replica.is_deleted = True
                replica.replica_version += 1
                replica.replica_synced_at = datetime.now(timezone.utc)
            return

        # ✅ Upsert реплики
        if replica is None:
            replica = SalesInvWarehousesReplicaModel(
                warehouse_id=warehouse_id,
                name=payload["name"],
                description=payload.get("description"),
                tenant_id=payload["tenant_id"],
            )
            db.add(replica)
        else:
            replica.name = payload["name"]
            replica.description = payload.get("description")
            replica.tenant_id = payload["tenant_id"]
            replica.is_deleted = payload.get("is_deleted", False)
            replica.replica_version += 1
            replica.replica_synced_at = datetime.now(timezone.utc)


# ✅ Регистрация при импорте модуля (импорт выполняется в main.py)
register_handler(
    target_domain="sales",
    aggregate_type="inv_warehouses",
    handler=InvWarehousesReplicaHandler(),
)