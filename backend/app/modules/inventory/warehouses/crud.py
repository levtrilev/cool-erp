"""CRUD для складов с блокировками (Бэкенд Правило №40)."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud.base import CRUDBase
from app.core.doctypes.document_base import EDITING_LOCK_TIMEOUT_MINUTES
from app.modules.inventory.warehouses.models import InvWarehouseModel
from app.modules.inventory.warehouses.schemas import (
    InvWarehouseCreateSchema,
    InvWarehouseUpdateSchema,
)


class WarehouseNotFoundError(Exception):
    """Склад не найден или недоступен в текущем тенанте."""


class WarehouseVersionConflictError(Exception):
    """Ожидаемая версия не совпадает с версией в БД (409)."""


class WarehouseEditingLockedError(Exception):
    """Склад редактируется другим пользователем (423)."""


class CRUDInvWarehouse(
    CRUDBase[InvWarehouseModel, InvWarehouseCreateSchema, InvWarehouseUpdateSchema]
):
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[InvWarehouseModel], int]:
        stmt = select(self.model).where(self.model.deleted_at.is_(None))
        count_stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.deleted_at.is_(None))
        )

        if not is_superadmin:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
            count_stmt = count_stmt.where(self.model.tenant_id == tenant_id)

        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(self.model.name.ilike(pattern))
            count_stmt = count_stmt.where(self.model.name.ilike(pattern))

        total = (await db.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(self.model.name).offset(skip).limit(limit)
        items = list((await db.execute(stmt)).scalars().all())
        return items, total

    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        warehouse_id: uuid.UUID,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel | None:
        stmt = select(self.model).where(
            self.model.id == warehouse_id,
            self.model.deleted_at.is_(None),
        )
        if not is_superadmin:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def acquire_editing_lock(
        self,
        db: AsyncSession,
        *,
        warehouse_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        """Атомарный захват блокировки с учётом таймаута."""
        model = self.model
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)

        conditions: list[ColumnElement[bool]] = [
            model.id == warehouse_id,
            model.deleted_at.is_(None),
            or_(
                model.editing_by_user_id.is_(None),
                model.editing_since < cutoff,
            ),
        ]
        if not is_superadmin:
            conditions.append(model.tenant_id == tenant_id)

        stmt = (
            update(model)
            .where(*conditions)
            .values(editing_by_user_id=user_id, editing_since=now)
            .returning(model.id)
        )
        locked_id = (await db.execute(stmt)).scalar_one_or_none()

        if locked_id is None:
            warehouse = await self.get_for_user(
                db,
                warehouse_id=warehouse_id,
                tenant_id=tenant_id,
                is_superadmin=is_superadmin,
            )
            if warehouse is None:
                raise WarehouseNotFoundError("Склад не найден")
            raise WarehouseEditingLockedError("Склад уже редактируется")

        warehouse = await self.get_for_user(
            db,
            warehouse_id=warehouse_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден")
        await db.flush()
        await db.refresh(warehouse)
        return warehouse

    async def release_editing_lock(
        self,
        db: AsyncSession,
        *,
        warehouse_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        warehouse = await self.get_for_user(
            db,
            warehouse_id=warehouse_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден")

        if (
            not is_superadmin
            and warehouse.editing_by_user_id is not None
            and warehouse.editing_by_user_id != user_id
        ):
            raise WarehouseEditingLockedError(
                "Блокировка принадлежит другому пользователю"
            )

        warehouse.editing_by_user_id = None
        warehouse.editing_since = None
        await db.flush()
        await db.refresh(warehouse)
        return warehouse

    async def save_with_version(
        self,
        db: AsyncSession,
        *,
        warehouse_id: uuid.UUID,
        obj_in: InvWarehouseUpdateSchema,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        model = self.model
        warehouse = await self.get_for_user(
            db,
            warehouse_id=warehouse_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден")

        # Жёсткая проверка пессимистической блокировки
        if (
            warehouse.editing_by_user_id is not None
            and warehouse.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if warehouse.editing_since is None or warehouse.editing_since > cutoff:
                raise WarehouseEditingLockedError(
                    "Склад заблокирован другим пользователем"
                )

        values: dict[str, Any] = obj_in.model_dump(
            exclude_unset=True, exclude={"version"}
        )
        values["version"] = model.version + 1
        values["updated_at"] = func.now()
        values["updated_by_user_id"] = user_id
        values["editing_by_user_id"] = None
        values["editing_since"] = None

        conditions: list[ColumnElement[bool]] = [
            model.id == warehouse_id,
            model.version == obj_in.version,
            model.deleted_at.is_(None),
        ]
        if not is_superadmin:
            conditions.append(model.tenant_id == tenant_id)

        stmt = (
            update(model)
            .where(*conditions)
            .values(**values)
            .returning(model.id)
        )
        updated_id = (await db.execute(stmt)).scalar_one_or_none()

        if updated_id is None:
            raise WarehouseVersionConflictError(
                "Склад изменён другим пользователем. Обновите данные."
            )

        await db.flush()
        await db.refresh(warehouse)
        return warehouse

    async def mark_deleted(
        self,
        db: AsyncSession,
        *,
        warehouse_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        warehouse = await self.get_for_user(
            db,
            warehouse_id=warehouse_id,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден")

        if (
            warehouse.editing_by_user_id is not None
            and warehouse.editing_by_user_id != user_id
            and not is_superadmin
        ):
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
            if warehouse.editing_since is None or warehouse.editing_since > cutoff:
                raise WarehouseEditingLockedError(
                    "Склад заблокирован и не может быть удалён"
                )

        warehouse.deleted_at = datetime.now(timezone.utc)
        warehouse.deleted_by_user_id = user_id
        warehouse.updated_by_user_id = user_id
        warehouse.editing_by_user_id = None
        warehouse.editing_since = None
        warehouse.version = warehouse.version + 1
        await db.flush()
        await db.refresh(warehouse)
        return warehouse


crud_warehouse = CRUDInvWarehouse(InvWarehouseModel)