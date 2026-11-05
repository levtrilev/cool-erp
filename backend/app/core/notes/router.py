import logging
import uuid
from datetime import date
from typing import cast as typing_cast

from fastapi import APIRouter, HTTPException, status

from app.core.access.schemas import UserProtocol
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
    SortOrder,
)
from app.core.audit.utils import get_entity_name
from app.core.schemas import ApiResponse, PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[NoteResponseSchema]],
)
async def get_notes(
    current_session: CurrentUser,
    db: DBSession,
    skip: int = 0,
    limit: int = 15,
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
        is_superadmin=current_session.is_superadmin,
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
        is_superadmin=current_session.is_superadmin,
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
            is_superadmin=current_session.is_superadmin,
        )
    except SectionNotInTenantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except NotePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(note)

    # ✅ ЗАПИСЬ В АУДИТ: создание заметки
    try:
        from app.core.audit.models import DataAuditLog

        audit_log = DataAuditLog(
            id=uuid.uuid4(),
            tenant_id=current_session.tenant_id,
            user_id=current_session.id,
            entity_type="note",
            entity_id=note.id,
            entity_name=note.title,
            action="create",
            changes=None,
        )
        db.add(audit_log)
        await db.commit()
    except Exception as e:
        logger.warning(f"Could not write data audit: {e}")

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
    try:
        # ✅ Сохраняем текущие значения полей перед обновлением
        note_before = await crud_note.get(db, id=note_id)
        old_values = {}
        if note_before:
            for field in NoteUpdateSchema.model_fields:
                if field in obj_in.model_dump(exclude_unset=True):
                    old_values[field] = getattr(note_before, field, None)

        note = await crud_note.save_with_version(
            db,
            note_id=note_id,
            obj_in=obj_in,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            user_id=typing_cast(UserProtocol, current_session).id,
            is_superadmin=current_session.is_superadmin,
        )
    except NoteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NoteVersionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except NoteEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except NoteAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SectionNotInTenantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(note)

    # ✅ ЗАПИСЬ В АУДИТ: обновление заметки
    try:
        from app.core.audit.models import DataAuditLog

        # Формируем словарь изменений
        changes = {}
        dump = obj_in.model_dump(exclude_unset=True)
        for field, new_value in dump.items():
            if field in old_values and old_values[field] != new_value:
                if field.endswith('_id'):
                    old_name = await get_entity_name(db, field[:-3], old_values[field])
                    new_name = await get_entity_name(db, field[:-3], new_value)
                    changes[field] = {
                        "old": old_name if old_name else str(old_values[field]),
                        "new": new_name if new_name else str(new_value)
                    }
                else:
                    changes[field] = {"old": str(old_values[field]), "new": str(new_value)}

        if changes:
            audit_log = DataAuditLog(
                id=uuid.uuid4(),
                tenant_id=current_session.tenant_id,
                user_id=current_session.id,
                entity_type="note",
                entity_id=note.id,
                entity_name=note.title,
                action="update",
                changes=changes if changes else None,
            )
            db.add(audit_log)
            await db.commit()
    except Exception as e:
        logger.warning(f"Could not write data audit: {e}")

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
            user_id=typing_cast(UserProtocol, current_session).id,
            is_superadmin=current_session.is_superadmin,
        )
    except NoteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NoteEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except NoteAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    await db.commit()

    # ✅ ЗАПИСЬ В АУДИТ: удаление заметки
    try:
        from app.core.audit.models import DataAuditLog

        audit_log = DataAuditLog(
            id=uuid.uuid4(),
            tenant_id=current_session.tenant_id,
            user_id=current_session.id,
            entity_type="note",
            entity_id=note.id,
            entity_name=note.title,
            action="delete",
            changes={"deleted": True},
        )
        db.add(audit_log)
        await db.commit()
    except Exception as e:
        logger.warning(f"Could not write data audit: {e}")

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
            user_id=typing_cast(UserProtocol, current_session).id,
            is_superadmin=current_session.is_superadmin,
        )
    except NoteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NoteEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except NoteAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(note)
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
            user_id=typing_cast(UserProtocol, current_session).id,
            is_superadmin=current_session.is_superadmin,
        )
    except NoteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NoteEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(note)
    return ApiResponse(
        success=True,
        message="Блокировка освобождена",
        data=NoteResponseSchema.model_validate(note),
    )