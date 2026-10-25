import uuid
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.roles.models import RoleModel
from app.core.roles.schemas import RoleCreateSchema, RoleUpdateSchema


class CRUDRole:
    async def get_multi(
        self,
        db: AsyncSession,
        current_tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        is_superadmin: bool = False,
    ) -> tuple[list[RoleModel], int]:
        stmt = select(RoleModel)
        count_stmt = select(func.count()).select_from(RoleModel)

        if not is_superadmin and current_tenant_id:
            stmt = stmt.where(RoleModel.tenant_id == current_tenant_id)
            count_stmt = count_stmt.where(RoleModel.tenant_id == current_tenant_id)

        if search:
            search_filter = RoleModel.name.ilike(f"%{search}%")
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = stmt.offset(skip).limit(limit).order_by(RoleModel.name)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def get(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        current_tenant_id: uuid.UUID | None = None,
        is_superadmin: bool = False,
    ) -> RoleModel | None:
        stmt = select(RoleModel).where(RoleModel.id == item_id)
        if not is_superadmin and current_tenant_id:
            stmt = stmt.where(RoleModel.tenant_id == current_tenant_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        data: RoleCreateSchema,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> RoleModel:
        if not is_superadmin and data.tenant_id != current_tenant_id:
            raise HTTPException(
                status_code=403,
                detail="Нельзя создавать роли для другой организации",
            )
        if not is_superadmin:
            data.tenant_id = current_tenant_id

        db_obj = RoleModel(**data.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        data: RoleUpdateSchema,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> RoleModel:
        stmt = select(RoleModel).where(RoleModel.id == item_id)
        if not is_superadmin:
            stmt = stmt.where(RoleModel.tenant_id == current_tenant_id)
        result = await db.execute(stmt)
        db_obj = result.scalar_one_or_none()

        # ✅ ИСПРАВЛЕНИЕ: assert для явного указания Pyright, что db_obj не None
        assert db_obj is not None, "Роль не найдена"

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_obj, key, value)

        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> RoleModel:
        stmt = select(RoleModel).where(RoleModel.id == item_id)
        if not is_superadmin:
            stmt = stmt.where(RoleModel.tenant_id == current_tenant_id)
        result = await db.execute(stmt)
        db_obj = result.scalar_one_or_none()

        # ✅ ИСПРАВЛЕНИЕ: assert для явного указания Pyright, что db_obj не None
        assert db_obj is not None, "Роль не найдена"

        await db.delete(db_obj)
        await db.flush()
        return db_obj

    async def check_name_exists(
        self,
        db: AsyncSession,
        *,
        name: str,
        tenant_id: uuid.UUID,
        exclude_role_id: uuid.UUID | None = None,
    ) -> bool:
        """
        Проверяет, существует ли роль с таким названием в организации.
        
        Параметры:
            name: название роли для проверки
            tenant_id: ID организации
            exclude_role_id: ID роли для исключения (при обновлении)
        
        Возвращает:
            True, если роль с таким названием уже существует
        """
        stmt = select(RoleModel).where(
            RoleModel.name == name,
            RoleModel.tenant_id == tenant_id,
        )
        if exclude_role_id is not None:
            stmt = stmt.where(RoleModel.id != exclude_role_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

crud_role = CRUDRole()