import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.orm.attributes import flag_modified
from app.core.permissions.models import PermissionModel
from app.core.permissions.crud import crud_permission
from app.core.permissions.schemas import PermissionCreateSchema, PermissionUpdateSchema
from app.core.roles.models import RoleModel
from app.core.roles.crud import crud_role
from app.core.roles.schemas import RoleSaveSchema, RoleCreateSchema, RoleUpdateSchema
from app.core.users.models import UserModel

# ✅ ИСПРАВЛЕНИЕ: __name__ вместо name
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Если логгер не имеет хендлеров — добавляем StreamHandler, чтобы вывод шёл в терминал
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(_handler)


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
    ) -> RoleModel: # type: ignore
        logger.info(f"[save_role] START: role_id={role_id}, user_ids={data.user_ids}")

        # 1. Создаем или обновляем саму роль
        if role_id:
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

        # 2. УМНАЯ СИНХРОНИЗАЦИЯ полномочий (Permissions)
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

        # 3. Синхронизация пользователей (Users)
        # if data.user_ids is not None:
        #     logger.info(
        #         f"[save_role] Syncing users: target_user_ids={data.user_ids}, role_id={role.id}"
        #     )
        #     target_user_ids: set[uuid.UUID] = set(data.user_ids)
        #     stmt = select(UserModel).where(UserModel.tenant_id == current_tenant_id)
        #     result = await db.execute(stmt)
        #     all_tenant_users = result.scalars().all()

        #     logger.info(
        #         f"[save_role] Loaded {len(all_tenant_users)} users for tenant {current_tenant_id}"
        #     )

        #     changed_count = 0
        #     for user in all_tenant_users:
        #         current_role_ids: set[uuid.UUID] = set(user.role_ids or [])
        #         updated = False

        #         if user.id in target_user_ids:
        #             if role.id not in current_role_ids:
        #                 current_role_ids.add(role.id)
        #                 updated = True
        #         else:
        #             if role.id in current_role_ids:
        #                 current_role_ids.discard(role.id)
        #                 updated = True

        #         if updated:
        #             # ✅ ИСПРАВЛЕНИЕ: Добавляем flag_modified для ARRAY полей
        #             user.role_ids = list(current_role_ids)
        #             flag_modified(user, "role_ids")
        #             db.add(user)
        #             changed_count += 1
        #             logger.info(
        #                 f"[save_role] User {user.id} ({user.name}) updated: role_ids={user.role_ids}"
        #             )

        #     logger.info(
        #         f"[save_role] Users sync complete: {changed_count} users changed"
        #     )

    # 3. Синхронизация пользователей (Users)
    # ✅ ИСПРАВЛЕНИЕ: Приведение всех UUID к строкам для гарантированного сравнения
        if data.user_ids is not None:
            logger.info(
                f"[save_role] Syncing users: target_user_ids={data.user_ids}, role_id={role.id}"
            )

            # ✅ Приводим все ID к строкам для сравнения
            target_user_ids_str: set[str] = {str(uid) for uid in data.user_ids}
            role_id_str: str = str(role.id)

            logger.info(
                f"[save_role] target_user_ids_str={target_user_ids_str}, role_id_str={role_id_str}"
            )

            stmt = select(UserModel).where(UserModel.tenant_id == current_tenant_id)
            result = await db.execute(stmt)
            all_tenant_users = result.scalars().all()

            logger.info(
                f"[save_role] Loaded {len(all_tenant_users)} users for tenant {current_tenant_id}"
            )

            changed_count = 0
            for user in all_tenant_users:
                user_id_str = str(user.id)

                # ✅ Приводим все role_ids к строкам
                current_role_ids_str: set[str] = {str(rid) for rid in (user.role_ids or [])}

                logger.info(
                    f"[save_role] Processing user {user.name}: "
                    f"id={user_id_str}, current_role_ids={current_role_ids_str}"
                )

                updated = False

                if user_id_str in target_user_ids_str:
                    # Пользователь должен иметь эту роль
                    if role_id_str not in current_role_ids_str:
                        current_role_ids_str.add(role_id_str)
                        updated = True
                        logger.info(
                            f"[save_role] Adding role {role_id_str} to user {user_id_str}"
                        )
                else:
                    # Пользователь НЕ должен иметь эту роль
                    if role_id_str in current_role_ids_str:
                        current_role_ids_str.discard(role_id_str)
                        updated = True
                        logger.info(
                            f"[save_role] Removing role {role_id_str} from user {user_id_str}"
                        )

                if updated:
                    # ✅ Преобразуем обратно в UUID для записи в БД
                    user.role_ids = [uuid.UUID(rid) for rid in current_role_ids_str]
                    db.add(user)
                    changed_count += 1

                    logger.info(
                        f"[save_role] User {user.id} ({user.name}) updated: role_ids={user.role_ids}"
                    )

            logger.info(f"[save_role] Users sync complete: {changed_count} users changed")

            # 4. Единый commit всей транзакции
            await db.commit()
            logger.info(f"[save_role] Transaction committed successfully")

            await db.refresh(role, attribute_names=["permissions"])
            logger.info(f"[save_role] SUCCESS: role={role.id}")
            return role


role_service = RoleService()
