from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from app.db.models.shelf_configuration import ShelfConfiguration
from app.vision.factory import (
    ReferenceImageNotFoundError,
    StockDetectorFactory,
    UnsupportedDetectorError,
)
from app.vision.opencv_roi import OpenCVROIDetector

TEST_MODEL_KEY = "test-model"


def create_opencv_configuration(
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


def create_yolo_configuration() -> ShelfConfiguration:
    return ShelfConfiguration(
        detector_type="yolo",
        reference_image_path=None,
        detector_config={
            "model_key": TEST_MODEL_KEY,
            "model_path": "models/shelf-stock.pt",
            "confidence_threshold": 0.65,
            "iou_threshold": 0.45,
            "image_size": 512,
            "class_ids": [0, 1],
            "device": "cpu",
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

    configuration = create_opencv_configuration(
        str(reference_path),
    )

    factory = StockDetectorFactory()

    detector = factory.create(
        configuration,
    )

    assert isinstance(
        detector,
        OpenCVROIDetector,
    )
    assert detector.name == "opencv_roi"


def test_factory_rejects_missing_reference_image() -> None:
    configuration = create_opencv_configuration(
        "/path/that/does/not/exist.jpg",
    )

    factory = StockDetectorFactory()

    with pytest.raises(
        ReferenceImageNotFoundError,
    ):
        factory.create(
            configuration,
        )


def test_factory_creates_yolo_detector() -> None:
    configuration = create_yolo_configuration()

    fake_detector = MagicMock()
    fake_detector.name = "yolo"

    with patch(
        "app.vision.factory.YOLOStockDetector",
        return_value=fake_detector,
    ) as detector_class:
        factory = StockDetectorFactory()

        detector = factory.create(
            configuration,
        )

    detector_class.assert_called_once_with(
        model_path="models/shelf-stock.pt",
        confidence_threshold=0.65,
        iou_threshold=0.45,
        image_size=512,
        class_ids=[0, 1],
        device="cpu",
    )

    assert detector is fake_detector
    assert detector.name == "yolo"


def test_factory_creates_yolo_detector_with_defaults() -> None:
    configuration = ShelfConfiguration(
        detector_type="yolo",
        reference_image_path=None,
        detector_config={
            "model_key": TEST_MODEL_KEY,
            "model_path": "models/shelf-stock.pt",
        },
    )

    fake_detector = MagicMock()

    with patch(
        "app.vision.factory.YOLOStockDetector",
        return_value=fake_detector,
    ) as detector_class:
        factory = StockDetectorFactory()

        detector = factory.create(
            configuration,
        )

    detector_class.assert_called_once_with(
        model_path="models/shelf-stock.pt",
        confidence_threshold=0.5,
        iou_threshold=0.7,
        image_size=640,
        class_ids=None,
        device=None,
    )

    assert detector is fake_detector


def test_factory_rejects_unsupported_detector() -> None:
    configuration = ShelfConfiguration(
        detector_type="unsupported",
        reference_image_path=None,
        detector_config={},
    )

    factory = StockDetectorFactory()

    with pytest.raises(
        UnsupportedDetectorError,
        match="Unsupported detector type: unsupported",
    ):
        factory.create(
            configuration,
        )
