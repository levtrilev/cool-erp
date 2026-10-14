import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth.dependencies import get_current_session
from app.core.auth.models import UserSession
from app.core.database import get_db
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.sections.crud import crud_section
from app.core.sections.schemas import (
    SectionCreateSchema,
    SectionResponseSchema,
    SectionUpdateSchema,
)

router = APIRouter(prefix="/sections", tags=["Sections"])


@router.post("/", response_model=ApiResponse[SectionResponseSchema], status_code=201)
async def create_section(
    data: SectionCreateSchema,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Создание нового раздела. tenant_id берется из сессии."""
    db_obj = await crud_section.create(db, data, tenant_id=session.tenant_id)
    await db.commit()
    return ApiResponse(
        success=True,
        message="Раздел создан",
        data=SectionResponseSchema.model_validate(db_obj),
    )


# @router.get("/", response_model=ApiResponse[PaginatedResponse[SectionResponseSchema]])
# async def get_sections(
#     skip: int = 0,
#     limit: int = 10,
#     search: str | None = None,
#     # ✅ НОВОЕ: опциональный tenant_id для суперадмина
#     tenant_id: uuid.UUID | None = None,
#     db: AsyncSession = Depends(get_db),
#     session: UserSession = Depends(get_current_session),
# ):
#     """
#     Получение пагинированного списка разделов с опциональным поиском.
    
#     Если передан tenant_id и пользователь — суперадмин,
#     возвращаются разделы указанного предприятия.
#     """
#     # ✅ Защита: обычный админ не может запросить чужой tenant_id
#     if tenant_id and not session.is_superadmin:
#         raise HTTPException(
#             status_code=403,
#             detail="Только суперадмин может запрашивать разделы другого предприятия",
#         )

#     items, total = await crud_section.get_multi_paginated(
#         db,
#         user_tenant_id=session.tenant_id,
#         skip=skip,
#         limit=limit,
#         search=search,
#         user_is_superadmin=session.is_superadmin,
#         target_tenant_id=tenant_id,  # ✅ Передаём target_tenant_id
#     )
#     return ApiResponse(
#         success=True,
#         message="Разделы получены",
#         data=PaginatedResponse(
#             items=[SectionResponseSchema.model_validate(item) for item in items],
#             total=total,
#             page=(skip // limit) + 1,
#             size=limit,
#         ),
#     )
@router.get("/", response_model=ApiResponse[PaginatedResponse[SectionResponseSchema]])
async def get_sections(
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    tenant_id: uuid.UUID | None = None,  # ✅ НОВЫЙ query-параметр
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    # ✅ Правило №26: Защита от запроса чужих разделов обычным админом
    if tenant_id and not session.is_superadmin:
        tenant_id = session.tenant_id

    items, total = await crud_section.get_multi_paginated(
        db,
        user_tenant_id=session.tenant_id,
        skip=skip,
        limit=limit,
        search=search,
        user_is_superadmin=session.is_superadmin,
        target_tenant_id=tenant_id,  # ✅ Передаём в CRUD
    )
    
    return ApiResponse(
        success=True,
        message="Разделы получены",
        data=PaginatedResponse(
            items=[SectionResponseSchema.model_validate(item) for item in items],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
        ),
    )

@router.get("/{section_id}", response_model=ApiResponse[SectionResponseSchema])
async def get_section(
    section_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Получение одного раздела по ID."""
    db_obj = await crud_section.get(db, id=section_id, tenant_id=session.tenant_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Раздел не найден")
    return ApiResponse(
        success=True,
        message="Раздел получен",
        data=SectionResponseSchema.model_validate(db_obj),
    )


@router.put("/{section_id}", response_model=ApiResponse[SectionResponseSchema])
async def update_section(
    section_id: uuid.UUID,
    data: SectionUpdateSchema,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Обновление существующего раздела."""
    db_obj = await crud_section.get(db, id=section_id, tenant_id=session.tenant_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Раздел не найден")
    updated_obj = await crud_section.update(db, db_obj=db_obj, obj_in=data)
    await db.commit()
    return ApiResponse(
        success=True,
        message="Раздел обновлен",
        data=SectionResponseSchema.model_validate(updated_obj),
    )


@router.delete("/{section_id}", response_model=ApiResponse[SectionResponseSchema])
async def delete_section(
    section_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Удаление раздела."""
    deleted_obj = await crud_section.delete(
        db, id=section_id, tenant_id=session.tenant_id
    )
    if not deleted_obj:
        raise HTTPException(status_code=404, detail="Раздел не найден")
    await db.commit()
    return ApiResponse(
        success=True,
        message="Раздел удален",
        data=SectionResponseSchema.model_validate(deleted_obj),
    )