import uuid
from fastapi import HTTPException
from sqlalchemy import select, func     #, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions.models import PermissionModel
from app.core.permissions.schemas import PermissionCreateSchema, PermissionUpdateSchema

class CRUDPermission:
    # def __init__(self, model):
    #     self.model = model

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
        stmt = select(PermissionModel)
        count_stmt = select(func.count()).select_from(PermissionModel)

        # ✅ Правило №26: Фильтрация по tenant_id
        if not is_superadmin and current_tenant_id:
            stmt = stmt.where(PermissionModel.tenant_id == current_tenant_id)
            count_stmt = count_stmt.where(PermissionModel.tenant_id == current_tenant_id)

        # Дополнительный фильтр по роли (удобно для экрана редактирования роли)
        if role_id:
            stmt = stmt.where(PermissionModel.role_id == role_id)
            count_stmt = count_stmt.where(PermissionModel.role_id == role_id)

        if search:
            search_filter = PermissionModel.doctype.ilike(f"%{search}%")
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()
        
        stmt = stmt.offset(skip).limit(limit).order_by(PermissionModel.doctype)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def get(
        self, 
        db: AsyncSession, 
        item_id: uuid.UUID, 
        current_tenant_id: uuid.UUID | None = None, 
        is_superadmin: bool = False
    ) -> PermissionModel | None:
        stmt = select(PermissionModel).where(PermissionModel.id == item_id)
        if not is_superadmin and current_tenant_id:
            stmt = stmt.where(PermissionModel.tenant_id == current_tenant_id)
            
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self, 
        db: AsyncSession, 
        data: PermissionCreateSchema, 
        current_tenant_id: uuid.UUID, 
        is_superadmin: bool = False
    ) -> PermissionModel:
        if not is_superadmin and data.tenant_id != current_tenant_id:
            raise HTTPException(status_code=403, detail="Нельзя создавать полномочия для другой организации")
        
        if not is_superadmin:
            data.tenant_id = current_tenant_id

        db_obj = PermissionModel(**data.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, 
        db: AsyncSession, 
        item_id: uuid.UUID, 
        data: PermissionUpdateSchema, 
        current_tenant_id: uuid.UUID, 
        is_superadmin: bool = False
    ) -> PermissionModel:
        stmt = select(PermissionModel).where(PermissionModel.id == item_id)
        if not is_superadmin:
            stmt = stmt.where(PermissionModel.tenant_id == current_tenant_id)
            
        result = await db.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if not db_obj:
            raise HTTPException(status_code=404, detail="Полномочие не найдено")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_obj, key, value)
            
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(
        self, 
        db: AsyncSession, 
        item_id: uuid.UUID, 
        current_tenant_id: uuid.UUID, 
        is_superadmin: bool = False
    ) -> PermissionModel:
        stmt = select(PermissionModel).where(PermissionModel.id == item_id)
        if not is_superadmin:
            stmt = stmt.where(PermissionModel.tenant_id == current_tenant_id)
            
        result = await db.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if not db_obj:
            raise HTTPException(status_code=404, detail="Полномочие не найдено")

        await db.delete(db_obj)
        await db.commit()
        return db_obj

    # Специальный метод для массового удаления полномочий роли (удобно при синхронизации на фронте)
    async def delete_by_role_id(
        self, 
        db: AsyncSession, 
        role_id: uuid.UUID, 
        current_tenant_id: uuid.UUID, 
        is_superadmin: bool = False
    ) -> PermissionModel | None:
        obj = await self.get(db, role_id, current_tenant_id, is_superadmin)

        if not obj:
            return None
            
        await db.delete(obj)
        await db.flush()
        return obj

        async def delete_by_role_id(
        self, 
        db: AsyncSession, 
        role_id: uuid.UUID, 
        current_tenant_id: uuid.UUID, 
        is_superadmin: bool = False
    ) -> int:
            """Массовое удаление полномочий для конкретной роли."""
        from sqlalchemy import delete
        
        stmt = delete(self.model).where(self.model.role_id == role_id)
        
        # ✅ Правило №26: Защита от удаления полномочий чужого тенанта
        if not is_superadmin:
            stmt = stmt.where(self.model.tenant_id == current_tenant_id)
            
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

crud_permission = CRUDPermission()