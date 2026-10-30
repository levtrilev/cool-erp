"""Сервис компаний с публикацией событий репликации."""
import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.outbox import outbox
from app.modules.business_partners.companies.crud import crud_company
from app.modules.business_partners.companies.models import BpCompanyModel
from app.modules.business_partners.companies.schemas import (
    BpCompanyCreateSchema,
    BpCompanyUpdateSchema,
)

logger = logging.getLogger(__name__)


class CompanyService:
    """Публичный сервис домена business_partners."""

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: BpCompanyCreateSchema,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """Создание компании + публикация события для репликации."""
        tenant_id = obj_in.tenant_id or current_tenant_id
        if not is_superadmin and tenant_id != current_tenant_id:
            raise PermissionError("Нет доступа к другой организации")

        data_dict = obj_in.model_dump(exclude_unset=True)
        data_dict["tenant_id"] = tenant_id
        data_dict["author_id"] = user_id
        data_dict["created_by_user_id"] = user_id

        company = BpCompanyModel(**data_dict)
        db.add(company)
        await db.flush()
        await db.refresh(company)

        await self._publish_event(db, "business_partners.company.created", company)
        return company

    async def update(
        self,
        db: AsyncSession,
        *,
        company_id: uuid.UUID,
        obj_in: BpCompanyUpdateSchema,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """Обновление компании с проверкой блокировок."""
        updated = await crud_company.save_with_version(
            db,
            company_id=company_id,
            obj_in=obj_in,
            tenant_id=current_tenant_id,
            user_id=user_id,
            is_superadmin=is_superadmin,
        )
        await self._publish_event(db, "business_partners.company.updated", updated)
        return updated

    async def delete(
        self,
        db: AsyncSession,
        *,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> BpCompanyModel:
        """Мягкое удаление компании."""
        deleted = await crud_company.mark_deleted(
            db,
            company_id=company_id,
            tenant_id=current_tenant_id,
            user_id=user_id,
            is_superadmin=is_superadmin,
        )
        # await outbox.publish_ordered(
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
        """Публикация события изменения компании для репликации."""
        await outbox.publish(
            db,
            event_type=event_type,
            source_domain="business_partners",
            aggregate_type="bp_companies",
            aggregate_id=company.id,
            payload={
                "id": str(company.id),
                "name": company.name,
                "fullname": company.fullname,
                "inn": company.inn,
                "tenant_id": str(company.tenant_id),
                "is_deleted": False,
            },
            ordering_key=f"business_partners:bp_companies:{company.id}",
        )


company_service = CompanyService()