# type: ignore

"""Тесты регистрации новой организации с полной структурой доступа."""

import uuid # pyright: ignore[reportUnusedImport]

import pytest
import pytest_asyncio # pyright: ignore[reportUnusedImport]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions.models import PermissionModel
from app.core.roles.models import RoleModel
from app.core.sections.models import SectionModel, SectionType
from app.core.tenants.models import TenantModel
from app.core.users.models import UserModel


@pytest.mark.asyncio
class TestNewTenantRegistration:
    """Тесты регистрации нового пользователя с новой организацией."""

    async def test_register_new_tenant_creates_tenant(
        self, client, db_session: AsyncSession # type: ignore
    ):
        """Регистрация создаёт новую организацию."""
        response = await client.post( # type: ignore
            "/users/public/register",
            json={
                "name": "Тестовый Админ",
                "email": "admin@test.org",
                "password": "password123",
                "tenant_name": "Тестовая Организация",
            },
        )
        assert response.status_code == 201 # type: ignore
        data = response.json()
        assert data["is_new_tenant"] is True
        assert data["is_admin"] is True
        assert data["tenant_name"] == "Тестовая Организация"

        # Проверяем, что организация создана в БД
        tenant = (
            await db_session.execute(
                select(TenantModel).where(
                    TenantModel.name == "Тестовая Организация"
                )
            )
        ).scalar_one_or_none()
        assert tenant is not None
        assert tenant.active is True

    async def test_register_new_tenant_creates_default_section(
        self, client, db_session: AsyncSession
    ):
        """Регистрация создаёт раздел «Общий-<Организация>»."""
        # Находим созданную организацию
        tenant = (
            await db_session.execute(
                select(TenantModel).where(
                    TenantModel.name == "Тестовая Организация"
                )
            )
        ).scalar_one()

        # Проверяем, что раздел создан
        section = (
            await db_session.execute(
                select(SectionModel).where(
                    SectionModel.tenant_id == tenant.id,
                    SectionModel.section_type == SectionType.TENANT_DEFAULT,
                )
            )
        ).scalar_one_or_none()
        assert section is not None
        assert section.name == "Общий-Тестовая Организация"

    async def test_register_new_tenant_creates_platform_section(
        self, client, db_session: AsyncSession
    ):
        """Регистрация создаёт или использует платформенный раздел «Общий»."""
        # Проверяем, что платформенный раздел существует
        platform_section = (
            await db_session.execute(
                select(SectionModel).where(
                    SectionModel.section_type == SectionType.PLATFORM
                )
            )
        ).scalar_one_or_none()
        assert platform_section is not None
        assert platform_section.name == "Общий"
        assert platform_section.tenant_id is None

    async def test_register_new_tenant_creates_admin_role(
        self, client, db_session: AsyncSession
    ):
        """Регистрация создаёт роль администратора организации."""
        tenant = (
            await db_session.execute(
                select(TenantModel).where(
                    TenantModel.name == "Тестовая Организация"
                )
            )
        ).scalar_one()

        role = (
            await db_session.execute(
                select(RoleModel).where(
                    RoleModel.tenant_id == tenant.id,
                    RoleModel.name == "Администратор Тестовая Организация",
                )
            )
        ).scalar_one_or_none()
        assert role is not None
        assert role.description is not None

    async def test_admin_role_contains_both_sections(
        self, client, db_session: AsyncSession
    ):
        """Роль администратора содержит оба раздела: платформенный и тенантный."""
        tenant = (
            await db_session.execute(
                select(TenantModel).where(
                    TenantModel.name == "Тестовая Организация"
                )
            )
        ).scalar_one()

        role = (
            await db_session.execute(
                select(RoleModel).where(
                    RoleModel.tenant_id == tenant.id,
                    RoleModel.name == "Администратор Тестовая Организация",
                )
            )
        ).scalar_one()

        # Проверяем, что роль содержит оба раздела
        assert role.section_ids is not None
        assert len(role.section_ids) == 2

        # Проверяем, что один из разделов — платформенный
        platform_section = (
            await db_session.execute(
                select(SectionModel).where(
                    SectionModel.section_type == SectionType.PLATFORM
                )
            )
        ).scalar_one()
        assert platform_section.id in role.section_ids

        # Проверяем, что второй раздел — тенантный
        tenant_section = (
            await db_session.execute(
                select(SectionModel).where(
                    SectionModel.tenant_id == tenant.id,
                    SectionModel.section_type == SectionType.TENANT_DEFAULT,
                )
            )
        ).scalar_one()
        assert tenant_section.id in role.section_ids

    async def test_register_new_tenant_creates_permissions(
        self, client, db_session: AsyncSession
    ):
        """Регистрация создаёт Permissions для всех активных doctype."""
        tenant = (
            await db_session.execute(
                select(TenantModel).where(
                    TenantModel.name == "Тестовая Организация"
                )
            )
        ).scalar_one()

        role = (
            await db_session.execute(
                select(RoleModel).where(
                    RoleModel.tenant_id == tenant.id,
                    RoleModel.name == "Администратор Тестовая Организация",
                )
            )
        ).scalar_one()

        # Проверяем, что созданы Permissions для всех активных doctype
        permissions = (
            await db_session.execute(
                select(PermissionModel).where(
                    PermissionModel.role_id == role.id,
                    PermissionModel.tenant_id == tenant.id,
                )
            )
        ).scalars().all()

        # Должно быть 3 Permission (для 3 активных doctype из фикстуры)
        assert len(permissions) == 3

        # Проверяем, что каждый Permission имеет полный доступ
        for perm in permissions:
            assert perm.full_access is True
            assert perm.author is True
            assert perm.reader is True
            assert perm.editor is True
            assert perm.can_delete is True
            assert perm.access_by_tags is False

    async def test_register_new_tenant_creates_admin_user(
        self, client, db_session: AsyncSession
    ):
        """Регистрация создаёт пользователя с is_admin=True."""
        user = (
            await db_session.execute(
                select(UserModel).where(UserModel.email == "admin@test.org")
            )
        ).scalar_one_or_none()
        assert user is not None
        assert user.is_admin is True
        assert user.is_superadmin is False

    async def test_admin_user_has_role_assigned(
        self, client, db_session: AsyncSession
    ):
        """Пользователь-администратор имеет назначенную роль."""
        tenant = (
            await db_session.execute(
                select(TenantModel).where(
                    TenantModel.name == "Тестовая Организация"
                )
            )
        ).scalar_one()

        user = (
            await db_session.execute(
                select(UserModel).where(UserModel.email == "admin@test.org")
            )
        ).scalar_one()

        role = (
            await db_session.execute(
                select(RoleModel).where(
                    RoleModel.tenant_id == tenant.id,
                    RoleModel.name == "Администратор Тестовая Организация",
                )
            )
        ).scalar_one()

        # Проверяем, что роль назначена пользователю
        assert user.role_ids is not None
        assert len(user.role_ids) == 1
        assert user.role_ids[0] == role.id

    async def test_admin_can_login(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Администратор может войти в систему."""
        cookies = await login_and_get_cookie("admin@test.org", "password123")
        assert "session_token" in cookies

    async def test_admin_can_read_tenants(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Администратор может видеть свою организацию."""
        cookies = await login_and_get_cookie("admin@test.org", "password123")

        response = await client.get("/tenants/", cookies=cookies)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Обычный пользователь видит только свою организацию
        assert data["data"]["total"] >= 1

    async def test_admin_can_read_users(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Администратор может видеть пользователей своей организации."""
        cookies = await login_and_get_cookie("admin@test.org", "password123")

        response = await client.get("/users/", cookies=cookies)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 1

    async def test_admin_can_read_roles(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Администратор может видеть роли своей организации."""
        cookies = await login_and_get_cookie("admin@test.org", "password123")

        response = await client.get("/roles/", cookies=cookies)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 1

    async def test_admin_can_read_sections(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Администратор может видеть разделы своей организации."""
        cookies = await login_and_get_cookie("admin@test.org", "password123")

        response = await client.get("/sections/", cookies=cookies)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 2  # Минимум 2 раздела: платформенный + тенантный