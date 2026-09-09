import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles.models import RoleModel
from app.core.roles.crud import crud_role
from app.core.roles.schemas import RoleSaveSchema, RoleCreateSchema, RoleUpdateSchema
from app.core.permissions.crud import crud_permission
from app.core.permissions.schemas import PermissionCreateSchema
from app.core.users.models import UserModel


class RoleService:
    """
    Сервис для управления ролями с их связями (полномочия и пользователи).
    Обеспечивает атомарность операций в рамках одной транзакции.
    """

    async def save_role(
        self,
        db: AsyncSession,
        data: RoleSaveSchema,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool,
        role_id: uuid.UUID | None = None,
    ) -> RoleModel:
        # 1. Создаем или обновляем саму роль
        if role_id:
            # Подготовка данных только для полей роли (игнорируем permissions и user_ids на этом шаге)
            update_data = RoleUpdateSchema(
                name=data.name,
                description=data.description,
                section_ids=data.section_ids,
                section_names=data.section_names,
            )
            role = await crud_role.update(
                db, 
                item_id=role_id, 
                data=update_data, 
                current_tenant_id=current_tenant_id, 
                is_superadmin=is_superadmin
            )
        else:
            create_data = RoleCreateSchema(
                name=data.name,
                description=data.description,
                tenant_id=data.tenant_id, # Берем из payload, но CRUD проверит его на совпадение с current_tenant_id
                section_ids=data.section_ids,
                section_names=data.section_names,
            )
            role = await crud_role.create(
                db, 
                data=create_data, 
                current_tenant_id=current_tenant_id, 
                is_superadmin=is_superadmin
            )

        # 2. Синхронизация полномочий (Permissions)
        # Удаляем все старые полномочия этой роли
        await crud_permission.delete_by_role_id(
            db, 
            role_id=role.id, 
            current_tenant_id=current_tenant_id,
            is_superadmin=is_superadmin
        )
        
        # Создаем новые полномочия из переданного списка
        if data.permissions:
            for perm_data in data.permissions:
                # ✅ Правило №26: Жесткая привязка к текущему тенанту и роли
                perm_dict = perm_data.model_dump()
                perm_dict['role_id'] = role.id
                perm_dict['tenant_id'] = current_tenant_id
                perm_dict['role_name'] = role.name # Денормализация для UI
                
                safe_perm_data = PermissionCreateSchema(**perm_dict)
                await crud_permission.create(
                    db,
                    data=safe_perm_data,
                    current_tenant_id=current_tenant_id,
                    is_superadmin=is_superadmin
                )

        # 3. Синхронизация пользователей (Users)
        # Если передан список user_ids (даже пустой), мы обновляем привязки
        if data.user_ids is not None:
            target_user_ids = set(data.user_ids)
            
            # Получаем всех пользователей текущего тенанта (Правило №26)
            stmt = select(UserModel).where(UserModel.tenant_id == current_tenant_id)
            result = await db.execute(stmt)
            all_tenant_users = result.scalars().all()
            
            for user in all_tenant_users:
                current_role_ids = set(user.role_ids or [])
                updated = False
                
                if user.id in target_user_ids:
                    # Пользователь должен иметь эту роль
                    if role.id not in current_role_ids:
                        current_role_ids.add(role.id)
                        updated = True
                else:
                    # Пользователь НЕ должен иметь эту роль
                    if role.id in current_role_ids:
                        current_role_ids.remove(role.id)
                        updated = True
                
                if updated:
                    user.role_ids = list(current_role_ids)
                    db.add(user)

        # 4. Коммитим все изменения одной транзакцией
        await db.commit()
        
        # Возвращаем обновленный объект роли (с подгруженными relationships благодаря lazy="selectin")
        await db.refresh(role)
        return role


role_service = RoleService()