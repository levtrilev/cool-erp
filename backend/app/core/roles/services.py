import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions.models import PermissionModel
from app.core.permissions.crud import crud_permission
from app.core.permissions.schemas import (
    PermissionCreateSchema,
    PermissionUpdateSchema,
)
from app.core.roles.models import RoleModel
from app.core.roles.crud import crud_role
from app.core.roles.schemas import (
    RoleSaveSchema,
    RoleCreateSchema,
    RoleUpdateSchema,
)
from app.core.users.models import UserModel
from app.core.sections.models import SectionModel

# ✅ Правило №36: корректное имя логгера
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
        logger.info(
            "[save_role] START: role_id=%s, user_ids=%s, permissions_count=%s",
            role_id,
            data.user_ids,
            len(data.permissions) if data.permissions else 0,
        )

        # ============================================================
        # 0. ЦЕЛЕВАЯ ОРГАНИЗАЦИЯ РОЛИ — безусловное присваивание
        # ============================================================
        # ✅ Сначала всегда присваиваем значение по умолчанию.
        # Это гарантирует, что имя связано с объектом на любой ветке.
        target_role_tenant_id: uuid.UUID = (
            data.tenant_id if data.tenant_id is not None else current_tenant_id # type: ignore
        )

        if role_id is not None:
            # При обновлении авторитетным источником является БД,
            # а не значение, присланное клиентом.
            existing_role = await crud_role.get(
                db,
                item_id=role_id,
                current_tenant_id=current_tenant_id,
                is_superadmin=is_superadmin,
            )
            if existing_role is None:
                raise HTTPException(status_code=404, detail="Роль не найдена")

            # ✅ Перезаписываем только для существующей роли
            target_role_tenant_id = existing_role.tenant_id

        # ============================================================
        # 0.1. ВАЛИДАЦИЯ: разделы должны принадлежать организации роли
        # ============================================================
        if data.section_ids:
            # Определяем целевую организацию роли
            if role_id:
                # При обновлении — организация существующей роли
                role_for_check = await crud_role.get(
                    db,
                    item_id=role_id,
                    current_tenant_id=current_tenant_id,
                    is_superadmin=is_superadmin,
                )
                if not role_for_check:
                    raise HTTPException(status_code=404, detail="Роль не найдена")
                target_role_tenant_id = role_for_check.tenant_id
            else:
                # При создании — организация из данных или текущая
                target_role_tenant_id = data.tenant_id or current_tenant_id

            # Загружаем все разделы по переданным ID одним запросом
            sections_stmt = select(SectionModel).where(
                SectionModel.id.in_(data.section_ids)
            )
            sections_result = await db.execute(sections_stmt)
            found_sections: list[SectionModel] = list(sections_result.scalars().all())
            found_section_ids: set[uuid.UUID] = {s.id for s in found_sections}

            # Проверка 1: все переданные ID существуют
            missing_ids: set[uuid.UUID] = set(data.section_ids) - found_section_ids
            if missing_ids:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Разделы не найдены: "
                        + ", ".join(str(mid) for mid in missing_ids)
                    ),
                )

            # Проверка 2: каждый раздел принадлежит организации роли
            # или является платформенным (tenant_id IS NULL)
            invalid_section_names: list[str] = []
            for section in found_sections:
                # Платформенный раздел доступен любой организации (ТЗ §4.3)
                if section.tenant_id is None:
                    continue
                # Раздел чужой организации — запрещено
                if section.tenant_id != target_role_tenant_id:
                    invalid_section_names.append(section.name)

            if invalid_section_names:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Попытка добавить для Роли Раздел из другой Организации: "
                        + ", ".join(invalid_section_names)
                    ),
                )

            logger.info(
                "[save_role] Sections validated: %d sections OK for tenant %s",
                len(found_sections),
                target_role_tenant_id,
            )

        # ============================================================
        # 0.2. Проверка уникальности названия роли
        # ============================================================
        if await crud_role.check_name_exists(
            db,
            name=data.name,
            tenant_id=target_role_tenant_id,
            exclude_role_id=role_id,  # При обновлении исключаем саму роль
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Роль с названием '{data.name}' уже существует в этой организации",
            )

        # ============================================================
        # 1. Создаем или обновляем саму роль
        # ============================================================
        if role_id:
            # Получаем существующую роль для проверки смены организации
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

            # ✅ ИСПРАВЛЕНИЕ: Условное создание схемы без промежуточных словарей.
            # tenant_id включается ТОЛЬКО для суперадмина — это гарантирует, что
            # для обычного админа поле будет truly unset, и exclude_unset=True
            # в crud.py его проигнорирует (не запишет NULL в NOT NULL колонку).
            if is_superadmin and data.tenant_id:
                update_data = RoleUpdateSchema(
                    name=data.name,
                    description=data.description,
                    section_ids=data.section_ids,
                    section_names=data.section_names,
                    tenant_id=data.tenant_id,
                )
            else:
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

        logger.info("[save_role] Role saved: id=%s, name=%s", role.id, role.name)

        # ============================================================
        # 2. Синхронизация полномочий (Permissions)
        # ============================================================

        stmt = select(PermissionModel).where(PermissionModel.role_id == role.id)
        if not is_superadmin:
            stmt = stmt.where(PermissionModel.tenant_id == current_tenant_id)
        result = await db.execute(stmt)
        existing_permissions = {p.id: p for p in result.scalars().all()}
        incoming_perm_ids: set[uuid.UUID] = set()

        # ✅ КРИТИЧНО: tenant_id берётся из РОЛИ, а не из сессии пользователя
        # Это гарантирует, что permission всегда принадлежит той же организации,
        # что и роль, независимо от того, кто сохраняет (суперадмин или админ)
        target_tenant_id: uuid.UUID = role.tenant_id

        if data.permissions:
            for perm_data in data.permissions:
                if perm_data.id and perm_data.id in existing_permissions:
                    # ✅ Обновление существующего permission
                    # Исключаем id и tenant_id — они не изменяются
                    perm_dict = perm_data.model_dump(exclude={"id", "tenant_id"})
                    perm_dict["role_id"] = role.id
                    perm_dict["role_name"] = role.name
                    update_schema = PermissionUpdateSchema(**perm_dict)
                    
                    # ✅ Используем переименованный метод (Правило №31)
                    await crud_permission.update_permission(
                        db,
                        item_id=perm_data.id,
                        obj_in=update_schema,
                        current_tenant_id=target_tenant_id,
                        is_superadmin=is_superadmin,
                    )
                    incoming_perm_ids.add(perm_data.id)
                else:
                    # ✅ Создание нового permission
                    perm_dict = perm_data.model_dump(exclude={"id", "tenant_id"})
                    perm_dict["role_id"] = role.id
                    perm_dict["role_name"] = role.name
                    # ✅ ОБЯЗАТЕЛЬНО: добавляем tenant_id из роли в схему
                    # Без этого Pydantic выдаст ValidationError: tenant_id Field required
                    perm_dict["tenant_id"] = target_tenant_id
                    
                    safe_perm_data = PermissionCreateSchema(**perm_dict)
                    
                    # ✅ Используем переименованный метод (Правило №31)
                    new_perm = await crud_permission.create_permission(
                        db,
                        obj_in=safe_perm_data,
                        current_tenant_id=target_tenant_id,
                        is_superadmin=is_superadmin,
                    )
                    incoming_perm_ids.add(new_perm.id)

        # Удаление записей, которых нет во входящем списке
        perms_to_delete = set(existing_permissions.keys()) - incoming_perm_ids
        for perm_id in perms_to_delete:
            # ✅ Используем переименованный метод (Правило №31)
            await crud_permission.delete_permission(
                db,
                item_id=perm_id,
                current_tenant_id=target_tenant_id,
                is_superadmin=is_superadmin,
            )

        logger.info(
            "[save_role] Permissions synced: incoming=%d, deleted=%d",
            len(incoming_perm_ids),
            len(perms_to_delete),
        )

        # ============================================================
        # 3. Синхронизация пользователей (Users)
        # ============================================================
        # ✅ role_ids — это ARRAY(UUID), а не JSONB.
        # flag_modified НЕ нужен — SQLAlchemy отслеживает изменения автоматически.
        # Все UUID работают напрямую, без приведения к строкам.
        if data.user_ids is not None:
            logger.info(
                "[save_role] Syncing users: target_user_ids=%s, role_id=%s",
                data.user_ids,
                role.id,
            )

            target_user_ids: set[uuid.UUID] = set(data.user_ids)

            # ✅ Используем organization роли (а не текущего пользователя)
            tenant_for_users = role.tenant_id
            stmt = select(UserModel).where(UserModel.tenant_id == tenant_for_users)
            result = await db.execute(stmt)
            all_tenant_users = result.scalars().all()

            logger.info(
                "[save_role] Loaded %d users for tenant %s",
                len(all_tenant_users),
                tenant_for_users,
            )

            changed_count = 0
            for user in all_tenant_users:
                # ✅ ARRAY(UUID) автоматически десериализуется в uuid.UUID
                current_role_ids: set[uuid.UUID] = set(user.role_ids or [])
                updated = False

                if user.id in target_user_ids:
                    # Пользователь должен иметь эту роль
                    if role.id not in current_role_ids:
                        current_role_ids.add(role.id)
                        updated = True
                else:
                    # Пользователь НЕ должен иметь эту роль
                    if role.id in current_role_ids:
                        current_role_ids.discard(role.id)
                        updated = True

                if updated:
                    # ✅ Присваиваем новый список (SQLAlchemy отследит изменение для ARRAY)
                    user.role_ids = list(current_role_ids)
                    # ✅ НЕ вызываем flag_modified — для ARRAY это не нужно
                    # ✅ НЕ вызываем db.add(user) — объект уже в сессии
                    changed_count += 1

                    logger.info(
                        "[save_role] User %s (%s) updated: role_ids=%s",
                        user.id,
                        user.name,
                        user.role_ids,
                    )

            logger.info(
                "[save_role] Users sync complete: %d users changed",
                changed_count,
            )

        # ============================================================
        # 4. Единый commit всей агрегированной операции
        # ============================================================
        await db.commit()
        logger.info("[save_role] Transaction committed successfully")

        await db.refresh(role, attribute_names=["permissions"])
        logger.info("[save_role] SUCCESS: role=%s", role.id)
        return role

    async def _check_role_assignments(
        self, db: AsyncSession, role: RoleModel
    ) -> list[str]:
        """
        Проверяет наличие назначений для роли.
        Возвращает список типов назначений: ["Разделы", "Полномочия", "Пользователи"].

        Используется для запрета смены организации роли, если у неё уже есть связи.
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

        # 3. ✅ Проверяем пользователей через .contains() для ARRAY(UUID)
        # Генерирует SQL: role_ids @> ARRAY['uuid']::uuid[]
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
            "[_check_role_assignments] role=%s, assigned=%s",
            role.id,
            assigned,
        )
        return assigned


role_service = RoleService()