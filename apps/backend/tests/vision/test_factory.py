from pathlib import Path

import cv2
import numpy as np
import pytest

from app.db.models.shelf_configuration import ShelfConfiguration
from app.vision.factory import (
    ReferenceImageNotFoundError,
    StockDetectorFactory,
)
from app.vision.opencv_roi import OpenCVROIDetector


def create_configuration(
    reference_image_path: str,
) -> ShelfConfiguration:
    return ShelfConfiguration(
        detector_type="opencv_roi",
        reference_image_path=reference_image_path,
        detector_config={
            "difference_threshold": 30.0,
            "regions": [
                {
                    "x": 0,
                    "y": 0,
                    "width": 50,
                    "height": 50,
                },
                {
                    "x": 50,
                    "y": 0,
                    "width": 50,
                    "height": 50,
                },
            ],
        },
    )


def test_factory_creates_opencv_roi_detector(
    tmp_path: Path,
) -> None:
    reference_image = np.zeros(
        (50, 100, 3),
        dtype=np.uint8,
    )

    reference_path = tmp_path / "reference.jpg"

    saved = cv2.imwrite(
        str(reference_path),
        reference_image,
    )

    assert saved is True

    configuration = create_configuration(
        str(reference_path),
    )

    factory = StockDetectorFactory()

    detector = factory.create(configuration)

    assert isinstance(detector, OpenCVROIDetector)
    assert detector.name == "opencv_roi"


def test_factory_rejects_missing_reference_image() -> None:
    configuration = create_configuration(
        "/path/that/does/not/exist.jpg",
    )

    factory = StockDetectorFactory()

    with pytest.raises(
        ReferenceImageNotFoundError,
    ):
        factory.create(configuration)
