import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DoctypeBaseSchema(BaseModel):
    doctype: str
    doctype_name: str
    description: Optional[str] = None
    is_active: bool = True


class DoctypeCreateSchema(DoctypeBaseSchema):
    pass


class DoctypeUpdateSchema(BaseModel):
    doctype_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DoctypeResponseSchema(DoctypeBaseSchema):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID