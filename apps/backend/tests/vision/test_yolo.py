from collections.abc import Sequence

import numpy as np

from app.vision.detector import ImageArray
from app.vision.yolo import (
    YOLOBoxes,
    YOLOModel,
    YOLOResult,
    YOLOStockDetector,
)


class FakeBoxes:
    def __init__(
        self,
        classes: list[float],
    ) -> None:
        self._classes = np.asarray(
            classes,
            dtype=np.float32,
        )

    @property
    def cls(self) -> object:
        return self._classes


class FakeResult:
    def __init__(
        self,
        boxes: YOLOBoxes | None,
    ) -> None:
        self._boxes = boxes

    @property
    def boxes(self) -> YOLOBoxes | None:
        return self._boxes


class FakeYOLOModel:
    def __init__(
        self,
        results: Sequence[YOLOResult],
    ) -> None:
        self._results = results

        self.received_conf: float | None = None
        self.received_iou: float | None = None
        self.received_imgsz: int | None = None
        self.received_classes: list[int] | None = None
        self.received_device: str | None = None
        self.received_verbose: bool | None = None

    def predict(
        self,
        source: ImageArray,
        *,
        conf: float,
        iou: float,
        imgsz: int,
        classes: list[int] | None,
        device: str | None,
        verbose: bool,
    ) -> Sequence[YOLOResult]:
        self.received_conf = conf
        self.received_iou = iou
        self.received_imgsz = imgsz
        self.received_classes = classes
        self.received_device = device
        self.received_verbose = verbose

        return self._results


def create_image() -> ImageArray:
    return np.zeros(
        (100, 100, 3),
        dtype=np.uint8,
    )


def test_detect_counts_yolo_detections() -> None:
    model = FakeYOLOModel(
        results=[
            FakeResult(
                FakeBoxes(
                    [0.0, 0.0, 0.0],
                )
            )
        ]
    )

    detector = YOLOStockDetector(
        model_path="test-model.pt",
        model=model,
    )

    result = detector.detect(
        create_image(),
    )

    assert result.detected_units == 3
    assert result.detector_name == "yolo"


def test_detect_returns_zero_when_no_boxes_exist() -> None:
    model = FakeYOLOModel(
        results=[
            FakeResult(None),
        ]
    )

    detector = YOLOStockDetector(
        model_path="test-model.pt",
        model=model,
    )

    result = detector.detect(
        create_image(),
    )

    assert result.detected_units == 0


def test_detect_passes_configuration_to_model() -> None:
    model = FakeYOLOModel(
        results=[
            FakeResult(
                FakeBoxes(
                    [1.0],
                )
            )
        ]
    )

    detector = YOLOStockDetector(
        model_path="test-model.pt",
        confidence_threshold=0.65,
        iou_threshold=0.45,
        image_size=512,
        class_ids=[1, 2],
        device="cpu",
        model=model,
    )

    detector.detect(
        create_image(),
    )

    assert model.received_conf == 0.65
    assert model.received_iou == 0.45
    assert model.received_imgsz == 512
    assert model.received_classes == [1, 2]
    assert model.received_device == "cpu"
    assert model.received_verbose is False


def test_detect_counts_detections_across_results() -> None:
    model = FakeYOLOModel(
        results=[
            FakeResult(
                FakeBoxes(
                    [0.0, 0.0],
                )
            ),
            FakeResult(
                FakeBoxes(
                    [0.0],
                )
            ),
        ]
    )

    detector = YOLOStockDetector(
        model_path="test-model.pt",
        model=model,
    )

    result = detector.detect(
        create_image(),
    )

    assert result.detected_units == 3


def test_detect_rejects_empty_image() -> None:
    model = FakeYOLOModel(
        results=[],
    )

    detector = YOLOStockDetector(
        model_path="test-model.pt",
        model=model,
    )

    empty_image = np.zeros(
        (0, 0, 3),
        dtype=np.uint8,
    )

    try:
        detector.detect(
            empty_image,
        )
    except ValueError as error:
        assert str(error) == "Image cannot be empty."
    else:
        raise AssertionError(
            "Expected ValueError.",
        )


def test_detector_satisfies_yolo_model_protocol() -> None:
    model: YOLOModel = FakeYOLOModel(
        results=[],
    )

    detector = YOLOStockDetector(
        model_path="test-model.pt",
        model=model,
    )

    assert detector.name == "yolo"
