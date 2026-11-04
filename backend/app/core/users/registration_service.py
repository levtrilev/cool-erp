"""Сервис регистрации с полным созданием структуры доступа.

При регистрации нового пользователя с новой организацией создаёт:
  1. Тенант (через crud_tenant.create — создаёт раздел «Общий-<Организация>»)
  2. Роль «Администратор <Организация>» с разделом по умолчанию
  3. Permissions для всех активных doctype (полный доступ)
  4. Пользователя с is_admin=True и назначенной ролью

Всё в одной транзакции. Только flush. Commit выполняется в роутере.
"""
import uuid
import logging

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.doctypes.models import DoctypeModel
from app.core.permissions.models import PermissionModel
from app.core.roles.models import RoleModel
from app.core.sections.models import SectionModel, SectionType
from app.core.sections.crud import crud_section
from app.core.tenants.crud import crud_tenant
from app.core.users.models import UserModel
from app.core.users.schemas import PublicRegisterSchema

logger = logging.getLogger(__name__)


class RegistrationService:
    """Создание организации + полной структуры доступа за одну транзакцию."""

    async def register(
        self,
        db: AsyncSession,
        *,
        user_in: PublicRegisterSchema,
    ) -> tuple[UserModel, bool]:
        """
        Публичная регистрация.

        Если организация существует → создаёт рядового пользователя.
        Если не существует → создаёт полную структуру доступа.

        Возвращает:
            (пользователь, is_new_tenant)

        Важно:
            Только flush. Commit выполняется в роутере (Правило №40, часть 8.1).
        """
        # 1. Проверяем, существует ли организация
        existing_tenant = await crud_tenant.get_by_name(db, name=user_in.tenant_name)

        if existing_tenant is not None:
            # ✅ Организация существует → рядовой пользователь без ролей
            user = await self._create_user(
                db,
                name=user_in.name,
                email=user_in.email,
                password=user_in.password,
                tenant_id=existing_tenant.id,
                is_admin=False,
                role_ids=[],
            )
            logger.info(
                "Регистрация в существующую организацию: %s → %s",
                existing_tenant.name,
                user.email,
            )
            return user, False

        # ✅ Организация не существует → создаём полную структуру доступа

        # 2a. Создаём тенант
        #     crud_tenant.create уже создаёт раздел «Общий-<Организация>»
        #     через crud_section.create_tenant_default (ТЗ §4.4.1)
        tenant = await crud_tenant.create(db, name=user_in.tenant_name)

        # 2b. Находим созданный раздел «Общий-<Организация>»
        tenant_default_section = await self._get_tenant_default_section(db, tenant_id=tenant.id)

        # ✅ 2b-a. Получаем или создаём платформенный раздел «Общий»
        platform_section = await crud_section.get_or_create_platform_default(db)

        # 2c. Создаём роль администратора
        role = await self._create_admin_role(
            db,
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            sections=[
                (tenant_default_section.id, tenant_default_section.name),
                (platform_section.id, platform_section.name),
            ],
        )

        # 2d. Создаём Permissions для всех активных doctype
        await self._create_permissions_for_all_doctypes(
            db,
            role_id=role.id,
            role_name=role.name,
            tenant_id=tenant.id,
            tenant_name=tenant.name,
        )

        # 2e. Создаём пользователя-администратора с назначенной ролью
        user = await self._create_user(
            db,
            name=user_in.name,
            email=user_in.email,
            password=user_in.password,
            tenant_id=tenant.id,
            is_admin=True,
            role_ids=[role.id],
        )

        logger.info(
            "Регистрация завершена: организация=%s, пользователь=%s, "
            "роль=%s, разделы=[%s, %s]",
            tenant.name,
            user.name,
            role.name,
            tenant_default_section.name,
            platform_section.name,
        )

        return user, True

    # ==================================================================
    # ВНУТРЕННИЕ МЕТОДЫ
    # ==================================================================

    async def _get_tenant_default_section(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
    ) -> SectionModel:
        """
        Получение раздела «Общий-<Организация>» для тенанта.

        Раздел создаётся автоматически внутри crud_tenant.create
        через crud_section.create_tenant_default (ТЗ §4.4.1).
        """
        stmt = select(SectionModel).where(
            SectionModel.tenant_id == tenant_id,
            SectionModel.section_type == SectionType.TENANT_DEFAULT,
        )
        section = (await db.execute(stmt)).scalar_one_or_none()
        if section is None:
            # Это не должно произойти, если crud_tenant.create работает корректно.
            # Но защищаемся от рассинхронизации.
            raise RuntimeError(
                f"Раздел «Общий-<Организация>» не найден для тенанта {tenant_id}. "
                "Проверьте, что crud_tenant.create вызывает "
                "crud_section.create_tenant_default."
            )
        return section

    # async def _create_admin_role(
    #     self,
    #     db: AsyncSession,
    #     *,
    #     tenant_id: uuid.UUID,
    #     tenant_name: str,
    #     section_id: uuid.UUID,
    #     section_name: str,
    # ) -> RoleModel:
    #     """
    #     Создание роли администратора организации.

    #     Роль содержит:
    #       - Раздел «Общий-<Организация>» в section_ids
    #       - Описание для аудита

    #     ТЗ §4.2.1: роль без section_ids недействующая.
    #     Мы явно задаём раздел, чтобы роль сразу давала доступ.
    #     """
    #     role = RoleModel(
    #         name=f"Администратор {tenant_name}",
    #         tenant_id=tenant_id,
    #         description="Роль администратора, создана автоматически при регистрации",
    #         section_ids=[section_id],
    #         section_names=[section_name],
    #     )
    #     db.add(role)
    #     await db.flush()
    #     await db.refresh(role)
    #     return role

    async def _create_admin_role(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        tenant_name: str,
        sections: list[tuple[uuid.UUID, str]],
    ) -> RoleModel:
        """
        Создание роли администратора организации.

        Аргументы:
            sections: список кортежей (section_id, section_name),
                      включающий ВСЕ необходимые разделы:
                      - «Общий-<Организация>» (tenant_default)
                      - «Общий» (platform)

        ТЗ §4.2.4: для доступа к общедоступному контенту роль должна
        явно включать Раздел «Общий» и/или «Общий-<Организация>».
        """
        section_ids: list[uuid.UUID] = [s[0] for s in sections]
        section_names: list[str] = [s[1] for s in sections]

        role = RoleModel(
            name=f"Администратор {tenant_name}",
            tenant_id=tenant_id,
            description="Роль администратора, создана автоматически при регистрации",
            section_ids=section_ids,
            section_names=section_names,
        )
        db.add(role)
        await db.flush()
        await db.refresh(role)
        return role

    async def _create_permissions_for_all_doctypes(
        self,
        db: AsyncSession,
        *,
        role_id: uuid.UUID,
        role_name: str,
        tenant_id: uuid.UUID,
        tenant_name: str,
    ) -> None:
        """
        Создание Permissions для всех активных doctype.

        Правило №43: tenant_id Permission = tenant_id роли.
        Мы создаём роль и Permission напрямую, поэтому сами
        устанавливаем корректный tenant_id.

        Каждый Permission:
          - full_access = true (полный доступ)
          - can_delete = true (право удаления)
          - editor, author, reader = true (все уровни)
        """
        stmt = select(DoctypeModel).where(DoctypeModel.is_active.is_(True))
        doctypes: list[DoctypeModel] = list(
            (await db.execute(stmt)).scalars().all()
        )

        if not doctypes:
            logger.warning(
                "Нет активных doctype при регистрации тенанта %s. "
                "Permissions не созданы.",
                tenant_name,
            )
            return

        for dt in doctypes:
            perm = PermissionModel(
                role_id=role_id,
                # ✅ Правило №43: tenant_id берём из роли (тут они совпадают,
                # так как роль создана для этого тенанта)
                tenant_id=tenant_id,
                doctype=dt.doctype,
                doctype_name=dt.doctype_name,
                role_name=role_name,
                tenant_name=tenant_name,
                full_access=True,
                author=True,
                reader=True,
                editor=True,
                can_delete=True,
                access_by_tags=False,
            )
            db.add(perm)

        await db.flush()

        logger.info(
            "Создано %d Permission для роли %s (тенант %s)",
            len(doctypes),
            role_name,
            tenant_name,
        )

    async def _create_user(
        self,
        db: AsyncSession,
        *,
        name: str,
        email: str,
        password: str,
        tenant_id: uuid.UUID,
        is_admin: bool,
        role_ids: list[uuid.UUID],
    ) -> UserModel:
        """
        Создание пользователя с хешированием пароля.

        Аналог crud_user.register_new_user, но с flush вместо commit.
        Commit выполняется в роутере (Правило №40, часть 8.1).
        """
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)

        user = UserModel(
            name=name,
            email=email,
            password=hashed_password.decode("utf-8"),
            tenant_id=tenant_id,
            is_admin=is_admin,
            is_superadmin=False,
            role_ids=role_ids,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user


registration_service = RegistrationService()