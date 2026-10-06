import uuid
# from typing import cast

from fastapi import APIRouter, HTTPException

# ✅ Правило №32: Аннотированные типы для безопасности
from app.core.auth.dependencies import SuperAdminUser, CurrentUser, DBSession
from app.core.doctypes.crud import crud_doctype
from app.core.doctypes.schemas import (
    DoctypeCreateSchema,
    DoctypeUpdateSchema,
    DoctypeResponseSchema,
)
from app.core.schemas import ApiResponse, PaginatedResponse

router = APIRouter(prefix="/doctypes", tags=["Doctypes"])


@router.get("/", response_model=ApiResponse[PaginatedResponse[DoctypeResponseSchema]])
async def get_doctypes(
    current_session: CurrentUser,  # ✅ Правило №32: Аннотированный тип
    db: DBSession,
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
):
    """Получение списка типов документов. Обычные пользователи видят только свои."""
    items, total = await crud_doctype.get_multi_paginated(
        db,
        tenant_id=current_session.tenant_id,
        skip=skip,
        limit=limit,
        search=search,
        user_is_superadmin=current_session.is_superadmin,
    )

    # ✅ 1. Явное создание экземпляра (ОБЯЗАТЕЛЬНО со скобками и аргументами!)
    paginated_data = PaginatedResponse(
        items=[DoctypeResponseSchema.model_validate(item) for item in items],
        total=total,
        page=skip+1,
        size=limit,
    )

    return ApiResponse(
        success=True,
        message="Типы документов получены",
        data=paginated_data,
        # data=PaginatedResponse[DoctypeResponseSchema],
        )
    


@router.post("/", response_model=ApiResponse[DoctypeResponseSchema], status_code=201)
async def create_doctype(
    obj_in: DoctypeCreateSchema,
    current_session: SuperAdminUser,  # ✅ Правило №32: Только суперадмин
    db: DBSession,
):
    """Создание типа документа. Только для суперадмина."""
    obj = await crud_doctype.create(
        db,
        obj_in=obj_in,
        tenant_id=current_session.tenant_id,
        user_is_superadmin=True,
    )
    return ApiResponse(
        success=True,
        message="Тип документа создан",
        data=DoctypeResponseSchema.model_validate(obj),
    )


@router.put("/{doctype_id}", response_model=ApiResponse[DoctypeResponseSchema])
async def update_doctype(
    doctype_id: uuid.UUID,
    obj_in: DoctypeUpdateSchema,
    current_session: SuperAdminUser,
    db: DBSession,
):
    """Обновление типа документа. Только для суперадмина."""
    # ✅ Правило №31: СНАЧАЛА загружаем объект через базовый метод get
    db_obj = await crud_doctype.get(db, id=doctype_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Тип документа не найден")

    # ✅ ЗАТЕМ передаём его в update
    updated_obj = await crud_doctype.update(
        db,
        db_obj=db_obj,
        obj_in=obj_in,
        tenant_id=current_session.tenant_id,
        user_is_superadmin=True,
    )
    return ApiResponse(
        success=True,
        message="Тип документа обновлён",
        data=DoctypeResponseSchema.model_validate(updated_obj),
    )


@router.delete("/{doctype_id}", response_model=ApiResponse[DoctypeResponseSchema])
async def delete_doctype(
    doctype_id: uuid.UUID,
    current_session: SuperAdminUser,
    db: DBSession,
):
    """Удаление типа документа. Только для суперадмина."""
    # ✅ Правило №31: Используем базовый метод remove
    deleted_obj = await crud_doctype.remove(db, id=doctype_id)
    if not deleted_obj:
        raise HTTPException(status_code=404, detail="Тип документа не найден")

    return ApiResponse(
        success=True,
        message="Тип документа удалён",
        data=DoctypeResponseSchema.model_validate(deleted_obj),
    )
