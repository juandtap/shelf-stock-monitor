import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ROIConfiguration(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class OpenCVROIConfiguration(BaseModel):
    difference_threshold: float = Field(ge=0)
    regions: list[ROIConfiguration] = Field(min_length=1)


class ShelfConfigurationCreate(BaseModel):
    camera_id: uuid.UUID
    product_id: uuid.UUID
    detector_type: Literal["opencv_roi"]
    reference_image_path: str = Field(
        min_length=1,
        max_length=500,
    )
    detector_config: OpenCVROIConfiguration

    @model_validator(mode="after")
    def validate_detector_requirements(
        self,
    ) -> "ShelfConfigurationCreate":
        if self.detector_type == "opencv_roi" and not self.reference_image_path:
            raise ValueError("reference_image_path is required for opencv_roi.")

        return self


class ShelfConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    camera_id: uuid.UUID
    product_id: uuid.UUID
    detector_type: str
    reference_image_path: str | None
    detector_config: OpenCVROIConfiguration
    is_active: bool
    created_at: datetime
    updated_at: datetime
