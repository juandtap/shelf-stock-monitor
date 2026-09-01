from pathlib import Path
from typing import cast

import cv2

from app.vision.detector import ImageArray
from app.vision.models import RegionOfInterest


class ROIVisualizer:
    @staticmethod
    def draw(
        *,
        image: ImageArray,
        regions: list[RegionOfInterest],
    ) -> ImageArray:
        output = image.copy()

        for index, region in enumerate(regions, start=1):
            top_left = (region.x, region.y)
            bottom_right = (
                region.x + region.width,
                region.y + region.height,
            )

            cv2.rectangle(
                output,
                top_left,
                bottom_right,
                (255, 255, 255),
                3,
            )

            cv2.putText(
                output,
                f"ROI {index}",
                (region.x + 10, region.y + 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        return output

    @staticmethod
    def load(image_path: str) -> ImageArray:
        path = Path(image_path)

        if not path.is_file():
            raise FileNotFoundError(f"Image not found: {path}")

        image_raw = cv2.imread(
            str(path),
            cv2.IMREAD_COLOR,
        )

        if image_raw is None:
            raise ValueError(f"Unable to read image: {path}")

        return cast(ImageArray, image_raw)

    @staticmethod
    def save(
        *,
        image: ImageArray,
        output_path: str,
    ) -> None:
        path = Path(output_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        saved = cv2.imwrite(
            str(path),
            image,
        )

        if not saved:
            raise RuntimeError(f"Unable to save image: {path}")
