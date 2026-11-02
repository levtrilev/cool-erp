"""CRUD для складов с блокировками (Бэкенд Правило №40)
и контролем доступа (ТЗ RBAC/ABAC §8)."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, cast as typing_cast # pyright: ignore[reportUnusedImport]
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.access.service import AccessService, DocumentProtocol
from app.core.crud.base import CRUDBase
from app.core.doctypes.document_base import EDITING_LOCK_TIMEOUT_MINUTES
from app.modules.inventory.warehouses.models import InvWarehouseModel
from app.modules.inventory.warehouses.schemas import (
    InvWarehouseCreateSchema,
    InvWarehouseUpdateSchema,
)
from app.core.access.schemas import UserProtocol

# ✅ Избегаем циклического импорта — UserModel нужен только для типизации
# if TYPE_CHECKING:
#     from app.core.users.models import UserModel


class WarehouseNotFoundError(Exception):
    """Склад не найден или недоступен в текущем тенанте."""


class WarehouseVersionConflictError(Exception):
    """Ожидаемая версия не совпадает с версией в БД (409)."""


class WarehouseEditingLockedError(Exception):
    """Склад редактируется другим пользователем (423)."""


class CRUDInvWarehouse(
    CRUDBase[InvWarehouseModel, InvWarehouseCreateSchema, InvWarehouseUpdateSchema]
):
    """CRUD для складов с блокировками и контролем доступа."""

    # ==================================================================
    # СПИСОК (ТЗ §2.6 — RLS-семантика: скрытые записи не возвращаются)
    # ==================================================================
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[InvWarehouseModel], int]:
        """
        Список складов с контролем доступа через AccessService.
        Фильтр включает ВСЕ 5 слоёв ТЗ RBAC/ABAC §3.
        """
        model = self.model
        base_where = model.deleted_at.is_(None)

        # ✅ КРИТИЧНО: SQL-фильтр видимости через AccessService
        access_service = AccessService(db)
        access_filter = await access_service.build_access_filter(user, model)
        if access_filter is None:
            # Пользователю не видна ни одна запись (нет ролей / нет разделов /
            # не прошёл тег-фильтр) — возвращаем пустой список.
            return [], 0

        stmt = select(model).where(base_where, access_filter)
        count_stmt = (
            select(func.count())
            .select_from(model)
            .where(base_where, access_filter)
        )

        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(model.name.ilike(pattern))
            count_stmt = count_stmt.where(model.name.ilike(pattern))

        total = (await db.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(model.name).offset(skip).limit(limit)
        items = list((await db.execute(stmt)).scalars().all())
        return items, total

    # ==================================================================
    # ОДНОЧНАЯ ЗАПИСЬ (ТЗ §2.3 — нет права на чтение ⇒ 404)
    # ==================================================================
    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        warehouse_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel | None:
        """
        Получение склада с контролем доступа.
        Возвращает None, если запись не видна пользователю (ТЗ §2.3).
        """
        model = self.model
        stmt = select(model).where(
            model.id == warehouse_id,
            model.deleted_at.is_(None),
        )
        if not is_superadmin:
            stmt = stmt.where(model.tenant_id == tenant_id)

        warehouse = (await db.execute(stmt)).scalar_one_or_none()
        if warehouse is None:
            return None

        # ✅ Проверка доступа через AccessService (все 5 слоёв)
        access_service = AccessService(db)
        # ✅ Правило №45: статический анализатор не сопоставляет
        # дескрипторы Mapped[... модели] с аннотациями значений протокола.
        # В рантайме совместимость гарантирована миксинами.
        warehouse_doc: DocumentProtocol = typing_cast("DocumentProtocol", warehouse)
        access = await access_service.resolve_access(user, warehouse_doc)
        if not access.visible:
            return None
        return warehouse

    # ==================================================================
    # БЛОКИРОВКИ (Правило №40, часть 3) + контроль доступа
    # ==================================================================
    async def acquire_editing_lock(
        self,
        db: AsyncSession,
        *,
        warehouse_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        """Атомарный захват блокировки с учётом таймаута и контроля доступа."""
        model = self.model

        # ✅ СНАЧАЛА проверяем доступ — если пользователь не видит склад,
        # он не должен иметь возможности даже попытаться его заблокировать.
        pre_check = await self.get_for_user(
            db,
            warehouse_id=warehouse_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if pre_check is None:
            raise WarehouseNotFoundError("Склад не найден")

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)

        # ✅ Правило №40, часть 3.2: РОВНО ДВА условия для захвата
        conditions: list[ColumnElement[bool]] = [
            model.id == warehouse_id,
            model.deleted_at.is_(None),
            or_(
                model.editing_by_user_id.is_(None),   # ✅ свободно
                model.editing_since < cutoff,          # ✅ истекло
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
                user=user,
                tenant_id=tenant_id,
                is_superadmin=is_superadmin,
            )
            if warehouse is None:
                raise WarehouseNotFoundError("Склад не найден")
            raise WarehouseEditingLockedError("Склад уже редактируется")

        warehouse = await self.get_for_user(
            db,
            warehouse_id=warehouse_id,
            user=user,
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
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        """Освобождение блокировки владельцем или суперадмином."""
        warehouse = await self.get_for_user(
            db,
            warehouse_id=warehouse_id,
            user=user,
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

    # ==================================================================
    # СОХРАНЕНИЕ С ВЕРСИЕЙ (Правило №40, часть 5) + контроль доступа
    # ==================================================================
    async def save_with_version(
        self,
        db: AsyncSession,
        *,
        warehouse_id: uuid.UUID,
        obj_in: InvWarehouseUpdateSchema,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        """Сохранение с проверкой обеих блокировок и контроля доступа."""
        model = self.model

        warehouse = await self.get_for_user(
            db,
            warehouse_id=warehouse_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден")

        # ✅ Проверка уровня доступа: изменение требует минимум level >= 2
        access_service = AccessService(db)
        warehouse_doc: DocumentProtocol = typing_cast("DocumentProtocol", warehouse)
        access = await access_service.resolve_access(user, warehouse_doc)
        if access.level < 2:
            raise WarehouseNotFoundError("Склад не найден")

        # ✅ Правило №40, часть 5.2: ЖЁСТКАЯ проверка пессимистической блокировки
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

    # ==================================================================
    # МЯГКОЕ УДАЛЕНИЕ (Правило №40, часть 6) + контроль доступа
    # ==================================================================
    async def mark_deleted(
        self,
        db: AsyncSession,
        *,
        warehouse_id: uuid.UUID,
        user: UserProtocol,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> InvWarehouseModel:
        """Мягкое удаление с проверкой блокировки и контроля доступа."""
        warehouse = await self.get_for_user(
            db,
            warehouse_id=warehouse_id,
            user=user,
            tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден")

        # ✅ Проверка права на удаление: can_delete (ТЗ §5.2.4)
        access_service = AccessService(db)
        warehouse_doc: DocumentProtocol = typing_cast("DocumentProtocol", warehouse)
        access = await access_service.resolve_access(user, warehouse_doc)
        if not access.can_delete:
            raise WarehouseNotFoundError("Склад не найден")

        # ✅ Правило №40, часть 6.1: проверка блокировки перед удалением
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