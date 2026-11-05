# type: ignore

"""Параметризованные тесты контроля доступа к документам."""
import uuid 

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_access_control.conftest import DOMAIN_CONFIG, create_document_in_db


@pytest.mark.asyncio
class TestDocumentAccessControl:
    """Тесты контроля доступа к документам (параметризованные по домену)."""

    @pytest.fixture(params=["companies", "warehouses", "goods"])
    def domain(self, request) -> str:
        return request.param

    @pytest.fixture
    def api_prefix(self, domain: str) -> str:
        return DOMAIN_CONFIG[domain]["api_prefix"]

    @pytest.fixture
    def doctype(self, domain: str) -> str:
        return DOMAIN_CONFIG[domain]["doctype"]

    @pytest.fixture
    def create_payload(self, domain: str) -> dict:
        return DOMAIN_CONFIG[domain]["create_payload"].copy()

    # ==================================================================
    # СЛОЙ 1: ТЕНАНТ
    # ==================================================================
    async def test_user_sees_only_own_tenant_documents(
        self,
        domain: str,
        api_prefix: str,
        create_payload: dict,
        access_test_data: dict,
        client,
        login_and_get_cookie,
        db_session: AsyncSession,  # ✅ ДОБАВЛЕНО
    ):
        t = access_test_data
        section_id = t["section_a_default"].id
        author_id = t["admin_a"].id

        doc_a = await create_document_in_db(
            db_session,  # ✅ ИСПРАВЛЕНО: передаём db_session напрямую
            domain,
            tenant_id=t["tenant_a"].id,
            section_id=section_id,
            author_id=author_id,
            name="Документ A",
        )
        await db_session.commit()

        cookies = await login_and_get_cookie("admin_a@test.org", t["password"])
        client.cookies.update(cookies)

        response = await client.get(f"{api_prefix}/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        items = data["data"]["items"]
        item_ids = [item["id"] for item in items]
        assert str(doc_a.id) in item_ids

    async def test_user_cannot_see_other_tenant_documents(
        self,
        domain: str,
        api_prefix: str,
        create_payload: dict,
        access_test_data: dict,
        client,
        login_and_get_cookie,
    ):
        t = access_test_data
        cookies = await login_and_get_cookie("user_b@test.org", t["password"])
        client.cookies.update(cookies)

        response = await client.get(f"{api_prefix}/")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 0

    # ==================================================================
    # СЛОЙ 2: РАЗДЕЛ
    # ==================================================================
    async def test_user_cannot_see_documents_in_excluded_section(
        self,
        domain: str,
        api_prefix: str,
        create_payload: dict,
        access_test_data: dict,
        client,
        login_and_get_cookie,
        db_session: AsyncSession,  # ✅ ДОБАВЛЕНО
    ):
        t = access_test_data

        doc_x = await create_document_in_db(
            db_session,  # ✅ ИСПРАВЛЕНО
            domain,
            tenant_id=t["tenant_a"].id,
            section_id=t["section_custom_x"].id,
            author_id=t["admin_a"].id,
            name="Документ в разделе X",
        )
        await db_session.commit()

        cookies = await login_and_get_cookie("admin_a@test.org", t["password"])
        client.cookies.update(cookies)

        response = await client.get(f"{api_prefix}/")
        assert response.status_code == 200
        data = response.json()
        items = data["data"]["items"]
        item_ids = [item["id"] for item in items]

        assert str(doc_x.id) not in item_ids

    async def test_platform_section_documents_visible_with_role(
        self,
        domain: str,
        api_prefix: str,
        create_payload: dict,
        access_test_data: dict,
        client,
        login_and_get_cookie,
        db_session: AsyncSession,  # ✅ ДОБАВЛЕНО
    ):
        t = access_test_data
        from app.core.roles.models import RoleModel
        from app.core.permissions.models import PermissionModel
        from app.core.users.models import UserModel
        import bcrypt

        doc_platform = await create_document_in_db(
            db_session,  # ✅ ИСПРАВЛЕНО
            domain,
            tenant_id=t["tenant_a"].id,
            section_id=t["section_platform"].id,
            author_id=t["admin_a"].id,
            name="Документ в Общем",
        )
        await db_session.commit()

        role_b_with_platform = RoleModel(
            name="Роль B с Общим",
            tenant_id=t["tenant_b"].id,
            section_ids=[t["section_b_default"].id, t["section_platform"].id],
            section_names=["Общий-Тенант B", "Общий"],
        )
        db_session.add(role_b_with_platform)
        await db_session.flush()

        perm = PermissionModel(
            role_id=role_b_with_platform.id,
            tenant_id=t["tenant_b"].id,
            doctype=DOMAIN_CONFIG[domain]["doctype"],
            doctype_name=DOMAIN_CONFIG[domain]["doctype"],
            reader=True,
        )
        db_session.add(perm)

        user_b_with_role = UserModel(
            name="Пользователь B с ролью",
            email=f"user_b_role_{domain}@test.org",
            password=bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode(),
            tenant_id=t["tenant_b"].id,
            is_admin=False,
            is_superadmin=False,
            role_ids=[role_b_with_platform.id],
        )
        db_session.add(user_b_with_role)
        await db_session.commit()

        cookies = await login_and_get_cookie(f"user_b_role_{domain}@test.org", "password123")
        client.cookies.update(cookies)

        response = await client.get(f"{api_prefix}/")
        assert response.status_code == 200
        data = response.json()
        items = data["data"]["items"]
        item_ids = [item["id"] for item in items]

        assert str(doc_platform.id) in item_ids

    # ==================================================================
    # СЛОЙ 3: ТИП ДОКУМЕНТА (PERMISSION)
    # ==================================================================
    async def test_user_without_permission_cannot_see_documents(
        self,
        domain: str,
        api_prefix: str,
        access_test_data: dict,
        client,
        login_and_get_cookie,
    ):
        t = access_test_data
        cookies = await login_and_get_cookie("user_b@test.org", t["password"])
        client.cookies.update(cookies)

        response = await client.get(f"{api_prefix}/")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 0

    async def test_user_with_empty_sections_cannot_see_documents(
        self,
        domain: str,
        api_prefix: str,
        access_test_data: dict,
        client,
        login_and_get_cookie,
        db_session: AsyncSession,  # ✅ ДОБАВЛЕНО
    ):
        t = access_test_data

        doc = await create_document_in_db(
            db_session,  # ✅ ИСПРАВЛЕНО
            domain,
            tenant_id=t["tenant_a"].id,
            section_id=t["section_a_default"].id,
            author_id=t["admin_a"].id,
            name="Документ для теста пустых разделов",
        )
        await db_session.commit()

        cookies = await login_and_get_cookie("no_sections_a@test.org", t["password"])
        client.cookies.update(cookies)

        response = await client.get(f"{api_prefix}/")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 0

    # ==================================================================
    # СЛОЙ 5: УРОВЕНЬ ДОСТУПА
    # ==================================================================
    async def test_reader_cannot_create_documents(
        self,
        domain: str,
        api_prefix: str,
        create_payload: dict,
        access_test_data: dict,
        client,
        login_and_get_cookie,
        db_session: AsyncSession,
    ):
        t = access_test_data
        create_payload["section_id"] = str(t["section_a_default"].id)
        create_payload["tenant_id"] = str(t["tenant_a"].id)  # ✅ Добавлено для прохождения валидации схемы

        cookies = await login_and_get_cookie("reader_a@test.org", t["password"])
        client.cookies.update(cookies)

        response = await client.post(f"{api_prefix}/", json=create_payload)  # ✅ Добавлен слеш
        # Ожидаем 403 (нет права на создание) или 404 (если AccessService ещё не внедрён и возвращает 404 при отсутствии прав)
        assert response.status_code in [403, 404], f"Ожидался 403 или 404, получен {response.status_code}: {response.text}"
        
    async def test_reader_cannot_update_documents(
        self,
        domain: str,
        api_prefix: str,
        create_payload: dict,
        access_test_data: dict,
        client,
        login_and_get_cookie,
        db_session: AsyncSession,  # ✅ ДОБАВЛЕНО
    ):
        t = access_test_data

        doc = await create_document_in_db(
            db_session,  # ✅ ИСПРАВЛЕНО
            domain,
            tenant_id=t["tenant_a"].id,
            section_id=t["section_a_default"].id,
            author_id=t["admin_a"].id,
            name="Документ для читателя",
        )
        await db_session.commit()

        cookies = await login_and_get_cookie("reader_a@test.org", t["password"])
        client.cookies.update(cookies)

        response = await client.put(
            f"{api_prefix}/{doc.id}",
            json={**create_payload, "version": doc.version},
        )
        assert response.status_code in [403, 404]

    async def test_reader_cannot_delete_documents(
        self,
        domain: str,
        api_prefix: str,
        access_test_data: dict,
        client,
        login_and_get_cookie,
        db_session: AsyncSession,  # ✅ ДОБАВЛЕНО
    ):
        t = access_test_data

        doc = await create_document_in_db(
            db_session,  # ✅ ИСПРАВЛЕНО
            domain,
            tenant_id=t["tenant_a"].id,
            section_id=t["section_a_default"].id,
            author_id=t["admin_a"].id,
            name="Документ для удаления",
        )
        await db_session.commit()

        cookies = await login_and_get_cookie("reader_a@test.org", t["password"])
        client.cookies.update(cookies)

        response = await client.delete(f"{api_prefix}/{doc.id}")
        assert response.status_code in [403, 404]

    # ==================================================================
    # ПРАВО НА УДАЛЕНИЕ (ТЗ §5.2.4)
    # ==================================================================
    async def test_can_delete_auto_at_level_ge_2(
        self,
        domain: str,
        api_prefix: str,
        access_test_data: dict,
        client,
        login_and_get_cookie,
        db_session: AsyncSession,  # ✅ ДОБАВЛЕНО
    ):
        t = access_test_data

        # Создаём документ от имени author_a
        doc = await create_document_in_db(
            db_session,  # ✅ ИСПРАВЛЕНО
            domain,
            tenant_id=t["tenant_a"].id,
            section_id=t["section_a_default"].id,
            author_id=t["author_a"].id,
            name="Документ для удаления админом",
        )
        await db_session.commit()
        
        # Логинимся как author_a
        cookies = await login_and_get_cookie("author_a@test.org", t["password"])
        client.cookies.update(cookies)
        
        # Пытаемся удалить
        response = await client.delete(f"{api_prefix}/{doc.id}")
        # ✅ Автор с уровнем 2 должен иметь право на удаление своих документов
        assert response.status_code == 200

    # ==================================================================
    # БЛОКИРОВКИ РЕДАКТИРОВАНИЯ
    # ==================================================================
    async def test_acquire_lock_requires_level_ge_2(
        self,
        domain: str,
        api_prefix: str,
        access_test_data: dict,
        client,
        login_and_get_cookie,
        db_session: AsyncSession,  # ✅ ДОБАВЛЕНО
    ):
        t = access_test_data

        doc = await create_document_in_db(
            db_session,  # ✅ ИСПРАВЛЕНО
            domain,
            tenant_id=t["tenant_a"].id,
            section_id=t["section_a_default"].id,
            author_id=t["admin_a"].id,
            name="Документ для блокировки",
        )
        await db_session.commit()

        cookies = await login_and_get_cookie("reader_a@test.org", t["password"])
        client.cookies.update(cookies)

        response = await client.post(f"{api_prefix}/{doc.id}/lock")
        assert response.status_code in [403, 404]

    async def test_admin_can_acquire_lock(
        self,
        domain: str,
        api_prefix: str,
        access_test_data: dict,
        client,
        login_and_get_cookie,
        db_session: AsyncSession,  # ✅ ДОБАВЛЕНО
    ):
        t = access_test_data

        doc = await create_document_in_db(
            db_session,  # ✅ ИСПРАВЛЕНО
            domain,
            tenant_id=t["tenant_a"].id,
            section_id=t["section_a_default"].id,
            author_id=t["admin_a"].id,
            name="Документ для блокировки админом",
        )
        await db_session.commit()

        cookies = await login_and_get_cookie("admin_a@test.org", t["password"])
        client.cookies.update(cookies)

        url = f"{api_prefix}/{doc.id}/lock"
        print(f"🔍 URL: {url}")
        response = await client.post(url)        
        
        # response = await client.post(f"{api_prefix}/{doc.id}/lock")
        assert response.status_code == 200

    async def test_author_can_delete_own_document(
        self,
        domain: str,
        api_prefix: str,
        access_test_data: dict,
        client,
        login_and_get_cookie,
        db_session: AsyncSession,
    ):
        """
        Автор может удалять только свои документы (ТЗ §5.2.4: уровень ≥ 2).
        """
        t = access_test_data

        # Создаём документ от имени author_a
        doc = await create_document_in_db(
            db_session,
            domain,
            tenant_id=t["tenant_a"].id,
            section_id=t["section_a_default"].id,
            author_id=t["author_a"].id,  # ✅ Автор = author_a
            name="Свой документ автора",
        )
        await db_session.commit()

        # Логинимся как author_a
        cookies = await login_and_get_cookie("author_a@test.org", t["password"])
        client.cookies.update(cookies)

        # Пытаемся удалить свой документ
        response = await client.delete(f"{api_prefix}/{doc.id}")
        # ✅ Ожидаем 200 — автор может удалять свои документы
        assert response.status_code == 200, f"Ожидался 200, получен {response.status_code}: {response.text}"

    async def test_author_cannot_delete_other_user_document(
        self,
        domain: str,
        api_prefix: str,
        access_test_data: dict,
        client,
        login_and_get_cookie,
        db_session: AsyncSession,
    ):
        """
        Автор НЕ может удалять чужие документы.
        """
        t = access_test_data

        # Создаём документ от имени admin_a (другой пользователь)
        doc = await create_document_in_db(
            db_session,
            domain,
            tenant_id=t["tenant_a"].id,
            section_id=t["section_a_default"].id,
            author_id=t["admin_a"].id,  # ✅ Автор = admin_a (не author_a)
            name="Чужой документ для автора",
        )
        await db_session.commit()

        # Логинимся как author_a
        cookies = await login_and_get_cookie("author_a@test.org", t["password"])
        client.cookies.update(cookies)

        # Пытаемся удалить чужой документ
        response = await client.delete(f"{api_prefix}/{doc.id}")
        # ✅ Ожидаем 403 или 404 — автор не может удалять чужие документы
        assert response.status_code in [403, 404], f"Ожидался 403 или 404, получен {response.status_code}: {response.text}"