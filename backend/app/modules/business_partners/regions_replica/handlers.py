"""Обработчики репликации для домена business_partners.

✅ Репликация включает ПОЛНЫЙ КОНТРАКТ ДОСТУПА (§3.3):
   все события обязаны содержать поля тенанта, раздела, автора и тегов.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.handlers import register_handler
from app.modules.business_partners.regions_replica.models import BpSalesRegionsReplicaModel


class SalesRegionsReplicaHandler:
    """
    Обработчик репликации регионов из домена sales в домен business_partners.

    Регистрируется для пары:
      - target_domain = "business_partners"
      - aggregate_type = "sales_regions"

    Вызывается репликатором при обработке задач из
    core_replication_tasks для событий типа "sales.region.*".
    """

    def get_target_table(self) -> str:
        """Имя таблицы реплики в домене business_partners."""
        return "bp_sales_regions_replica"

    def get_target_domain(self) -> str:
        """Имя целевого домена."""
        return "business_partners"

    async def apply(
        self,
        db: AsyncSession,
        payload: dict[str, Any],
        operation: str,
    ) -> None:
        """
        Применение изменения региона к реплике.

        Ожидаемый формат payload (из RegionService._publish_event):
            {
                "id": "<region_id>",
                "name": "<name>",
                "capital": "<capital | null>",
                "code": "<code | null>",
                "area": "<area | null>",
                "tenant_id": "<tenant_id>",
                "section_id": "<section_id>",      # ← контракт доступа
                "author_id": "<author_id>",        # ← контракт доступа
                "or_tags": [...],                  # ← контракт доступа
                "and_tags": [...],                 # ← контракт доступа
                "is_deleted": false
            }
        """
        region_id: str = payload["id"]

        # Поиск существующей реплики
        stmt = select(BpSalesRegionsReplicaModel).where(
            BpSalesRegionsReplicaModel.region_id == region_id
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

        # ✅ Upsert реплики с полным контрактом доступа
        if replica is None:
            replica = BpSalesRegionsReplicaModel(
                region_id=region_id,
                name=payload["name"],
                capital=payload.get("capital"),
                code=payload.get("code"),
                area=payload.get("area"),
                # ✅ Контракт доступа (§3.3) — все 5 полей
                tenant_id=payload["tenant_id"],
                section_id=payload["section_id"],
                author_id=payload["author_id"],
                or_tags=payload.get("or_tags"),
                and_tags=payload.get("and_tags"),
            )
            db.add(replica)
        else:
            replica.name = payload["name"]
            replica.capital = payload.get("capital")
            replica.code = payload.get("code")
            replica.area = payload.get("area")
            # ✅ Контракт доступа обновляется при каждом событии
            replica.tenant_id = payload["tenant_id"]
            replica.section_id = payload["section_id"]
            replica.author_id = payload["author_id"]
            replica.or_tags = payload.get("or_tags")
            replica.and_tags = payload.get("and_tags")
            replica.is_deleted = payload.get("is_deleted", False)
            replica.replica_version += 1
            replica.replica_synced_at = datetime.now(timezone.utc)


# ✅ Регистрация при импорте модуля
register_handler(
    target_domain="business_partners",
    aggregate_type="sales_regions",
    handler=SalesRegionsReplicaHandler(),
)