"""backend/app/core/sections/router.py"""
import logging
import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.core.audit import service as audit_service
from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.sections.crud import crud_section
from app.core.sections.exceptions import (
    SectionHasDocumentsError,
    SectionNotAdminError,
    SectionNotFoundError,
    SectionProtectedError,
)
from app.core.sections.schemas import (
    SectionCreateSchema,
    SectionResponseSchema,
    SectionUpdateSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sections", tags=["Sections"])


@router.get("/", response_model=ApiResponse[PaginatedResponse[SectionResponseSchema]])
async def get_sections(
    current_session: CurrentUser,
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, gt=0, le=1000),   # ✅ защита от ZeroDivisionError
    search: str | None = None,
    target_tenant_id: uuid.UUID | None = None,
) -> ApiResponse[PaginatedResponse[SectionResponseSchema]]:
    """Список разделов, видимых пользователю."""
    items, total = await crud_section.list_for_user(
        db,
        tenant_id=current_session.tenant_id,
        is_superadmin=bool(current_session.is_superadmin),
        target_tenant_id=target_tenant_id,
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
            user_id=current_session.id,
            is_admin=bool(current_session.is_admin),
            is_superadmin=bool(current_session.is_superadmin),
        )

        # ✅ Аудит создания — в той же транзакции, через сервис
        await audit_service.log_data_create(
            db,
            tenant_id=section.tenant_id or current_session.tenant_id,
            user_id=current_session.id,
            entity_type="section",
            entity_id=section.id,
            entity_name=section.name,
            changes=obj_in.model_dump(mode="json"),
        )


        await db.commit()
        await db.refresh(section)
    except SectionNotAdminError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка создания раздела: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка создания раздела",
        ) from exc

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
        is_superadmin=bool(current_session.is_superadmin),
    )

    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Раздел не найден")

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
    # ✅ old_values собираем ДО crud.update_custom — иначе diff будет old == new
    section_before = await crud_section.get_for_user(
        db,
        section_id=section_id,
        tenant_id=current_session.tenant_id,
        is_superadmin=bool(current_session.is_superadmin),
    )
    old_values: dict[str, uuid.UUID | str | None] = {}
    if section_before:
        dump = obj_in.model_dump(exclude_unset=True)
        for field in SectionUpdateSchema.model_fields:
            if field in dump:
                old_values[field] = getattr(section_before, field, None)

    try:
        section = await crud_section.update_custom(
            db,
            section_id=section_id,
            obj_in=obj_in,
            tenant_id=current_session.tenant_id,
            user_id=current_session.id,
            is_admin=bool(current_session.is_admin),
            is_superadmin=bool(current_session.is_superadmin),
        )

        # ✅ Аудит обновления — в той же транзакции, через сервис
        await audit_service.log_data_update(
            db,
            tenant_id=section.tenant_id or current_session.tenant_id,
            user_id=current_session.id,
            entity_type="section",
            entity_id=section.id,
            entity_name=section.name,
            old_values=old_values,
            new_values=obj_in.model_dump(exclude_unset=True),
        )


        await db.commit()
        await db.refresh(section)
    except SectionNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SectionProtectedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SectionNotAdminError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка обновления раздела %s: %s", section_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка обновления раздела",
        ) from exc

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
            user_id=current_session.id,
            is_admin=bool(current_session.is_admin),
            is_superadmin=bool(current_session.is_superadmin),
        )

        # ✅ Аудит удаления — в той же транзакции, через сервис
        await audit_service.log_data_delete(
            db,
            tenant_id=section.tenant_id or current_session.tenant_id,
            user_id=current_session.id,
            entity_type="section",
            entity_id=section.id,
            entity_name=section.name,
        )


        await db.commit()
    except SectionNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SectionProtectedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SectionNotAdminError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SectionHasDocumentsError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка удаления раздела %s: %s", section_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка удаления раздела",
        ) from exc

    return ApiResponse(
        success=True,
        message="Раздел удалён",
        data=SectionResponseSchema.model_validate(section),
    )