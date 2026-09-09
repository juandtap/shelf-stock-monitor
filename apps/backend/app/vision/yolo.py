from collections.abc import Sequence
from typing import Protocol, cast

import numpy as np
from ultralytics import YOLO  # type: ignore[attr-defined]

from app.vision.detector import ImageArray
from app.vision.models import StockDetectionResult


class YOLOBoxes(Protocol):
    @property
    def cls(self) -> object: ...


class YOLOResult(Protocol):
    @property
    def boxes(self) -> YOLOBoxes | None: ...


class YOLOModel(Protocol):
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
    ) -> Sequence[YOLOResult]: ...


class YOLOStockDetector:
    def __init__(
        self,
        *,
        model_path: str,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.7,
        image_size: int = 640,
        class_ids: list[int] | None = None,
        device: str | None = None,
        model: YOLOModel | None = None,
    ) -> None:
        if not model_path:
            raise ValueError(
                "model_path cannot be empty.",
            )

        if not 0 <= confidence_threshold <= 1:
            raise ValueError(
                "confidence_threshold must be between 0 and 1.",
            )

        if not 0 <= iou_threshold <= 1:
            raise ValueError(
                "iou_threshold must be between 0 and 1.",
            )

        if image_size <= 0:
            raise ValueError(
                "image_size must be positive.",
            )

        if class_ids is not None:
            if not class_ids:
                raise ValueError(
                    "class_ids cannot be empty when provided.",
                )

            if any(class_id < 0 for class_id in class_ids):
                raise ValueError(
                    "class_ids cannot contain negative values.",
                )

        self._model_path = model_path
        self._confidence_threshold = confidence_threshold
        self._iou_threshold = iou_threshold
        self._image_size = image_size
        self._class_ids = class_ids
        self._device = device

        self._model = (
            model
            if model is not None
            else cast(
                YOLOModel,
                YOLO(model_path),
            )
        )

    @property
    def name(self) -> str:
        return "yolo"

    def detect(
        self,
        image: ImageArray,
    ) -> StockDetectionResult:
        self._validate_image(image)

        results = self._model.predict(
            source=image,
            conf=self._confidence_threshold,
            iou=self._iou_threshold,
            imgsz=self._image_size,
            classes=self._class_ids,
            device=self._device,
            verbose=False,
        )

        detected_units = self._count_detections(
            results,
        )

        return StockDetectionResult(
            detected_units=detected_units,
            detector_name=self.name,
        )

    @staticmethod
    def _validate_image(
        image: ImageArray,
    ) -> None:
        if image.size == 0:
            raise ValueError(
                "Image cannot be empty.",
            )

        if image.ndim not in (2, 3):
            raise ValueError(
                "Image must be grayscale or a multi-channel image.",
            )

    @staticmethod
    def _count_detections(
        results: Sequence[YOLOResult],
    ) -> int:
        detected_units = 0

        for result in results:
            boxes = result.boxes

            if boxes is None:
                continue

            classes = boxes.cls

            if hasattr(classes, "cpu"):
                classes = classes.cpu()

            if hasattr(classes, "numpy"):
                classes = classes.numpy()

            class_array = np.asarray(
                classes,
            )

            detected_units += int(
                class_array.size,
            )

        return detected_units
