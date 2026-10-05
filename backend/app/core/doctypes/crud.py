import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.doctypes.models import DoctypeModel
from app.core.doctypes.schemas import DoctypeCreateSchema, DoctypeUpdateSchema


class DoctypeCRUD:
    """CRUD operations for document types (doctypes). Global entity (no tenant_id)."""

    def __init__(self, model: type[DoctypeModel]):
        self.model = model

    async def get(self, db: AsyncSession, id: uuid.UUID) -> DoctypeModel | None:
        """Get document type by ID."""
        stmt = select(self.model).where(self.model.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_doctype(
        self, db: AsyncSession, doctype: str
    ) -> DoctypeModel | None:
        """Get document type by system name (for uniqueness check)."""
        stmt = select(self.model).where(self.model.doctype == doctype)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        active_only: bool = True,
    ) -> list[DoctypeModel]:
        """Get list of document types with optional search."""
        stmt = select(self.model)

        if active_only:
            stmt = stmt.where(self.model.is_active.is_(True))

        if search:
            search_filter = self.model.doctype_name.ilike(f"%{search}%") | self.model.doctype.ilike(f"%{search}%")
            stmt = stmt.where(search_filter)

        stmt = stmt.offset(skip).limit(limit).order_by(self.model.doctype_name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        active_only: bool = True,
    ) -> tuple[list[DoctypeModel], int]:
        """
        Get paginated list of document types.
        Returns tuple: (list of objects, total count).
        """
        # 1. Count total records
        count_stmt = select(func.count()).select_from(self.model)

        if active_only:
            count_stmt = count_stmt.where(self.model.is_active.is_(True))

        if search:
            search_filter = self.model.doctype_name.ilike(f"%{search}%") | self.model.doctype.ilike(f"%{search}%")
            count_stmt = count_stmt.where(search_filter)

        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # 2. Get actual records
        items = await self.get_multi(db, skip, limit, search, active_only)

        return items, total

    async def create(self, db: AsyncSession, obj_in: DoctypeCreateSchema) -> DoctypeModel:
        """
        Create new document type.
        Checks uniqueness of system name (doctype).
        """
        # Check uniqueness of system name
        existing = await self.get_by_doctype(db, obj_in.doctype)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Document type with this system name already exists"
            )

        db_obj = self.model(
            doctype=obj_in.doctype,
            doctype_name=obj_in.doctype_name,
            description=obj_in.description,
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: DoctypeModel,
        obj_in: DoctypeUpdateSchema | dict[str, Any],
    ) -> DoctypeModel:
        """Update existing document type."""
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        # If system name is changed, check uniqueness
        if "doctype" in update_data and update_data["doctype"] != db_obj.doctype:
            existing = await self.get_by_doctype(db, update_data["doctype"])
            # If found another object with same name
            if existing and existing.id != db_obj.id:
                raise HTTPException(
                    status_code=400,
                    detail="Document type with this system name already exists"
                )

        for field, value in update_data.items():
            # Use 'is not None' to correctly handle False, 0, ""
            if value is not None:
                setattr(db_obj, field, value)

        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, id: uuid.UUID) -> DoctypeModel | None:
        """
        Delete document type.
        Uses get() to check existence.
        """
        obj = await self.get(db, id)
        if not obj:
            return None

        await db.delete(obj)
        await db.flush()
        return obj


# CRUD instance for use in routers
crud_doctype = DoctypeCRUD(DoctypeModel)
