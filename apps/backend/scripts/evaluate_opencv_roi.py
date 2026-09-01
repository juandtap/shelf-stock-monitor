from pathlib import Path
from typing import cast

import cv2

from app.vision.detector import ImageArray
from app.vision.models import RegionOfInterest
from app.vision.opencv_roi import OpenCVROIDetector

REFERENCE_IMAGE = Path("../../data/references/shelf_01_empty.png")

SAMPLES_DIRECTORY = Path("../../data/samples")

DIFFERENCE_THRESHOLD = 20.0


def load_image(path: Path) -> ImageArray:
    image_raw = cv2.imread(
        str(path),
        cv2.IMREAD_COLOR,
    )

    if image_raw is None:
        raise RuntimeError(f"Unable to read image: {path}")

    return cast(ImageArray, image_raw)


def create_regions(
    *,
    width: int,
    height: int,
) -> list[RegionOfInterest]:
    slot_width = width // 4

    horizontal_margin = int(slot_width * 0.05)

    roi_y = int(height * 0.10)
    roi_bottom = int(height * 0.78)
    roi_height = roi_bottom - roi_y

    return [
        RegionOfInterest(
            x=(slot_width * index) + horizontal_margin,
            y=roi_y,
            width=slot_width - (horizontal_margin * 2),
            height=roi_height,
        )
        for index in range(4)
    ]


def main() -> None:
    reference_image = load_image(
        REFERENCE_IMAGE,
    )

    height, width = reference_image.shape[:2]

    regions = create_regions(
        width=width,
        height=height,
    )

    detector = OpenCVROIDetector(
        empty_reference=reference_image,
        regions=regions,
        difference_threshold=DIFFERENCE_THRESHOLD,
    )

    samples = [
        ("shelf_01_empty.png", 0),
        ("shelf_01_25.png", 1),
        ("shelf_01_50.png", 2),
        ("shelf_01_75.png", 3),
        ("shelf_01_full.png", 4),
    ]

    print()
    print("OpenCV ROI evaluation")
    print("-" * 94)
    print(
        f"{'Image':<22}"
        f"{'Expected':>10}"
        f"{'Detected':>10}"
        f"{'ROI 1':>10}"
        f"{'ROI 2':>10}"
        f"{'ROI 3':>10}"
        f"{'ROI 4':>10}"
    )
    print("-" * 94)

    total_absolute_error = 0

    for filename, expected_units in samples:
        image = load_image(SAMPLES_DIRECTORY / filename)

        scores = detector.score_regions(image)
        result = detector.detect(image)

        absolute_error = abs(expected_units - result.detected_units)

        total_absolute_error += absolute_error

        print(
            f"{filename:<22}"
            f"{expected_units:>10}"
            f"{result.detected_units:>10}"
            f"{scores[0]:>10.2f}"
            f"{scores[1]:>10.2f}"
            f"{scores[2]:>10.2f}"
            f"{scores[3]:>10.2f}"
        )

    mae = total_absolute_error / len(samples)

    print("-" * 94)
    print(f"MAE: {mae:.2f} units")
    print(f"Difference threshold: {DIFFERENCE_THRESHOLD:.2f}")


if __name__ == "__main__":
    main()
