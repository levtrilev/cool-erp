import uuid

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud.base import CRUDBase
from app.core.permissions.models import PermissionModel
from app.core.permissions.schemas import (
    PermissionCreateSchema,
    PermissionUpdateSchema,
)
from app.core.roles.models import RoleModel


class CRUDPermission(CRUDBase[PermissionModel, PermissionCreateSchema, PermissionUpdateSchema]):
    """
    CRUD для Permission.

    ✅ Правило №31: новые методы не переопределяют сигнатуры базового класса.
    Используем уникальные имена: create_permission, update_permission, delete_permission.
    """

    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        role_id: uuid.UUID | None = None,
        current_tenant_id: uuid.UUID | None = None,
        is_superadmin: bool = False,
    ) -> tuple[list[PermissionModel], int]:
        """Список полномочий с фильтрацией."""
        stmt = select(PermissionModel)
        count_stmt = select(func.count()).select_from(PermissionModel)

        # ✅ Правило №26: фильтрация по tenant_id
        if not is_superadmin and current_tenant_id:
            stmt = stmt.where(PermissionModel.tenant_id == current_tenant_id)
            count_stmt = count_stmt.where(PermissionModel.tenant_id == current_tenant_id)

        if role_id:
            stmt = stmt.where(PermissionModel.role_id == role_id)
            count_stmt = count_stmt.where(PermissionModel.role_id == role_id)

        if search:
            search_filter = PermissionModel.doctype.ilike(f"%{search}%")
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = (await db.execute(count_stmt)).scalar_one()
        stmt = stmt.offset(skip).limit(limit).order_by(PermissionModel.doctype)
        items = list((await db.execute(stmt)).scalars().all())

        return items, total

    async def get_permission(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        current_tenant_id: uuid.UUID | None = None,
        is_superadmin: bool = False,
    ) -> PermissionModel | None:
        """Получение одного полномочия с проверкой доступа."""
        stmt = select(PermissionModel).where(PermissionModel.id == item_id)
        if not is_superadmin and current_tenant_id:
            stmt = stmt.where(PermissionModel.tenant_id == current_tenant_id)
        return (await db.execute(stmt)).scalar_one_or_none()

    async def create_permission(
        self,
        db: AsyncSession,
        obj_in: PermissionCreateSchema,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> PermissionModel:
        """
        Создание permission.

        ✅ КРИТИЧНО: tenant_id берётся ИЗ РОЛИ, а не из obj_in или current_tenant_id.
        """
        # ✅ ШАГ 1: Загружаем роль
        role_stmt = select(RoleModel).where(RoleModel.id == obj_in.role_id)
        role = (await db.execute(role_stmt)).scalar_one_or_none()

        if role is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Роль не найдена")

        # ✅ ШАГ 2: Проверка прав доступа к роли
        if not is_superadmin and role.tenant_id != current_tenant_id:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail="Нет доступа к роли другой организации",
            )

        # ✅ ШАГ 3: Берём tenant_id из роли
        target_tenant_id: uuid.UUID = role.tenant_id

        # ✅ ШАГ 4: Создаём permission с корректным tenant_id
        data_dict = obj_in.model_dump(exclude={"tenant_id"})
        db_obj = PermissionModel(**data_dict, tenant_id=target_tenant_id)

        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_permission(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        obj_in: PermissionUpdateSchema,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> PermissionModel:
        """Обновление существующего permission (без дублирования)."""
        stmt = select(PermissionModel).where(PermissionModel.id == item_id)
        if not is_superadmin:
            stmt = stmt.where(PermissionModel.tenant_id == current_tenant_id)

        db_obj = (await db.execute(stmt)).scalar_one_or_none()
        if not db_obj:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail="Полномочие не найдено или нет доступа к нему",
            )

        # ✅ Обновляем поля существующей записи
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"tenant_id", "role_id"})
        for key, value in update_data.items():
            setattr(db_obj, key, value)

        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete_permission(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> PermissionModel:
        """Удаление одного полномочия."""
        stmt = select(PermissionModel).where(PermissionModel.id == item_id)
        if not is_superadmin:
            stmt = stmt.where(PermissionModel.tenant_id == current_tenant_id)

        db_obj = (await db.execute(stmt)).scalar_one_or_none()
        if not db_obj:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Полномочие не найдено")

        await db.delete(db_obj)
        await db.flush()
        return db_obj

    async def delete_by_role_id(
        self,
        db: AsyncSession,
        role_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> int:
        """
        Массовое удаление всех permission для конкретной роли.

        Returns:
            Количество удалённых записей.
        """
        # ✅ Проверка прав доступа к роли
        role_stmt = select(RoleModel).where(RoleModel.id == role_id)
        role = (await db.execute(role_stmt)).scalar_one_or_none()

        if role is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Роль не найдена")

        if not is_superadmin and role.tenant_id != current_tenant_id:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail="Нет доступа к роли другой организации",
            )

        # ✅ Массовое удаление
        stmt = delete(PermissionModel).where(PermissionModel.role_id == role_id)
        
        # ✅ cast к CursorResult для доступа к rowcount
        result = await db.execute(stmt)
        await db.flush()
        # ✅ Безопасное получение rowcount без использования cast.
        # getattr возвращает Any, поэтому оборачиваем в int() для строгой типизации.
        # Fallback 0 на случай, если атрибут отсутствует (хотя для DELETE он есть всегда).
        rowcount: int = int(getattr(result, "rowcount", 0))
        return rowcount



crud_permission = CRUDPermission(PermissionModel)