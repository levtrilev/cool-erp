"""Обработчики репликации для домена inventory."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.handlers import register_handler
from app.modules.inventory.replica.models import InvSalesGoodsReplicaModel


class SalesGoodsReplicaHandler:
    """
    Обработчик репликации товаров из домена sales в домен inventory.

    Регистрируется для пары:
      - target_domain = "inventory"
      - aggregate_type = "sales_goods"

    Вызывается репликатором при обработке задач из
    core_replication_tasks для событий типа "sales.goods.*".
    """

    def get_target_table(self) -> str:
        """Имя таблицы реплики в домене inventory."""
        return "inv_sales_goods_replica"

    def get_target_domain(self) -> str:
        """Имя целевого домена."""
        return "inventory"

    async def apply(
        self,
        db: AsyncSession,
        payload: dict[str, Any],
        operation: str,
    ) -> None:
        """
        Применение изменения товара к реплике.

        Параметры:
            db: сессия БД
            payload: данные события (из поля `payload` в core_outbox)
            operation: "upsert" или "delete"

        Ожидаемый формат payload:
            {
                "id": "<goods_id>",
                "name": "<name>",
                "description": "<description | null>",
                "tenant_id": "<tenant_id>",
                "is_deleted": false
            }
        """
        goods_id: str = payload["id"]

        # Поиск существующей реплики
        stmt = select(InvSalesGoodsReplicaModel).where(
            InvSalesGoodsReplicaModel.goods_id == goods_id
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
            # Создаём новую запись реплики
            replica = InvSalesGoodsReplicaModel(
                goods_id=goods_id,
                name=payload["name"],
                description=payload.get("description"),
                tenant_id=payload["tenant_id"],
            )
            db.add(replica)
        else:
            # Обновляем существующую запись реплики
            replica.name = payload["name"]
            replica.description = payload.get("description")
            replica.tenant_id = payload["tenant_id"]
            replica.is_deleted = payload.get("is_deleted", False)
            replica.replica_version += 1
            replica.replica_synced_at = datetime.now(timezone.utc)


# ✅ Регистрация при импорте модуля
# Репликатор найдёт этот обработчик при поиске подписчиков
# для событий с aggregate_type="sales_goods"
register_handler(
    target_domain="inventory",
    aggregate_type="sales_goods",
    handler=SalesGoodsReplicaHandler(),
)