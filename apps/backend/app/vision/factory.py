from pathlib import Path
from typing import cast

import cv2
from pydantic import TypeAdapter

from app.db.models.shelf_configuration import ShelfConfiguration
from app.schemas.shelf_configuration import OpenCVROIConfiguration
from app.vision.detector import ImageArray, StockDetector
from app.vision.models import RegionOfInterest
from app.vision.opencv_roi import OpenCVROIDetector


class UnsupportedDetectorError(Exception):
    pass


class ReferenceImageNotFoundError(Exception):
    pass


class InvalidReferenceImageError(Exception):
    pass


class StockDetectorFactory:
    def create(
        self,
        configuration: ShelfConfiguration,
    ) -> StockDetector:
        if configuration.detector_type == "opencv_roi":
            return self._create_opencv_roi_detector(configuration)

        raise UnsupportedDetectorError(f"Unsupported detector type: {configuration.detector_type}")

    def _create_opencv_roi_detector(
        self,
        configuration: ShelfConfiguration,
    ) -> OpenCVROIDetector:
        if configuration.reference_image_path is None:
            raise ReferenceImageNotFoundError("Reference image path is not configured.")

        reference_path = Path(configuration.reference_image_path)

        if not reference_path.is_file():
            raise ReferenceImageNotFoundError(f"Reference image not found: {reference_path}")

        reference_image_raw = cv2.imread(
            str(reference_path),
            cv2.IMREAD_COLOR,
        )

        if reference_image_raw is None:
            raise InvalidReferenceImageError(f"Unable to read reference image: {reference_path}")

        reference_image = cast(
            ImageArray,
            reference_image_raw,
        )

        config = TypeAdapter(OpenCVROIConfiguration).validate_python(configuration.detector_config)

        regions = [
            RegionOfInterest(
                x=region.x,
                y=region.y,
                width=region.width,
                height=region.height,
            )
            for region in config.regions
        ]

        return OpenCVROIDetector(
            empty_reference=reference_image,
            regions=regions,
            difference_threshold=config.difference_threshold,
        )
