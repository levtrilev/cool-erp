from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.sections.models import SectionModel
from app.core.users.models import UserModel
from app.core.roles.models import RoleModel
from app.core.tenants.models import TenantModel
from app.modules.inventory.warehouses.models import InvWarehouseModel
from app.modules.sales.goods.models import SalesGoodsModel
from app.core.notes.models import NotesModel
from app.core.doctypes.models import DoctypeModel

async def get_entity_name(db: AsyncSession, entity_type: str, entity_id: UUID) -> str:
    """Возвращает название сущности по её типу и ID.

    Args:
        db: Асинхронная сессия SQLAlchemy
        entity_type: Тип сущности (section, user, role, tenant, warehouse, goods, note, doctype)
        entity_id: UUID сущности

    Returns:
        str: Название сущности или пустая строка, если не найдено
    """
    model_map = {
        "section": SectionModel,
        "user": UserModel,
        "role": RoleModel,
        "tenant": TenantModel,
        "warehouse": InvWarehouseModel,
        "goods": SalesGoodsModel,
        "note": NotesModel,
        "doctype": DoctypeModel,
    }

    model = model_map.get(entity_type)
    if not model:
        return ""

    try:
        stmt = select(model.name).where(model.id == entity_id)
        result = await db.execute(stmt)
        name = result.scalar_one_or_none()
        return str(name) if name else ""
    except Exception:
        return ""

async def get_user_emails(db: AsyncSession, user_ids: List[UUID]) -> List[str]:
    """Возвращает список email пользователей по их ID.

    Args:
        db: Асинхронная сессия SQLAlchemy
        user_ids: Список UUID пользователей

    Returns:
        List[str]: Список email пользователей
    """
    if not user_ids:
        return []

    stmt = select(UserModel.email).where(UserModel.id.in_(user_ids))
    result = await db.execute(stmt)
    emails = [email for email, in result.all()]
    return emails

async def get_user_names(db: AsyncSession, user_ids: List[UUID]) -> List[str]:
    """Возвращает список имен пользователей по их ID.

    Args:
        db: Асинхронная сессия SQLAlchemy
        user_ids: Список UUID пользователей

    Returns:
        List[str]: Список имен пользователей
    """
    if not user_ids:
        return []

    stmt = select(UserModel.name).where(UserModel.id.in_(user_ids))
    result = await db.execute(stmt)
    names = [name for name, in result.all()]
    return names
