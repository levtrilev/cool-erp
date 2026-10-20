import uuid

from fastapi import APIRouter, HTTPException

from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.sections.crud import crud_section
from app.core.sections.exceptions import (
    SectionHasDocumentsError,
    SectionNotAdminError,
    SectionNotFoundError,
    SectionNotInTenantError, # pyright: ignore[reportUnusedImport]
    SectionProtectedError,
)
from app.core.sections.schemas import (
    SectionCreateSchema,
    SectionResponseSchema,
    SectionUpdateSchema,
)

router = APIRouter(prefix="/sections", tags=["Sections"])


@router.get("/", response_model=ApiResponse[PaginatedResponse[SectionResponseSchema]])
async def get_sections(
    current_session: CurrentUser,
    db: DBSession,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    target_tenant_id: uuid.UUID | None = None,  # ✅ для суперадмина
) -> ApiResponse[PaginatedResponse[SectionResponseSchema]]:
    """Список разделов, видимых пользователю."""
    items, total = await crud_section.list_for_user(
        db,
        tenant_id=current_session.tenant_id,
        is_superadmin=current_session.is_superadmin,
        target_tenant_id=target_tenant_id,  # ✅ Передаём параметр
        skip=skip,
        limit=limit,
        search=search,
    )

    paginated = PaginatedResponse[SectionResponseSchema](
        items=[SectionResponseSchema.model_validate(item) for item in items],
        total=total,
        page=(skip // limit) + 1,
        size=limit,
    )

    return ApiResponse(success=True, message="Разделы получены", data=paginated)


@router.post("/", response_model=ApiResponse[SectionResponseSchema], status_code=201)
async def create_section(
    obj_in: SectionCreateSchema,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SectionResponseSchema]:
    """Создание произвольного раздела (только админ/суперадмин)."""
    try:
        section = await crud_section.create_custom(
            db,
            obj_in=obj_in,
            tenant_id=current_session.tenant_id,
            user_id=current_session.user.id,
            is_admin=current_session.user.is_admin,
            is_superadmin=current_session.is_superadmin,
        )
    except SectionNotAdminError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(section)

    return ApiResponse(
        success=True,
        message="Раздел создан",
        data=SectionResponseSchema.model_validate(section),
    )


@router.get("/{section_id}", response_model=ApiResponse[SectionResponseSchema])
async def get_section(
    section_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SectionResponseSchema]:
    """Один раздел."""
    section = await crud_section.get_for_user(
        db,
        section_id=section_id,
        tenant_id=current_session.tenant_id,
        is_superadmin=current_session.is_superadmin,
    )

    if section is None:
        raise HTTPException(status_code=404, detail="Раздел не найден")

    return ApiResponse(
        success=True,
        message="Раздел получен",
        data=SectionResponseSchema.model_validate(section),
    )


@router.put("/{section_id}", response_model=ApiResponse[SectionResponseSchema])
async def update_section(
    section_id: uuid.UUID,
    obj_in: SectionUpdateSchema,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SectionResponseSchema]:
    """Переименование произвольного раздела."""
    try:
        section = await crud_section.update_custom(
            db,
            section_id=section_id,
            obj_in=obj_in,
            tenant_id=current_session.tenant_id,
            user_id=current_session.user.id,
            is_admin=current_session.user.is_admin,
            is_superadmin=current_session.is_superadmin,
        )
    except SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SectionProtectedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SectionNotAdminError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(section)

    return ApiResponse(
        success=True,
        message="Раздел обновлён",
        data=SectionResponseSchema.model_validate(section),
    )


@router.delete("/{section_id}", response_model=ApiResponse[SectionResponseSchema])
async def delete_section(
    section_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SectionResponseSchema]:
    """Удаление произвольного раздела."""
    try:
        section = await crud_section.delete_custom(
            db,
            section_id=section_id,
            tenant_id=current_session.tenant_id,
            user_id=current_session.user.id,
            is_admin=current_session.user.is_admin,
            is_superadmin=current_session.is_superadmin,
        )
    except SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SectionProtectedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SectionNotAdminError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SectionHasDocumentsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    await db.commit()

    return ApiResponse(
        success=True,
        message="Раздел удалён",
        data=SectionResponseSchema.model_validate(section),
    )