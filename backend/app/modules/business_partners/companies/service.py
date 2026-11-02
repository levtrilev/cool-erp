"""Сервис компаний с публикацией событий репликации и контролем доступа."""
import uuid
import logging
from typing import TYPE_CHECKING, cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.outbox import outbox
from app.modules.business_partners.companies.crud import crud_company
from app.modules.business_partners.companies.models import BpCompanyModel
from app.modules.business_partners.companies.schemas import (
    BpCompanyCreateSchema,
    BpCompanyUpdateSchema,
)
from app.core.access.schemas import UserProtocol

# ✅ Избегаем циклического импорта — UserModel нужен только для типизации
if TYPE_CHECKING:
    from app.core.users.models import UserModel

logger = logging.getLogger(__name__)


class CompanyService:
    """Публичный сервис домена business_partners."""

    # ==================================================================
    # СОЗДАНИЕ КОМПАНИИ
    # ==================================================================
    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: BpCompanyCreateSchema,
        user: "UserModel",  # ✅ НОВОЕ: для контроля доступа и установки author_id
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """
        Создание компании + публикация события для репликации.
        
        Параметры:
            user: объект текущего пользователя (для author_id и created_by_user_id)
            user_id: ID пользователя (дублирует user.id для обратной совместимости)
            current_tenant_id: тенант сессии (используется, если tenant_id не передан)
        """
        # ✅ tenant_id: из схемы или из сессии
        tenant_id = obj_in.tenant_id or current_tenant_id
        if not is_superadmin and tenant_id != current_tenant_id:
            raise PermissionError("Нет доступа к другой организации")

        data_dict = obj_in.model_dump(exclude_unset=True)
        data_dict["tenant_id"] = tenant_id
        # ✅ author_id и created_by_user_id — из user
        data_dict["author_id"] = user.id
        data_dict["created_by_user_id"] = user.id

        company = BpCompanyModel(**data_dict)
        db.add(company)
        await db.flush()
        await db.refresh(company)

        # ✅ Публикация события с ПОЛНЫМ контрактом доступа (ТЗ §4.10.4)
        await self._publish_event(db, "business_partners.company.created", company)
        return company

    # ==================================================================
    # ОБНОВЛЕНИЕ КОМПАНИИ
    # ==================================================================
    async def update(
        self,
        db: AsyncSession,
        *,
        company_id: uuid.UUID,
        obj_in: BpCompanyUpdateSchema,
        user: "UserModel",  # ✅ НОВОЕ: для контроля доступа (level >= 2)
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """
        Обновление компании с проверкой блокировок и контроля доступа.
        
        Контроль доступа:
            - crud_company.save_with_version проверяет access.level >= 2
            - Если уровень < 2 — CompanyNotFoundError (404)
        """
        updated = await crud_company.save_with_version(
            db,
            company_id=company_id,
            obj_in=obj_in,
            user=cast(UserProtocol, user),
            tenant_id=current_tenant_id,
            user_id=user_id,
            is_superadmin=is_superadmin,
        )
        # ✅ Публикация события с ПОЛНЫМ контрактом доступа (ТЗ §4.10.4)
        await self._publish_event(db, "business_partners.company.updated", updated)
        return updated

    # ==================================================================
    # МЯГКОЕ УДАЛЕНИЕ КОМПАНИИ
    # ==================================================================
    async def delete(
        self,
        db: AsyncSession,
        *,
        company_id: uuid.UUID,
        user: "UserModel",  # ✅ НОВОЕ: для контроля доступа (can_delete)
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """
        Мягкое удаление компании с проверкой блокировки и контроля доступа.
        
        Контроль доступа:
            - crud_company.mark_deleted проверяет access.can_delete
            - Если can_delete = false — CompanyNotFoundError (404)
        """
        deleted = await crud_company.mark_deleted(
            db,
            company_id=company_id,
            user=cast(UserProtocol, user),
            tenant_id=current_tenant_id,
            user_id=user_id,
            is_superadmin=is_superadmin,
        )
        # ✅ Для удаления достаточно id и is_deleted (контракт доступа не нужен)
        await outbox.publish(
            db,
            event_type="business_partners.company.deleted",
            source_domain="business_partners",
            aggregate_type="bp_companies",
            aggregate_id=company_id,
            payload={"id": str(company_id), "is_deleted": True},
            ordering_key=f"business_partners:bp_companies:{company_id}",
        )
        return deleted

    # ==================================================================
    # ПУБЛИКАЦИЯ СОБЫТИЙ ДЛЯ РЕПЛИКАЦИИ
    # ==================================================================
    async def _publish_event(
        self,
        db: AsyncSession,
        event_type: str,
        company: BpCompanyModel,
    ) -> None:
        """
        Публикация события изменения компании для репликации.
        
        ⚠️ КРИТИЧНО (ТЗ репликации §4.10.4):
        payload ОБЯЗАН содержать все 5 полей контракта доступа:
        tenant_id, section_id, author_id, or_tags, and_tags.
        Без этих полей домен-получатель не сможет вычислить доступ
        через AccessService (нарушение Принципа 2.2 ТЗ).
        """
        await outbox.publish(
            db,
            event_type=event_type,
            source_domain="business_partners",
            aggregate_type="bp_companies",
            aggregate_id=company.id,
            payload={
                # Бизнес-данные
                "id": str(company.id),
                "name": company.name,
                "fullname": company.fullname,
                "inn": company.inn,
                # ✅ КОНТРАКТ ДОСТУПА (§3.3) — все 5 полей обязательны
                "tenant_id": str(company.tenant_id),
                "section_id": str(company.section_id),
                "author_id": str(company.author_id),
                "or_tags": list(company.or_tags or []),
                "and_tags": list(company.and_tags or []),
                "is_deleted": False,
            },
            ordering_key=f"business_partners:bp_companies:{company.id}",
        )


company_service = CompanyService()