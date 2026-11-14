import logging
from typing import cast
from uuid import UUID

from sqlalchemy import ColumnElement, Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sections.models import SectionModel
from app.core.users.models import UserModel
from app.core.roles.models import RoleModel
from app.core.tenants.models import TenantModel
from app.modules.inventory.warehouses.models import InvWarehouseModel
from app.modules.sales.goods.models import SalesGoodsModel
from app.core.notes.models import NotesModel
from app.core.doctypes.models import DoctypeModel


logger = logging.getLogger(__name__)

# entity_type -> (модель, имя колонки с «названием»)
_MODEL_NAME_FIELD: dict[str, tuple[type, str]] = {
    "section": (SectionModel, "name"),
    "user": (UserModel, "name"),
    "role": (RoleModel, "name"),
    "tenant": (TenantModel, "name"),
    "warehouse": (InvWarehouseModel, "name"),
    "goods": (SalesGoodsModel, "name"),
    "note": (NotesModel, "title"),
    "doctype": (DoctypeModel, "doctype_name"),
}

async def get_user_emails(db: AsyncSession, user_ids: list[UUID]) -> list[str]:
    """Возвращает список email пользователей по их ID.

    Args:
        db: Асинхронная сессия SQLAlchemy
        user_ids: Список UUID пользователей

    Returns:
        Список email пользователей
    """
    if not user_ids:
        return []

    stmt = select(UserModel.email).where(UserModel.id.in_(user_ids))
    result = await db.execute(stmt)
    emails = [email for email, in result.all()]
    return emails

async def get_entity_name(db: AsyncSession, entity_type: str, entity_id: UUID) -> str:
    """Возвращает название сущности по её типу и ID."""
    entry = _MODEL_NAME_FIELD.get(entity_type)
    if entry is None:
        return ""

    model, name_field = entry
    try:
        name_col = cast(ColumnElement[str], getattr(model, name_field))
        id_col = cast(ColumnElement[UUID], getattr(model, "id"))
        stmt: Select[tuple[str]] = select(name_col).where(id_col == entity_id)
        result = await db.execute(stmt)
        name = result.scalar_one_or_none()
        return str(name) if name else ""
    except AttributeError:
        # опечатка в имени колонки в _MODEL_NAME_FIELD — это баг конфигурации,
        # логируем и возвращаем пустую строку, но не прячем от наблюдаемости
        logger.exception("Invalid column %r for entity_type=%s", name_field, entity_type)
        return ""
    except SQLAlchemyError:
        # ошибки БД (например, таблица не создана) — не валим аудит
        logger.exception("DB error fetching name for %s:%s", entity_type, entity_id)
        return ""