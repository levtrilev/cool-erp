"""CRUD для чтения реплик товаров в домене inventory."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inventory.replica.models import InvSalesGoodsReplicaModel


class CRUDInvSalesGoodsReplica:
    """
    CRUD для чтения реплик товаров из домена sales.

    Запись в реплику выполняется только репликатором
    (см. handlers.py), поэтому методы записи отсутствуют.
    """

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[InvSalesGoodsReplicaModel], int]:
        """
        Список реплик товаров с мультивенантной изоляцией
        (Правило №26).
        """
        stmt = select(InvSalesGoodsReplicaModel)
        count_stmt = select(func.count()).select_from(InvSalesGoodsReplicaModel)

        if not is_superadmin:
            stmt = stmt.where(InvSalesGoodsReplicaModel.tenant_id == tenant_id)
            count_stmt = count_stmt.where(
                InvSalesGoodsReplicaModel.tenant_id == tenant_id
            )

        if not include_deleted:
            stmt = stmt.where(InvSalesGoodsReplicaModel.is_deleted == False)
            count_stmt = count_stmt.where(
                InvSalesGoodsReplicaModel.is_deleted == False
            )

        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(InvSalesGoodsReplicaModel.name.ilike(pattern))
            count_stmt = count_stmt.where(
                InvSalesGoodsReplicaModel.name.ilike(pattern)
            )

        total = (await db.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(InvSalesGoodsReplicaModel.name).offset(skip).limit(limit)
        items = list((await db.execute(stmt)).scalars().all())
        return items, total

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        goods_id: uuid.UUID,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvSalesGoodsReplicaModel | None:
        """Получение реплики товара по ID с мультивенантной изоляцией."""
        stmt = select(InvSalesGoodsReplicaModel).where(
            InvSalesGoodsReplicaModel.goods_id == goods_id
        )
        if not is_superadmin:
            stmt = stmt.where(InvSalesGoodsReplicaModel.tenant_id == tenant_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


crud_sales_goods_replica = CRUDInvSalesGoodsReplica()