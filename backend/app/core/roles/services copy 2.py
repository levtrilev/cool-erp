import logging
import uuid
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions.models import PermissionModel
from app.core.permissions.crud import crud_permission
from app.core.permissions.schemas import PermissionCreateSchema, PermissionUpdateSchema
from app.core.roles.models import RoleModel
from app.core.roles.crud import crud_role
from app.core.roles.schemas import RoleSaveSchema, RoleCreateSchema, RoleUpdateSchema
from app.core.users.models import UserModel

logger = logging.getLogger(__name__)


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
        logger.info(f"[save_role] START: role_id={role_id}, user_ids={data.user_ids}")

        # ============================================================
        # 1. Создаем или обновляем саму роль
        # ============================================================
        if role_id:
            # ✅ Получаем существующую роль для проверки смены организации
            existing_role = await crud_role.get(
                db,
                item_id=role_id,
                current_tenant_id=current_tenant_id,
                is_superadmin=is_superadmin,
            )
            if not existing_role:
                raise HTTPException(status_code=404, detail="Роль не найдена")

            # ✅ ПРОВЕРКА: суперадмин пытается сменить организацию роли
            if (
                is_superadmin
                and data.tenant_id
                and data.tenant_id != existing_role.tenant_id
            ):
                # Проверяем наличие связей в БД
                assigned = await self._check_role_assignments(db, existing_role)
                if assigned:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Для роли '{existing_role.name}' уже назначены: "
                            f"{', '.join(assigned)}. "
                            f"Нельзя изменить организацию. Сначала удалите все назначения."
                        ),
                    )

            # Если проверка пройдена — обновляем роль
            update_data = RoleUpdateSchema(
                name=data.name,
                description=data.description,
                section_ids=data.section_ids,
                section_names=data.section_names,
                tenant_id=data.tenant_id if is_superadmin else None,  # ✅ Только суперадмин
            )
            role = await crud_role.update(
                db,
                item_id=role_id,
                data=update_data,
                current_tenant_id=current_tenant_id,
                is_superadmin=is_superadmin,
            )
        else:
            create_data = RoleCreateSchema(
                name=data.name,
                description=data.description,
                tenant_id=data.tenant_id,
                section_ids=data.section_ids,
                section_names=data.section_names,
            )
            role = await crud_role.create(
                db,
                data=create_data,
                current_tenant_id=current_tenant_id,
                is_superadmin=is_superadmin,
            )

        logger.info(f"[save_role] Role saved: id={role.id}, name={role.name}")

        # ============================================================
        # 2. Синхронизация полномочий (без изменений)
        # ============================================================
        stmt = select(PermissionModel).where(PermissionModel.role_id == role.id)
        if not is_superadmin:
            stmt = stmt.where(PermissionModel.tenant_id == current_tenant_id)
        result = await db.execute(stmt)
        existing_permissions = {p.id: p for p in result.scalars().all()}

        incoming_perm_ids: set[uuid.UUID] = set()

        if data.permissions:
            for perm_data in data.permissions:
                if perm_data.id and perm_data.id in existing_permissions:
                    perm_dict = perm_data.model_dump(exclude={"id"})
                    perm_dict["role_id"] = role.id
                    perm_dict["tenant_id"] = current_tenant_id
                    perm_dict["role_name"] = role.name
                    update_schema = PermissionUpdateSchema(**perm_dict)
                    await crud_permission.update(
                        db,
                        item_id=perm_data.id,
                        data=update_schema,
                        current_tenant_id=current_tenant_id,
                        is_superadmin=is_superadmin,
                    )
                    incoming_perm_ids.add(perm_data.id)
                else:
                    perm_dict = perm_data.model_dump()
                    perm_dict["role_id"] = role.id
                    perm_dict["tenant_id"] = current_tenant_id
                    perm_dict["role_name"] = role.name
                    perm_dict.pop("id", None)
                    safe_perm_data = PermissionCreateSchema(**perm_dict)
                    new_perm = await crud_permission.create(
                        db,
                        data=safe_perm_data,
                        current_tenant_id=current_tenant_id,
                        is_superadmin=is_superadmin,
                    )
                    incoming_perm_ids.add(new_perm.id)

        perms_to_delete = set(existing_permissions.keys()) - incoming_perm_ids
        for perm_id in perms_to_delete:
            await crud_permission.delete(
                db,
                item_id=perm_id,
                current_tenant_id=current_tenant_id,
                is_superadmin=is_superadmin,
            )

        # ============================================================
        # 3. Синхронизация пользователей (без изменений)
        # ============================================================
        if data.user_ids is not None:
            logger.info(f"[save_role] Syncing users: target_user_ids={data.user_ids}")
            target_user_ids: set[uuid.UUID] = set(data.user_ids)
            # ✅ Используем organization роли (а не текущего пользователя) для поиска
            tenant_for_users = role.tenant_id
            stmt = select(UserModel).where(UserModel.tenant_id == tenant_for_users)
            result = await db.execute(stmt)
            all_tenant_users = result.scalars().all()

            logger.info(f"[save_role] Loaded {len(all_tenant_users)} users for tenant {tenant_for_users}")

            changed_count = 0
            for user in all_tenant_users:
                current_role_ids: set[uuid.UUID] = set(user.role_ids or [])
                updated = False

                if user.id in target_user_ids:
                    if role.id not in current_role_ids:
                        current_role_ids.add(role.id)
                        updated = True
                else:
                    if role.id in current_role_ids:
                        current_role_ids.discard(role.id)
                        updated = True

                if updated:
                    user.role_ids = list(current_role_ids)
                    changed_count += 1
                    logger.info(f"[save_role] User {user.id} ({user.name}) updated: role_ids={user.role_ids}")

            logger.info(f"[save_role] Users sync complete: {changed_count} users changed")

        # ============================================================
        # 4. Единый commit
        # ============================================================
        await db.commit()
        logger.info(f"[save_role] Transaction committed successfully")
        await db.refresh(role, attribute_names=["permissions"])
        logger.info(f"[save_role] SUCCESS: role={role.id}")
        return role

    async def _check_role_assignments(
        self, db: AsyncSession, role: RoleModel
    ) -> list[str]:
        """
        Проверяет наличие назначений для роли.
        Возвращает список типов назначений: ["Разделы", "Полномочия", "Пользователи"].
        """
        assigned: list[str] = []

        # 1. Проверяем разделы (поле section_ids в RoleModel)
        if role.section_ids:
            assigned.append("Разделы")

        # 2. Проверяем полномочия (COUNT в PermissionModel)
        perm_count_stmt = (
            select(func.count())
            .select_from(PermissionModel)
            .where(PermissionModel.role_id == role.id)
        )
        perm_count = (await db.execute(perm_count_stmt)).scalar() or 0
        if perm_count > 0:
            assigned.append("Полномочия")

        # 3. Проверяем пользователей (PostgreSQL ARRAY.contains через .any())
        user_count_stmt = (
            select(func.count())
            .select_from(UserModel)
            .where(
                UserModel.role_ids.isnot(None),
                UserModel.role_ids.contains([role.id]),
            )
        )
        user_count = (await db.execute(user_count_stmt)).scalar() or 0
        if user_count > 0:
            assigned.append("Пользователи")

        logger.info(
            f"[_check_role_assignments] role={role.id}, assigned={assigned}"
        )
        return assigned


role_service = RoleService()