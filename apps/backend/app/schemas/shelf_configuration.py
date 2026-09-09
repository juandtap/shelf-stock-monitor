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

    regions: list[ROIConfiguration] = Field(
        min_length=1,
    )


class YOLOConfiguration(BaseModel):
    model_path: str = Field(
        min_length=1,
        max_length=500,
    )

    confidence_threshold: float = Field(
        default=0.5,
        ge=0,
        le=1,
    )

    iou_threshold: float = Field(
        default=0.7,
        ge=0,
        le=1,
    )

    image_size: int = Field(
        default=640,
        gt=0,
    )

    class_ids: list[int] | None = None

    device: str | None = Field(
        default=None,
        max_length=50,
    )

    @model_validator(mode="after")
    def validate_class_ids(
        self,
    ) -> "YOLOConfiguration":
        if self.class_ids is not None:
            if not self.class_ids:
                raise ValueError(
                    "class_ids cannot be empty when provided.",
                )

            if any(class_id < 0 for class_id in self.class_ids):
                raise ValueError(
                    "class_ids cannot contain negative values.",
                )

            if len(set(self.class_ids)) != len(self.class_ids):
                raise ValueError(
                    "class_ids cannot contain duplicates.",
                )

        return self


DetectorConfiguration = OpenCVROIConfiguration | YOLOConfiguration


class ShelfConfigurationCreate(BaseModel):
    camera_id: uuid.UUID
    product_id: uuid.UUID

    detector_type: Literal[
        "opencv_roi",
        "yolo",
    ]

    reference_image_path: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    detector_config: DetectorConfiguration

    shelf_capacity: int = Field(
        gt=0,
    )

    low_stock_threshold: float = Field(
        default=50.0,
        ge=0,
        le=100,
    )

    @model_validator(mode="after")
    def validate_detector_requirements(
        self,
    ) -> "ShelfConfigurationCreate":
        if self.detector_type == "opencv_roi":
            if not isinstance(
                self.detector_config,
                OpenCVROIConfiguration,
            ):
                raise ValueError(
                    "detector_config must use OpenCVROIConfiguration for opencv_roi.",
                )

            if self.reference_image_path is None:
                raise ValueError(
                    "reference_image_path is required for opencv_roi.",
                )

            region_count = len(self.detector_config.regions)

            if self.shelf_capacity != region_count:
                raise ValueError(
                    "shelf_capacity must match the number of configured regions for opencv_roi.",
                )

        if self.detector_type == "yolo":
            if not isinstance(
                self.detector_config,
                YOLOConfiguration,
            ):
                raise ValueError(
                    "detector_config must use YOLOConfiguration for yolo.",
                )

        return self


class ShelfConfigurationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    camera_id: uuid.UUID
    product_id: uuid.UUID

    detector_type: str
    reference_image_path: str | None
    detector_config: DetectorConfiguration

    shelf_capacity: int
    low_stock_threshold: float
    is_active: bool

    created_at: datetime
    updated_at: datetime
