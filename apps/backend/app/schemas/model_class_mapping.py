import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelClassMappingCreate(BaseModel):
    model_key: str = Field(
        min_length=1,
        max_length=150,
    )
    class_id: int = Field(ge=0)
    product_id: uuid.UUID


class ModelClassMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_key: str
    class_id: int
    product_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
