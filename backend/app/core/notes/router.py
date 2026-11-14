"""backend/app/core/notes/router.py"""
import logging
import uuid
from datetime import date
from typing import cast as typing_cast

from fastapi import APIRouter, HTTPException, Query, status

from app.core.access.schemas import UserProtocol
from app.core.audit import service as audit_service
from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.notes.crud import crud_note
from app.core.notes.exceptions import (
    NoteAccessDeniedError,
    NoteEditingLockedError,
    NoteNotFoundError,
    NotePermissionError,
    NoteVersionConflictError,
    SectionNotInTenantError,
)
from app.core.notes.schemas import (
    NoteCreateSchema,
    NoteResponseSchema,
    NoteUpdateSchema,
    NoteSortField,
)
from app.core.schemas import SortOrder, ApiResponse, PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[NoteResponseSchema]],
)
async def get_notes(
    current_session: CurrentUser,
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(15, gt=0, le=1000),   # ✅ защита от ZeroDivisionError
    search: str | None = None,
    sort_by: NoteSortField | None = None,
    sort_order: SortOrder = SortOrder.ASC,
    filter_title: str | None = None,
    filter_doc_number: str | None = None,
    filter_doc_date: date | None = None,
    filter_doc_status: str | None = None,
    filter_section_name: str | None = None,
    filter_updated_at: date | None = None,
) -> ApiResponse[PaginatedResponse[NoteResponseSchema]]:
    """Список заметок с контролем доступа, сортировкой и фильтрацией."""
    items, total = await crud_note.get_multi(
        db,
        user=typing_cast(UserProtocol, current_session),
        tenant_id=current_session.tenant_id,
        is_superadmin=bool(current_session.is_superadmin),
        skip=skip,
        limit=limit,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        filter_title=filter_title,
        filter_doc_number=filter_doc_number,
        filter_doc_date=filter_doc_date,
        filter_doc_status=filter_doc_status,
        filter_section_name=filter_section_name,
        filter_updated_at=filter_updated_at,
    )
    paginated = PaginatedResponse[NoteResponseSchema](
        items=[NoteResponseSchema.model_validate(item) for item in items],
        total=total,
        page=(skip // limit) + 1,
        size=limit,
    )
    return ApiResponse(
        success=True,
        message="Заметки получены",
        data=paginated,
    )


@router.get("/{note_id}", response_model=ApiResponse[NoteResponseSchema])
async def get_note(
    note_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[NoteResponseSchema]:
    """Одна заметка с проверкой доступа через AccessService."""
    note = await crud_note.get_for_user(
        db,
        note_id=note_id,
        user=typing_cast(UserProtocol, current_session),
        tenant_id=current_session.tenant_id,
        is_superadmin=bool(current_session.is_superadmin),
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заметка не найдена")
    return ApiResponse(
        success=True,
        message="Заметка получена",
        data=NoteResponseSchema.model_validate(note),
    )


@router.post("/", response_model=ApiResponse[NoteResponseSchema], status_code=status.HTTP_201_CREATED)
async def create_note(
    obj_in: NoteCreateSchema,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[NoteResponseSchema]:
    """Создание заметки."""
    try:
        note = await crud_note.create_for_user(
            db,
            obj_in=obj_in,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            is_superadmin=bool(current_session.is_superadmin),
        )

        # ✅ Аудит создания — в той же транзакции, через сервис
        await audit_service.log_data_create(
            db,
            tenant_id=note.tenant_id,
            user_id=current_session.id,
            entity_type="note",
            entity_id=note.id,
            entity_name=note.title,
            changes=obj_in.model_dump(mode="json"),
        )
 

        await db.commit()
        await db.refresh(note)
    except SectionNotInTenantError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except NotePermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка создания заметки: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка создания заметки",
        ) from exc

    return ApiResponse(
        success=True,
        message="Заметка создана",
        data=NoteResponseSchema.model_validate(note),
    )


@router.put("/{note_id}", response_model=ApiResponse[NoteResponseSchema])
async def update_note(
    note_id: uuid.UUID,
    obj_in: NoteUpdateSchema,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[NoteResponseSchema]:
    """Сохранение с проверкой доступа, версии и блокировки."""
    # ✅ old_values собираем ДО crud.save_with_version — иначе diff будет old == new
    note_before = await crud_note.get(db, id=note_id)
    old_values: dict[str, uuid.UUID | str | None] = {}
    if note_before is not None:
        dump = obj_in.model_dump(exclude_unset=True)
        for field in NoteUpdateSchema.model_fields:
            if field in dump:
                old_values[field] = getattr(note_before, field, None)

    try:
        note = await crud_note.save_with_version(
            db,
            note_id=note_id,
            obj_in=obj_in,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            user_id=current_session.id,
            is_superadmin=bool(current_session.is_superadmin),
        )

        # ✅ Аудит обновления — в той же транзакции, через сервис
        await audit_service.log_data_update(
            db,
            tenant_id=note.tenant_id,
            user_id=current_session.id,
            entity_type="note",
            entity_id=note.id,
            entity_name=note.title,
            old_values=old_values,
            new_values=obj_in.model_dump(exclude_unset=True),
        )


        await db.commit()
        await db.refresh(note)
    except NoteNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NoteVersionConflictError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except NoteEditingLockedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except NoteAccessDeniedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotePermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SectionNotInTenantError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка обновления заметки %s: %s", note_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка обновления заметки",
        ) from exc

    return ApiResponse(
        success=True,
        message="Заметка сохранена",
        data=NoteResponseSchema.model_validate(note),
    )


@router.delete("/{note_id}", response_model=ApiResponse[NoteResponseSchema])
async def delete_note(
    note_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[NoteResponseSchema]:
    """Мягкое удаление с проверкой can_delete через AccessService."""
    try:
        note = await crud_note.mark_deleted(
            db,
            note_id=note_id,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            user_id=current_session.id,
            is_superadmin=bool(current_session.is_superadmin),
        )

        # ✅ Аудит удаления — в той же транзакции, через сервис
        await audit_service.log_data_delete(
            db,
            tenant_id=note.tenant_id,
            user_id=current_session.id,
            entity_type="note",
            entity_id=note.id,
            entity_name=note.title,
        )


        await db.commit()
    except NoteNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NoteEditingLockedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except NoteAccessDeniedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка удаления заметки %s: %s", note_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка удаления заметки",
        ) from exc

    return ApiResponse(
        success=True,
        message="Заметка удалена",
        data=NoteResponseSchema.model_validate(note),
    )


@router.post("/{note_id}/lock", response_model=ApiResponse[NoteResponseSchema])
async def acquire_note_lock(
    note_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[NoteResponseSchema]:
    """Захват пессимистической блокировки."""
    try:
        note = await crud_note.acquire_editing_lock(
            db,
            note_id=note_id,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            user_id=current_session.id,
            is_superadmin=bool(current_session.is_superadmin),
        )


        await db.commit()
        await db.refresh(note)
    except NoteNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NoteEditingLockedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except NoteAccessDeniedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotePermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка захвата блокировки заметки %s: %s", note_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка захвата блокировки",
        ) from exc

    return ApiResponse(
        success=True,
        message="Блокировка захвачена",
        data=NoteResponseSchema.model_validate(note),
    )


@router.delete("/{note_id}/lock", response_model=ApiResponse[NoteResponseSchema])
async def release_note_lock(
    note_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[NoteResponseSchema]:
    """Освобождение пессимистической блокировки."""
    try:
        note = await crud_note.release_editing_lock(
            db,
            note_id=note_id,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            user_id=current_session.id,
            is_superadmin=bool(current_session.is_superadmin),
        )


        await db.commit()
        await db.refresh(note)
    except NoteNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NoteEditingLockedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка освобождения блокировки заметки %s: %s", note_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка освобождения блокировки",
        ) from exc

    return ApiResponse(
        success=True,
        message="Блокировка освобождена",
        data=NoteResponseSchema.model_validate(note),
    )