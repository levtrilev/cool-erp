# type: ignore

"""Тесты регистрации в существующую организацию."""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenants.models import TenantModel
from app.core.users.models import UserModel


@pytest.mark.asyncio
class TestExistingTenantRegistration:
    """Тесты регистрации в существующую организацию."""

    async def test_register_existing_tenant_creates_regular_user(
        self, client, db_session: AsyncSession
    ):
        """Регистрация в существующую организацию создаёт рядового пользователя."""
        # Сначала создаём организацию через первого пользователя
        response = await client.post(
            "/users/public/register",
            json={
                "name": "Первый Админ",
                "email": "first_admin@test.org",
                "password": "password123",
                "tenant_name": "Существующая Организация",
            },
        )
        assert response.status_code == 201
        assert response.json()["is_new_tenant"] is True
        assert response.json()["is_admin"] is True

        # Теперь регистрируем второго пользователя в ту же организацию
        response = await client.post(
            "/users/public/register",
            json={
                "name": "Рядовой Пользователь",
                "email": "regular_user@test.org",
                "password": "password123",
                "tenant_name": "Существующая Организация",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_new_tenant"] is False
        assert data["is_admin"] is False

    async def test_regular_user_has_no_roles(
        self, client, db_session: AsyncSession
    ):
        """Рядовой пользователь не имеет назначенных ролей."""
        user = (
            await db_session.execute(
                select(UserModel).where(
                    UserModel.email == "regular_user@test.org"
                )
            )
        ).scalar_one_or_none()
        assert user is not None
        assert user.role_ids is None or len(user.role_ids) == 0

    async def test_regular_user_is_not_admin(
        self, client, db_session: AsyncSession
    ):
        """Рядовой пользователь не является администратором."""
        user = (
            await db_session.execute(
                select(UserModel).where(
                    UserModel.email == "regular_user@test.org"
                )
            )
        ).scalar_one_or_none()
        assert user is not None
        assert user.is_admin is False
        assert user.is_superadmin is False

    async def test_register_existing_tenant_does_not_create_new_tenant(
        self, client, db_session: AsyncSession
    ):
        """Регистрация в существующую организацию не создаёт новую организацию."""
        # Считаем количество организаций до регистрации
        tenants_before = (
            await db_session.execute(select(TenantModel))
        ).scalars().all()
        count_before = len(tenants_before)

        # Регистрируем пользователя в существующую организацию
        response = await client.post(
            "/users/public/register",
            json={
                "name": "Ещё Один Пользователь",
                "email": "another_user@test.org",
                "password": "password123",
                "tenant_name": "Существующая Организация",
            },
        )
        assert response.status_code == 201
        assert response.json()["is_new_tenant"] is False

        # Проверяем, что количество организаций не изменилось
        tenants_after = (
            await db_session.execute(select(TenantModel))
        ).scalars().all()
        count_after = len(tenants_after)
        assert count_after == count_before

    async def test_regular_user_can_login(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Рядовой пользователь может войти в систему."""
        cookies = await login_and_get_cookie("regular_user@test.org", "password123")
        assert "session_token" in cookies

    async def test_regular_user_can_read_own_tenant(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Рядовой пользователь может видеть свою организацию."""
        cookies = await login_and_get_cookie("regular_user@test.org", "password123")

        response = await client.get("/tenants/", cookies=cookies)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Обычный пользователь видит только свою организацию
        assert data["data"]["total"] == 1

    async def test_regular_user_cannot_create_tenants(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Рядовой пользователь не может создавать организации."""
        cookies = await login_and_get_cookie("regular_user@test.org", "password123")

        response = await client.post(
            "/tenants/",
            cookies=cookies,
            json={"name": "Новая Организация"},
        )
        # Только суперадмин может создавать организации
        assert response.status_code == 403

    async def test_regular_user_cannot_update_tenants(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Рядовой пользователь не может изменять организации."""
        cookies = await login_and_get_cookie("regular_user@test.org", "password123")

        # Получаем свою организацию
        response = await client.get("/tenants/", cookies=cookies)
        tenant_id = response.json()["data"]["items"][0]["id"]

        response = await client.put(
            f"/tenants/{tenant_id}",
            cookies=cookies,
            json={"name": "Изменённая Организация"},
        )
        # Только админ или суперадмин может изменять организации
        assert response.status_code == 403

    async def test_regular_user_cannot_delete_tenants(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Рядовой пользователь не может удалять организации."""
        cookies = await login_and_get_cookie("regular_user@test.org", "password123")

        # Получаем свою организацию
        response = await client.get("/tenants/", cookies=cookies)
        tenant_id = response.json()["data"]["items"][0]["id"]

        response = await client.delete(
            f"/tenants/{tenant_id}",
            cookies=cookies,
        )
        # Только суперадмин может удалять организации
        assert response.status_code == 403