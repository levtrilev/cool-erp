import uuid

# from typing import cast

from fastapi import APIRouter, HTTPException

# ✅ Правило №32: Аннотированные типы для безопасности
from app.core.auth.dependencies import SuperAdminUser, CurrentUser, DBSession
from app.core.domains.crud import crud_domain
from app.core.domains.schemas import (
    DomainCreateSchema,
    DomainUpdateSchema,
    DomainResponseSchema,
)
from app.core.schemas import ApiResponse, PaginatedResponse

router = APIRouter(prefix="/domains", tags=["Domains"])


@router.get("/", response_model=ApiResponse[PaginatedResponse[DomainResponseSchema]])
async def get_domains(
    current_session: CurrentUser,  # ✅ Правило №32: Аннотированный тип
    db: DBSession,
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
):
    """
    Получение списка доменов.
    Доступно всем авторизованным пользователям (для справочников).
    """
    # ✅ Правило №31: Используем базовый метод get_multi_paginated
    items, total = await crud_domain.get_multi_paginated(
        db,
        tenant_id=current_session.tenant_id,  # Не используется для domains, но передаём для совместимости
        skip=skip,
        limit=limit,
        search=search,
        search_field="name",  # ✅ Поиск по name
        user_is_superadmin=current_session.is_superadmin,
    )
    # ✅ 1. Явное создание экземпляра (ОБЯЗАТЕЛЬНО со скобками!)
    paginated_data = PaginatedResponse(
        items=[DomainResponseSchema.model_validate(item) for item in items],
        total=total,
        page=skip + 1,
        size=limit,
    )
    return (
        ApiResponse(
            success=True,
            message="Домены получены",
            data=paginated_data,
        )
    )


@router.post("/", response_model=ApiResponse[DomainResponseSchema], status_code=201)
async def create_domain(
    obj_in: DomainCreateSchema,
    current_session: SuperAdminUser,  # ✅ Правило №32: Только суперадмин
    db: DBSession,
):
    """Создание домена. Только для суперадмина."""
    obj = await crud_domain.create(
        db,
        obj_in=obj_in,
        user_is_superadmin=True,
    )
    return ApiResponse(
        success=True,
        message="Домен создан",
        data=DomainResponseSchema.model_validate(obj),
    )


@router.put("/{domain_id}", response_model=ApiResponse[DomainResponseSchema])
async def update_domain(
    domain_id: uuid.UUID,
    obj_in: DomainUpdateSchema,
    current_session: SuperAdminUser,
    db: DBSession,
):
    """Обновление домена. Только для суперадмина."""
    # ✅ Правило №31: СНАЧАЛА загружаем объект через базовый метод get
    db_obj = await crud_domain.get(db, id=domain_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Домен не найден")

    # ✅ ЗАТЕМ передаём его в update
    updated_obj = await crud_domain.update(
        db,
        db_obj=db_obj,
        obj_in=obj_in,
        user_is_superadmin=True,
    )
    return ApiResponse(
        success=True,
        message="Домен обновлён",
        data=DomainResponseSchema.model_validate(updated_obj),
    )


@router.delete("/{domain_id}", response_model=ApiResponse[DomainResponseSchema])
async def delete_domain(
    domain_id: uuid.UUID,
    current_session: SuperAdminUser,
    db: DBSession,
):
    """Удаление домена. Только для суперадмина."""
    # ✅ Правило №31: Используем переопределённый метод remove (с защитой)
    deleted_obj = await crud_domain.remove(db, id=domain_id)
    if not deleted_obj:
        raise HTTPException(status_code=404, detail="Домен не найден")

    return ApiResponse(
        success=True,
        message="Домен удалён",
        data=DomainResponseSchema.model_validate(deleted_obj),
    )
