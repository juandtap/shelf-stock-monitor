import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StockObservationCreate(BaseModel):
    camera_id: uuid.UUID
    product_id: uuid.UUID

    detected_units: int = Field(ge=0)
    shelf_capacity: int = Field(gt=0)

    detector_name: str = Field(
        min_length=1,
        max_length=50,
    )

    @model_validator(mode="after")
    def validate_detected_units(self) -> "StockObservationCreate":
        if self.detected_units > self.shelf_capacity:
            raise ValueError("detected_units cannot exceed shelf_capacity")

        return self


class StockObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    camera_id: uuid.UUID
    product_id: uuid.UUID

    detected_units: int
    shelf_capacity: int
    stock_percentage: float
    detector_name: str

    captured_at: datetime
    created_at: datetime
    updated_at: datetime
