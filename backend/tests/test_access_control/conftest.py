# type: ignore

"""Хелперы для тестов контроля доступа к документам."""
import uuid
from typing import Any

import bcrypt
import pytest
import pytest_asyncio
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions.models import PermissionModel
from app.core.roles.models import RoleModel
from app.core.sections.models import SectionModel, SectionType
from app.core.tenants.models import TenantModel
from app.core.users.models import UserModel


# Конфигурация доменов для параметризации
DOMAIN_CONFIG: dict[str, dict[str, Any]] = {
    "companies": {
        "api_prefix": "/business-partners/companies",
        "doctype": "bp_companies",
        "create_payload": {
            "name": "Тестовая компания",
            "fullname": "Тестовая компания ООО",
            "inn": "1234567890",
        },
        "model_module": "app.modules.business_partners.companies.models",
        "model_class": "BpCompanyModel",
    },
    "warehouses": {
        "api_prefix": "/inventory/warehouses",
        "doctype": "inv_warehouses",
        "create_payload": {
            "name": "Тестовый склад",
            "description": "Описание склада",
        },
        "model_module": "app.modules.inventory.warehouses.models",
        "model_class": "InvWarehouseModel",
    },
    "goods": {
        "api_prefix": "/sales/goods",
        "doctype": "sales_goods",
        "create_payload": {
            "name": "Тестовый товар",
            "description": "Описание товара",
        },
        "model_module": "app.modules.sales.goods.models",
        "model_class": "SalesGoodsModel",
    },
}


def _hash_password(password: str) -> str:
    """Хеширование пароля."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


@pytest_asyncio.fixture(autouse=True)
async def setup_test_data(db_session: AsyncSession):
    """
    Автоматически создаёт тестовые данные для каждого теста.
    Использует ON CONFLICT и LIMIT 1 для защиты от MultipleResultsFound.
    """
    with db_session.no_autoflush:
        domains = [
            ("business_partners", "Бизнес-партнёры"),
            ("inventory", "Склад"),
            ("sales", "Продажи"),
        ]

        domain_ids: dict[str, str] = {}
        for domain_key, domain_name in domains:
            insert_result = await db_session.execute(
                text("""
                    INSERT INTO public.domains (name) 
                    VALUES (:name) 
                    ON CONFLICT (name) DO NOTHING 
                    RETURNING id
                """),
                {"name": domain_name},
            )
            row = insert_result.scalar_one_or_none()
            
            if row is None:
                fetch_result = await db_session.execute(
                    text("SELECT id FROM public.domains WHERE name = :name LIMIT 1"),
                    {"name": domain_name},
                )
                row = fetch_result.scalar()
            
            domain_ids[domain_key] = str(row)

        doctypes_data = [
            {"doctype": "bp_companies", "doctype_name": "Компании", "domain_id": domain_ids["business_partners"]},
            {"doctype": "inv_warehouses", "doctype_name": "Склады", "domain_id": domain_ids["inventory"]},
            {"doctype": "sales_goods", "doctype_name": "Товары", "domain_id": domain_ids["sales"]},
        ]

        for data in doctypes_data:
            await db_session.execute(
                text("""
                    INSERT INTO public.doctypes (domain_id, doctype, doctype_name, is_active) 
                    VALUES (CAST(:domain_id AS uuid), :doctype, :doctype_name, true)
                    ON CONFLICT (doctype) DO NOTHING
                """),
                {
                    "domain_id": data["domain_id"],
                    "doctype": data["doctype"],
                    "doctype_name": data["doctype_name"],
                },
            )

        result = await db_session.execute(
            text("SELECT id FROM public.sections WHERE section_type = :section_type AND tenant_id IS NULL LIMIT 1"),
            {"section_type": SectionType.PLATFORM},
        )
        existing_platform = result.scalar()

        if existing_platform is None:
            platform = SectionModel(
                name="Общий",
                section_type=SectionType.PLATFORM,
                tenant_id=None,
                description="Платформенный общий раздел",
            )
            db_session.add(platform)

    await db_session.commit()


@pytest_asyncio.fixture
async def access_test_data(db_session: AsyncSession):
    """
    Создаёт полную структуру для тестов доступа.
    Идемпотентность: проверяем существование перед созданием.
    """
    # ===== 1. ТЕНАНТЫ =====
    tenant_a = (await db_session.execute(select(TenantModel).where(TenantModel.name == "Тенант A"))).scalar_one_or_none()
    if not tenant_a:
        tenant_a = TenantModel(name="Тенант A", active=True)
        db_session.add(tenant_a)
        await db_session.flush()

    tenant_b = (await db_session.execute(select(TenantModel).where(TenantModel.name == "Тенант B"))).scalar_one_or_none()
    if not tenant_b:
        tenant_b = TenantModel(name="Тенант B", active=True)
        db_session.add(tenant_b)
        await db_session.flush()

    # ===== 2. РАЗДЕЛЫ =====
    section_a_default = (await db_session.execute(select(SectionModel).where(SectionModel.name == "Общий-Тенант A"))).scalar_one_or_none()
    if not section_a_default:
        section_a_default = SectionModel(tenant_id=tenant_a.id, name="Общий-Тенант A", section_type=SectionType.TENANT_DEFAULT)
        db_session.add(section_a_default)
        await db_session.flush()

    section_b_default = (await db_session.execute(select(SectionModel).where(SectionModel.name == "Общий-Тенант B"))).scalar_one_or_none()
    if not section_b_default:
        section_b_default = SectionModel(tenant_id=tenant_b.id, name="Общий-Тенант B", section_type=SectionType.TENANT_DEFAULT)
        db_session.add(section_b_default)
        await db_session.flush()

    section_platform = (await db_session.execute(select(SectionModel).where(SectionModel.name == "Общий", SectionModel.section_type == SectionType.PLATFORM))).scalar_one_or_none()
    if not section_platform:
        section_platform = SectionModel(tenant_id=None, name="Общий", section_type=SectionType.PLATFORM)
        db_session.add(section_platform)
        await db_session.flush()

    section_custom_x = (await db_session.execute(select(SectionModel).where(SectionModel.name == "Раздел X", SectionModel.tenant_id == tenant_a.id))).scalar_one_or_none()
    if not section_custom_x:
        section_custom_x = SectionModel(tenant_id=tenant_a.id, name="Раздел X", section_type=SectionType.CUSTOM)
        db_session.add(section_custom_x)
        await db_session.flush()

    # ===== 3. РОЛИ =====
    role_admin_a = (await db_session.execute(select(RoleModel).where(RoleModel.name == "Админ A", RoleModel.tenant_id == tenant_a.id))).scalar_one_or_none()
    if not role_admin_a:
        role_admin_a = RoleModel(name="Админ A", tenant_id=tenant_a.id, section_ids=[section_a_default.id, section_platform.id], section_names=["Общий-Тенант A", "Общий"])
        db_session.add(role_admin_a)
        await db_session.flush()

    role_reader_a = (await db_session.execute(select(RoleModel).where(RoleModel.name == "Читатель A", RoleModel.tenant_id == tenant_a.id))).scalar_one_or_none()
    if not role_reader_a:
        role_reader_a = RoleModel(name="Читатель A", tenant_id=tenant_a.id, section_ids=[section_a_default.id], section_names=["Общий-Тенант A"])
        db_session.add(role_reader_a)
        await db_session.flush()

    role_no_sections_a = (await db_session.execute(select(RoleModel).where(RoleModel.name == "Без разделов A", RoleModel.tenant_id == tenant_a.id))).scalar_one_or_none()
    if not role_no_sections_a:
        role_no_sections_a = RoleModel(name="Без разделов A", tenant_id=tenant_a.id, section_ids=[], section_names=[])
        db_session.add(role_no_sections_a)
        await db_session.flush()

    # ===== 4. PERMISSIONS =====
    # Очищаем старые permissions для этих ролей
    await db_session.execute(
        delete(PermissionModel).where(
            PermissionModel.role_id.in_([role_admin_a.id, role_reader_a.id, role_no_sections_a.id])
        )
    )
    await db_session.flush()

    doctypes = ["bp_companies", "inv_warehouses", "sales_goods"]

    # Permission для "Админ A" — полный доступ
    for dt in doctypes:
        db_session.add(PermissionModel(role_id=role_admin_a.id, tenant_id=tenant_a.id, doctype=dt, doctype_name=dt, full_access=True, author=True, reader=True, editor=True, can_delete=True))
        db_session.add(PermissionModel(role_id=role_reader_a.id, tenant_id=tenant_a.id, doctype=dt, doctype_name=dt, full_access=False, author=False, reader=True, editor=False, can_delete=False))
        db_session.add(PermissionModel(role_id=role_no_sections_a.id, tenant_id=tenant_a.id, doctype=dt, doctype_name=dt, full_access=True, author=True, reader=True, editor=True, can_delete=True))

    # Permission для "Читатель A" — только reader
    for dt in doctypes:
        db_session.add(PermissionModel(
            role_id=role_reader_a.id, tenant_id=tenant_a.id, doctype=dt, doctype_name=dt,
            full_access=False, author=False, reader=True, editor=False, can_delete=False
        ))

    # ✅ НОВОЕ: Создаём роль "Автор A" с правами только author
    role_author_a = (await db_session.execute(
        select(RoleModel).where(RoleModel.name == "Автор A", RoleModel.tenant_id == tenant_a.id)
    )).scalar_one_or_none()
    if not role_author_a:
        role_author_a = RoleModel(
            name="Автор A",
            tenant_id=tenant_a.id,
            section_ids=[section_a_default.id],
            section_names=["Общий-Тенант A"],
        )
        db_session.add(role_author_a)
        await db_session.flush()

    # Permission для "Автор A" — только author (без editor, без full_access)
    for dt in doctypes:
        db_session.add(PermissionModel(
            role_id=role_author_a.id, tenant_id=tenant_a.id, doctype=dt, doctype_name=dt,
            full_access=False, author=True, reader=True, editor=False, can_delete=False
        ))

    await db_session.flush()

    # ===== 5. ПОЛЬЗОВАТЕЛИ =====
    hashed_password = _hash_password("password123")

    admin_a = (await db_session.execute(select(UserModel).where(UserModel.email == "admin_a@test.org"))).scalar_one_or_none()
    if not admin_a:
        admin_a = UserModel(name="Админ A", email="admin_a@test.org", password=hashed_password, tenant_id=tenant_a.id, is_admin=True, is_superadmin=False, role_ids=[role_admin_a.id])
        db_session.add(admin_a)

    reader_a = (await db_session.execute(select(UserModel).where(UserModel.email == "reader_a@test.org"))).scalar_one_or_none()
    if not reader_a:
        reader_a = UserModel(name="Читатель A", email="reader_a@test.org", password=hashed_password, tenant_id=tenant_a.id, is_admin=False, is_superadmin=False, role_ids=[role_reader_a.id])
        db_session.add(reader_a)

    # ✅ НОВОЕ: Пользователь "Автор A" с правами только author
    author_a = (await db_session.execute(select(UserModel).where(UserModel.email == "author_a@test.org"))).scalar_one_or_none()
    if not author_a:
        author_a = UserModel(
            name="Автор A", email="author_a@test.org", password=hashed_password,
            tenant_id=tenant_a.id, is_admin=False, is_superadmin=False,
            role_ids=[role_author_a.id]
        )
        db_session.add(author_a)

    no_sections_a = (await db_session.execute(select(UserModel).where(UserModel.email == "no_sections_a@test.org"))).scalar_one_or_none()
    if not no_sections_a:
        no_sections_a = UserModel(name="Без разделов A", email="no_sections_a@test.org", password=hashed_password, tenant_id=tenant_a.id, is_admin=False, is_superadmin=False, role_ids=[role_no_sections_a.id])
        db_session.add(no_sections_a)

    user_b = (await db_session.execute(select(UserModel).where(UserModel.email == "user_b@test.org"))).scalar_one_or_none()
    if not user_b:
        user_b = UserModel(name="Пользователь B", email="user_b@test.org", password=hashed_password, tenant_id=tenant_b.id, is_admin=False, is_superadmin=False, role_ids=[])
        db_session.add(user_b)

    await db_session.flush()
    await db_session.commit()

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "section_a_default": section_a_default,
        "section_b_default": section_b_default,
        "section_platform": section_platform,
        "section_custom_x": section_custom_x,
        "role_admin_a": role_admin_a,
        "role_reader_a": role_reader_a,
        "role_author_a": role_author_a,
        "role_no_sections_a": role_no_sections_a,
        "admin_a": admin_a,
        "author_a": author_a,
        "reader_a": reader_a,
        "no_sections_a": no_sections_a,
        "user_b": user_b,
        "password": "password123",
    }


async def create_document_in_db(
    db_session: AsyncSession,
    domain: str,
    *,
    tenant_id: uuid.UUID,
    section_id: uuid.UUID,
    author_id: uuid.UUID,
    name: str,
    extra_fields: dict[str, Any] | None = None,
) -> Any:
    """Создаёт документ напрямую в БД (независимо от CRUD/API)."""
    import importlib
    config = DOMAIN_CONFIG[domain]
    module = importlib.import_module(config["model_module"])
    model_class = getattr(module, config["model_class"])

    data = {
        "name": name,
        "tenant_id": tenant_id,
        "section_id": section_id,
        "author_id": author_id,
        "version": 1,
        "doc_status": "draft",
    }
    if extra_fields:
        data.update(extra_fields)

    doc = model_class(**data)
    db_session.add(doc)
    await db_session.flush()
    await db_session.refresh(doc)
    return doc