import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CameraCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    source_type: Literal["file"] = "file"
    source_uri: str | None = Field(
        default=None,
        min_length=1,
        max_length=1000,
    )


class CameraUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    location: str | None = Field(
        default=None,
        max_length=255,
    )
    source_type: Literal["file"] | None = None
    source_uri: str | None = Field(
        default=None,
        min_length=1,
        max_length=1000,
    )
    is_active: bool | None = None


class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    location: str | None
    source_type: str
    source_uri: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
