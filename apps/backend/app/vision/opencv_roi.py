from typing import cast

import cv2
import numpy as np

from app.vision.detector import ImageArray
from app.vision.models import RegionOfInterest, StockDetectionResult


class OpenCVROIDetector:
    def __init__(
        self,
        *,
        empty_reference: ImageArray,
        regions: list[RegionOfInterest],
        difference_threshold: float,
    ) -> None:
        if not regions:
            raise ValueError("At least one ROI is required.")

        if difference_threshold < 0:
            raise ValueError("difference_threshold cannot be negative.")

        self._validate_image(empty_reference)

        self._empty_reference = empty_reference.copy()
        self._regions = regions
        self._difference_threshold = difference_threshold

        self._validate_regions()

    @property
    def name(self) -> str:
        return "opencv_roi"

    def detect(self, image: ImageArray) -> StockDetectionResult:
        scores = self.score_regions(image)

        occupied_slots = sum(score >= self._difference_threshold for score in scores)

        return StockDetectionResult(
            detected_units=occupied_slots,
            shelf_capacity=len(self._regions),
            detector_name=self.name,
        )

    def score_regions(
        self,
        image: ImageArray,
    ) -> list[float]:
        self._validate_image(image)

        if image.shape != self._empty_reference.shape:
            raise ValueError("Input image dimensions must match the empty reference image.")

        scores: list[float] = []

        for region in self._regions:
            current_roi = self._extract_roi(image, region)
            reference_roi = self._extract_roi(
                self._empty_reference,
                region,
            )

            score = self._calculate_difference_score(
                current_roi=current_roi,
                reference_roi=reference_roi,
            )

            scores.append(score)

        return scores

    def _validate_regions(self) -> None:
        image_height, image_width = self._empty_reference.shape[:2]

        for region in self._regions:
            if region.x + region.width > image_width:
                raise ValueError("ROI exceeds image width.")

            if region.y + region.height > image_height:
                raise ValueError("ROI exceeds image height.")

    @staticmethod
    def _validate_image(image: ImageArray) -> None:
        if image.size == 0:
            raise ValueError("Image cannot be empty.")

        if image.ndim not in (2, 3):
            raise ValueError("Image must be grayscale or a multi-channel image.")

    @staticmethod
    def _extract_roi(
        image: ImageArray,
        region: RegionOfInterest,
    ) -> ImageArray:
        return image[
            region.y : region.y + region.height,
            region.x : region.x + region.width,
        ]

    @staticmethod
    def _calculate_difference_score(
        *,
        current_roi: ImageArray,
        reference_roi: ImageArray,
    ) -> float:
        current_gray = OpenCVROIDetector._to_grayscale(current_roi)
        reference_gray = OpenCVROIDetector._to_grayscale(reference_roi)

        difference = cv2.absdiff(
            current_gray,
            reference_gray,
        )

        return float(np.mean(difference))

    @staticmethod
    def _to_grayscale(image: ImageArray) -> ImageArray:
        if image.ndim == 2:
            return image

        if image.shape[2] == 3:
            grayscale = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY,
            )
            return cast(ImageArray, grayscale)

        if image.shape[2] == 4:
            grayscale = cv2.cvtColor(
                image,
                cv2.COLOR_BGRA2GRAY,
            )
            return cast(ImageArray, grayscale)

        raise ValueError("Unsupported number of image channels.")
