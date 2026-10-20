import uuid
from typing import cast

from fastapi import APIRouter, HTTPException

from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.notes.crud import crud_note
from app.core.notes.exceptions import (
    NoteEditingLockedError,
    NoteNotFoundError,
    NoteVersionConflictError,
    SectionNotInTenantError,
)
from app.core.notes.schemas import (
    NoteCreateSchema,
    NoteResponseSchema,
    NoteUpdateSchema,
)
from app.core.schemas import ApiResponse, PaginatedResponse
# from app.core.users.models import UserModel

from app.core.access import get_access_service
from app.core.access.schemas import UserProtocol

router = APIRouter(prefix="/notes", tags=["Notes"])


# @router.get("/", response_model=ApiResponse[PaginatedResponse[NoteResponseSchema]])
# async def get_notes(
#     current_session: CurrentUser,
#     db: DBSession,
#     skip: int = 0,
#     limit: int = 10,
#     search: str | None = None,
#     target_tenant_id: uuid.UUID | None = None,
# ) -> ApiResponse[PaginatedResponse[NoteResponseSchema]]:
#     """Список заметок. Суперадмин может указать организацию."""
#     # user: UserModel = cast(UserModel, current_session)
    
#     items, total = await crud_note.list_for_user(
#         db,
#         tenant_id=current_session.tenant_id,
#         is_superadmin=current_session.is_superadmin,
#         target_tenant_id=target_tenant_id,
#         skip=skip,
#         limit=limit,
#         search=search,
#     )
#     paginated = PaginatedResponse[NoteResponseSchema](
#         items=[NoteResponseSchema.model_validate(item) for item in items],
#         total=total,
#         page=(skip // limit) + 1,
#         size=limit,
#     )
#     return ApiResponse(success=True, message="Заметки получены", data=paginated)

@router.get("/", response_model=ApiResponse[PaginatedResponse[NoteResponseSchema]])
async def get_notes(
    current_session: CurrentUser,
    db: DBSession,
    skip: int = 0,
    limit: int = 15,
    search: str | None = None,
) -> ApiResponse[PaginatedResponse[NoteResponseSchema]]:
    """Список заметок с фильтрацией через AccessService."""
    items, total = await crud_note.list_for_user(
        db,
        user=cast(UserProtocol, current_session),  # ✅ Передаём весь объект пользователя
        skip=skip,
        limit=limit,
        search=search,
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

@router.post("/", response_model=ApiResponse[NoteResponseSchema], status_code=201)
async def create_note(
    obj_in: NoteCreateSchema,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[NoteResponseSchema]:
    """Создание заметки."""
    user: UserProtocol = cast(UserProtocol, current_session)
    
    try:
        note = await crud_note.create_for_user(
            db,
            obj_in=obj_in,
            tenant_id=user.tenant_id,
            author_id=user.id,
        )
    except SectionNotInTenantError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(note)  # ✅ Защита от expire_on_commit=True

    return ApiResponse(
        success=True,
        message="Заметка создана",
        data=NoteResponseSchema.model_validate(note),
    )


@router.get("/{note_id}", response_model=ApiResponse[NoteResponseSchema])
async def get_note(
    note_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[NoteResponseSchema]:
    """Одна заметка."""
    user: UserProtocol = cast(UserProtocol, current_session)
    
    note = await crud_note.get_for_user(
        db,
        note_id=note_id,
        tenant_id=user.tenant_id,
        is_superadmin=current_session.is_superadmin,
    )

    if note is None:
        raise HTTPException(status_code=404, detail="Заметка не найдена")

    return ApiResponse(
        success=True,
        message="Заметка получена",
        data=NoteResponseSchema.model_validate(note),
    )


@router.get("/{note_id}/access-check")
async def check_access( # type: ignore
    note_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
):
    """
    Временный тестовый эндпоинт для проверки работы AccessService.
    
    Возвращает детальный результат вычисления доступа для конкретного документа.
    Используется для отладки и валидации алгоритма resolve_access.
    """
    # Загружаем документ без фильтрации (прямой доступ для диагностики)
    from sqlalchemy import select
    from app.core.notes.models import NotesModel
    
    stmt = select(NotesModel).where(
        NotesModel.id == note_id,
        NotesModel.deleted_at.is_(None),
    )
    note = (await db.execute(stmt)).scalar_one_or_none()
    
    if note is None:
        raise HTTPException(status_code=404, detail="Заметка не найдена")
    
    # Вычисляем доступ через AccessService
    access_service = get_access_service(db)
    result = await access_service.resolve_access(current_session, note) # type: ignore
    
    return {
        "note_id": str(note.id),
        "note_title": note.title,
        "note_tenant_id": str(note.tenant_id),
        "note_section_id": str(note.section_id),
        "note_or_tags": note.or_tags,
        "note_and_tags": note.and_tags,
        "user_id": str(current_session.user.id),
        "user_tenant_id": str(current_session.tenant_id),
        "user_is_superadmin": current_session.is_superadmin,
        "user_tags": current_session.user.tags,
        "user_role_ids": current_session.user.role_ids,
        "access_result": result.model_dump(),
    } # type: ignore

@router.put("/{note_id}", response_model=ApiResponse[NoteResponseSchema])
async def update_note(
    note_id: uuid.UUID,
    obj_in: NoteUpdateSchema,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[NoteResponseSchema]:
    """Сохранение с проверкой версии (409 при конфликте)."""
    user: UserProtocol = cast(UserProtocol, current_session)
    
    try:
        note = await crud_note.save_with_version(
            db,
            note_id=note_id,
            obj_in=obj_in,
            tenant_id=user.tenant_id,
            user_id=user.id,
            is_superadmin=current_session.is_superadmin,
        )
    except NoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoteVersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except NoteEditingLockedError as exc:  # ✅ НОВОЕ
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    except SectionNotInTenantError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(note)

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
    """Мягкое удаление (deleted_at), запись остаётся в БД."""
    user: UserProtocol = cast(UserProtocol, current_session)
    
    try:
        note = await crud_note.mark_deleted(
            db,
            note_id=note_id,
            tenant_id=user.tenant_id,
            user_id=user.id,
            is_superadmin=current_session.is_superadmin,
        )
    except NoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoteEditingLockedError as exc:  # ✅ НОВОЕ
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(note)

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
    """Захват блокировки редактирования."""
    user: UserProtocol = cast(UserProtocol, current_session)
    
    try:
        note = await crud_note.acquire_editing_lock(
            db,
            note_id=note_id,
            tenant_id=user.tenant_id,
            user_id=user.id,
            is_superadmin=current_session.is_superadmin,
        )
    except NoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoteEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(note)

    return ApiResponse(
        success=True,
        message="Блокировка установлена",
        data=NoteResponseSchema.model_validate(note),
    )


@router.delete("/{note_id}/lock", response_model=ApiResponse[NoteResponseSchema])
async def release_note_lock(
    note_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[NoteResponseSchema]:
    """Освобождение блокировки редактирования."""
    user: UserProtocol = cast(UserProtocol, current_session)
    
    try:
        note = await crud_note.release_editing_lock(
            db,
            note_id=note_id,
            tenant_id=user.tenant_id,
            user_id=user.id,
            is_superadmin=current_session.is_superadmin,
        )
    except NoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoteEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(note)

    return ApiResponse(
        success=True,
        message="Блокировка снята",
        data=NoteResponseSchema.model_validate(note),
    )