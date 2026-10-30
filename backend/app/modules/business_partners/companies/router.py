"""FastAPI роутер для компаний с блокировками (Правило №40, часть 7)."""
from typing import cast
import uuid

from fastapi import APIRouter, HTTPException

from app.core.auth.dependencies import DBSession, CurrentUser
from app.core.schemas import ApiResponse, PaginatedResponse
from app.modules.business_partners.companies.crud import (
    crud_company,
    CompanyEditingLockedError,
    CompanyNotFoundError,
    CompanyVersionConflictError,
)
from app.modules.business_partners.companies.schemas import (
    BpCompanyCreateSchema,
    BpCompanyResponseSchema,
    BpCompanyUpdateSchema,
)
from app.modules.business_partners.companies.service import company_service
from app.core.access.schemas import UserProtocol

router = APIRouter(
    prefix="/business-partners/companies",
    tags=["Business Partners: Companies"],
)


@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[BpCompanyResponseSchema]],
)
async def list_companies(
    db: DBSession,
    session: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
) -> ApiResponse[PaginatedResponse[BpCompanyResponseSchema]]:
    """Список компаний."""
    items, total = await crud_company.get_multi(
        db,
        tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
        skip=skip,
        limit=limit,
        search=search,
    )
    return ApiResponse(
        success=True,
        message="Компании получены",
        data=PaginatedResponse(
            items=[BpCompanyResponseSchema.model_validate(i) for i in items],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
        ),
    )


@router.post(
    "/",
    response_model=ApiResponse[BpCompanyResponseSchema],
)
async def create_company(
    data: BpCompanyCreateSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[BpCompanyResponseSchema]:
    """Создание компании."""
    try:
        company = await company_service.create(
            db,
            obj_in=data,
            user_id=cast(UserProtocol, session).id,
            current_tenant_id=session.tenant_id,
            is_superadmin=session.is_superadmin,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    # ✅ Правило №40, часть 8.1: commit выполняется в роутере
    await db.commit()
    await db.refresh(company)
    return ApiResponse(
        success=True,
        message="Компания создана",
        data=BpCompanyResponseSchema.model_validate(company),
    )


@router.get(
    "/{company_id}",
    response_model=ApiResponse[BpCompanyResponseSchema],
)
async def get_company(
    company_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[BpCompanyResponseSchema]:
    """Одна компания."""
    company = await crud_company.get_for_user(
        db,
        company_id=company_id,
        tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
    )
    if company is None:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    return ApiResponse(
        success=True,
        message="Компания получена",
        data=BpCompanyResponseSchema.model_validate(company),
    )


@router.put(
    "/{company_id}",
    response_model=ApiResponse[BpCompanyResponseSchema],
)
async def update_company(
    company_id: uuid.UUID,
    data: BpCompanyUpdateSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[BpCompanyResponseSchema]:
    """Сохранение с проверкой версии (409) и блокировки (423)."""
    try:
        company = await company_service.update(
            db,
            company_id=company_id,
            obj_in=data,
            user_id=cast(UserProtocol, session).id,
            current_tenant_id=session.tenant_id,
            is_superadmin=session.is_superadmin,
        )
    except CompanyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CompanyVersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CompanyEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(company)
    return ApiResponse(
        success=True,
        message="Компания обновлена",
        data=BpCompanyResponseSchema.model_validate(company),
    )


@router.delete(
    "/{company_id}",
    response_model=ApiResponse[BpCompanyResponseSchema],
)
async def delete_company(
    company_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[BpCompanyResponseSchema]:
    """Мягкое удаление с проверкой блокировки (423)."""
    try:
        company = await company_service.delete(
            db,
            company_id=company_id,
            user_id=cast(UserProtocol, session).id,
            current_tenant_id=session.tenant_id,
            is_superadmin=session.is_superadmin,
        )
    except CompanyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CompanyEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    return ApiResponse(
        success=True,
        message="Компания удалена",
        data=BpCompanyResponseSchema.model_validate(company),
    )


# ==================================================================
# БЛОКИРОВКИ РЕДАКТИРОВАНИЯ (Правило №40, часть 7.1)
# ==================================================================


@router.post(
    "/{company_id}/lock",
    response_model=ApiResponse[BpCompanyResponseSchema],
)
async def acquire_company_lock(
    company_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[BpCompanyResponseSchema]:
    """Захват пессимистической блокировки редактирования."""
    try:
        company = await crud_company.acquire_editing_lock(
            db,
            company_id=company_id,
            tenant_id=session.tenant_id,
            user_id=cast(UserProtocol, session).id,
            is_superadmin=session.is_superadmin,
        )
    except CompanyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CompanyEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(company)
    return ApiResponse(
        success=True,
        message="Блокировка захвачена",
        data=BpCompanyResponseSchema.model_validate(company),
    )


@router.delete(
    "/{company_id}/lock",
    response_model=ApiResponse[BpCompanyResponseSchema],
)
async def release_company_lock(
    company_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[BpCompanyResponseSchema]:
    """Освобождение пессимистической блокировки редактирования."""
    try:
        company = await crud_company.release_editing_lock(
            db,
            company_id=company_id,
            tenant_id=session.tenant_id,
            user_id=cast(UserProtocol, session).id,
            is_superadmin=session.is_superadmin,
        )
    except CompanyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CompanyEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(company)
    return ApiResponse(
        success=True,
        message="Блокировка освобождена",
        data=BpCompanyResponseSchema.model_validate(company),
    )