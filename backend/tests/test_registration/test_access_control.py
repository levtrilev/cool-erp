# type: ignore

"""Тесты контроля доступа."""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles.models import RoleModel
from app.core.tenants.models import TenantModel
from app.core.users.models import UserModel


@pytest.mark.asyncio
class TestAccessControl:
    """Тесты контроля доступа к документам."""

    async def _get_default_section_id(self, client) -> str | None:
        """Вспомогательный метод для получения ID раздела tenant_default."""
        sections_resp = await client.get("/sections/")
        if sections_resp.status_code != 200:
            return None
        sections_data = sections_resp.json()
        for item in sections_data.get("data", {}).get("items", []):
            if item.get("section_type") == "tenant_default":
                return item["id"]
        if sections_data.get("data", {}).get("items"):
            return sections_data["data"]["items"][0]["id"]
        return None

    async def test_user_without_roles_cannot_read_companies(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Пользователь без ролей не может читать компании."""
        # 1. Создаём организацию с админом и рядовым пользователем
        await client.post(
            "/users/public/register",
            json={
                "name": "Админ",
                "email": "access_admin@test.org",
                "password": "password123",
                "tenant_name": "Организация Доступа",
            },
        )
        await client.post(
            "/users/public/register",
            json={
                "name": "Без Ролей",
                "email": "no_roles@test.org",
                "password": "password123",
                "tenant_name": "Организация Доступа",
            },
        )

        # 2. Админ входит в систему
        admin_cookies = await login_and_get_cookie("access_admin@test.org", "password123")
        client.cookies.update(admin_cookies)  # ✅ Корректная установка cookies

        # 3. Получаем ID раздела по умолчанию
        section_id = await self._get_default_section_id(client)
        assert section_id is not None, "Раздел tenant_default не найден"

        # 4. Админ создаёт компанию (с обязательным section_id)
        response = await client.post(
            "/business-partners/companies/",
            json={
                "name": "Тестовая Компания",
                "fullname": "Тестовая Компания ООО",
                "inn": "1234567890",
                "section_id": section_id,  # ✅ Обязательное поле
            },
        )
        assert response.status_code == 200, f"Failed to create company: {response.text}"

        # 5. Пользователь без ролей входит в систему
        no_roles_cookies = await login_and_get_cookie("no_roles@test.org", "password123")
        client.cookies.update(no_roles_cookies)

        # 6. Пользователь без ролей пытается прочитать компании
        response = await client.get("/business-partners/companies/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Пользователь без ролей не видит компании (пустой список)
        assert data["data"]["total"] == 0

    async def test_user_with_role_can_read_companies(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Пользователь с ролью может читать компании."""
        admin_cookies = await login_and_get_cookie("access_admin@test.org", "password123")
        client.cookies.update(admin_cookies)
        
        section_id = await self._get_default_section_id(client)
        if section_id:
            await client.post(
                "/business-partners/companies/",
                json={
                    "name": "Компания Админа",
                    "fullname": "Компания Админа ООО",
                    "inn": "1111111111",
                    "section_id": section_id,
                },
            )
            
        response = await client.get("/business-partners/companies/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 1

    async def test_user_without_roles_cannot_create_companies(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Пользователь без ролей не может создавать компании."""
        no_roles_cookies = await login_and_get_cookie("no_roles@test.org", "password123")
        client.cookies.update(no_roles_cookies)
        
        section_id = await self._get_default_section_id(client)
        
        response = await client.post(
            "/business-partners/companies/",
            json={
                "name": "Несанкционированная Компания",
                "fullname": "Несанкционированная Компания ООО",
                "inn": "0987654321",
                "section_id": section_id or "00000000-0000-0000-0000-000000000000",
            },
        )
        # Ожидаем 403 (Forbidden) или 404 (Not Found), если контроль доступа внедрён в service.py
        assert response.status_code in [403, 404], f"Ожидался 403 или 404, получен {response.status_code}: {response.text}"

    async def test_user_with_role_can_create_companies(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Пользователь с ролью может создавать компании."""
        admin_cookies = await login_and_get_cookie("access_admin@test.org", "password123")
        client.cookies.update(admin_cookies)
        
        section_id = await self._get_default_section_id(client)
        assert section_id is not None
        
        response = await client.post(
            "/business-partners/companies/",
            json={
                "name": "Авторизованная Компания",
                "fullname": "Авторизованная Компания ООО",
                "inn": "2222222222",
                "section_id": section_id,
            },
        )
        assert response.status_code == 200

    async def test_user_without_roles_cannot_read_warehouses(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Пользователь без ролей не может читать склады."""
        no_roles_cookies = await login_and_get_cookie("no_roles@test.org", "password123")
        client.cookies.update(no_roles_cookies)
        
        response = await client.get("/inventory/warehouses/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 0

    async def test_user_without_roles_cannot_read_goods(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Пользователь без ролей не может читать товары."""
        no_roles_cookies = await login_and_get_cookie("no_roles@test.org", "password123")
        client.cookies.update(no_roles_cookies)
        
        response = await client.get("/sales/goods/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 0

    async def test_admin_can_read_warehouses(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Администратор может читать склады."""
        admin_cookies = await login_and_get_cookie("access_admin@test.org", "password123")
        client.cookies.update(admin_cookies)
        
        response = await client.get("/inventory/warehouses/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_admin_can_read_goods(
        self, client, db_session: AsyncSession, login_and_get_cookie
    ):
        """Администратор может читать товары."""
        admin_cookies = await login_and_get_cookie("access_admin@test.org", "password123")
        client.cookies.update(admin_cookies)
        
        response = await client.get("/sales/goods/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True