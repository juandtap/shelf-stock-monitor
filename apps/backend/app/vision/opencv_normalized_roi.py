from typing import cast

import cv2
import numpy as np

from app.vision.detector import ImageArray
from app.vision.models import RegionOfInterest, StockDetectionResult


class OpenCVNormalizedROIDetector:
    def __init__(
        self,
        *,
        empty_reference: ImageArray,
        regions: list[RegionOfInterest],
        difference_threshold: float,
    ) -> None:
        if not regions:
            raise ValueError(
                "At least one ROI is required.",
            )

        if difference_threshold < 0:
            raise ValueError(
                "difference_threshold cannot be negative.",
            )

        self._validate_image(
            empty_reference,
        )

        self._empty_reference = empty_reference.copy()
        self._regions = regions
        self._difference_threshold = difference_threshold

        self._validate_regions()

    @property
    def name(self) -> str:
        return "opencv_roi_normalized"

    def detect(
        self,
        image: ImageArray,
    ) -> StockDetectionResult:
        scores = self.score_regions(image)

        occupied_slots = sum(score >= self._difference_threshold for score in scores)

        return StockDetectionResult(
            detected_units=occupied_slots,
            detector_name=self.name,
        )

    def score_regions(
        self,
        image: ImageArray,
    ) -> list[float]:
        self._validate_image(image)

        if image.shape != self._empty_reference.shape:
            raise ValueError(
                "Input image dimensions must match the empty reference image.",
            )

        scores: list[float] = []

        for region in self._regions:
            current_roi = self._extract_roi(
                image,
                region,
            )

            reference_roi = self._extract_roi(
                self._empty_reference,
                region,
            )

            score = self._calculate_normalized_difference_score(
                current_roi=current_roi,
                reference_roi=reference_roi,
            )

            scores.append(score)

        return scores

    @classmethod
    def _calculate_normalized_difference_score(
        cls,
        *,
        current_roi: ImageArray,
        reference_roi: ImageArray,
    ) -> float:
        current_gray = cls._to_grayscale(
            current_roi,
        )

        reference_gray = cls._to_grayscale(
            reference_roi,
        )

        normalized_current = cls._normalize_roi(current_gray)

        normalized_reference = cls._normalize_roi(reference_gray)

        difference = cv2.absdiff(
            normalized_current,
            normalized_reference,
        )

        return float(np.mean(difference))

    def _validate_regions(self) -> None:
        image_height, image_width = self._empty_reference.shape[:2]

        for region in self._regions:
            if region.x + region.width > image_width:
                raise ValueError(
                    "ROI exceeds image width.",
                )

            if region.y + region.height > image_height:
                raise ValueError(
                    "ROI exceeds image height.",
                )

    @staticmethod
    def _normalize_roi(
        image: ImageArray,
    ) -> ImageArray:
        image_float = image.astype(np.float32)

        mean = float(np.mean(image_float))

        standard_deviation = float(np.std(image_float))

        if standard_deviation < 1e-6:
            return np.full(
                image.shape,
                127,
                dtype=np.uint8,
            )

        normalized = (image_float - mean) / standard_deviation

        normalized = normalized * 32.0 + 127.0

        normalized_uint8 = np.clip(
            normalized,
            0,
            255,
        ).astype(np.uint8)

        return cast(
            ImageArray,
            normalized_uint8,
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
    def _extract_roi(
        image: ImageArray,
        region: RegionOfInterest,
    ) -> ImageArray:
        return image[
            region.y : (region.y + region.height),
            region.x : (region.x + region.width),
        ]

    @staticmethod
    def _to_grayscale(
        image: ImageArray,
    ) -> ImageArray:
        if image.ndim == 2:
            return image

        if image.shape[2] == 3:
            grayscale = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY,
            )

            return cast(
                ImageArray,
                grayscale,
            )

        if image.shape[2] == 4:
            grayscale = cv2.cvtColor(
                image,
                cv2.COLOR_BGRA2GRAY,
            )

            return cast(
                ImageArray,
                grayscale,
            )

        raise ValueError(
            "Unsupported number of image channels.",
        )
