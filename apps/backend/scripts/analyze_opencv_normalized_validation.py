from pathlib import Path
from typing import cast

import cv2
import numpy as np

from app.vision.detector import ImageArray
from app.vision.opencv_normalized_roi import (
    OpenCVNormalizedROIDetector,
)
from app.vision.shelf_geometry import (
    SYNTHETIC_SHELF_SLOTS,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

VALIDATION_DIRECTORY = PROJECT_ROOT / "data" / "robustness" / "synthetic-v1" / "val"

EMPTY_REFERENCE_PATH = PROJECT_ROOT / "data" / "synthetic" / "assets" / "shelf_2x4.png"

SCENARIOS = (
    "baseline",
    "brightness_low",
    "brightness_high",
    "contrast_low",
    "gaussian_noise",
    "blur",
)

ANALYSIS_THRESHOLD = 0.0


def load_image(
    path: Path,
) -> ImageArray:
    image = cv2.imread(
        str(path),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(f"Unable to read image: {path}")

    return cast(
        ImageArray,
        image,
    )


def load_occupied_slots(
    label_path: Path,
) -> set[int]:
    if not label_path.is_file():
        raise FileNotFoundError(f"Label not found: {label_path}")

    content = label_path.read_text(encoding="utf-8").strip()

    if not content:
        return set()

    occupied_slots: set[int] = set()

    for line in content.splitlines():
        parts = line.split()

        if len(parts) != 5:
            raise ValueError(f"Invalid YOLO label line: {line}")

        center_x = float(parts[1])

        center_y = float(parts[2])

        image_width = 1774
        image_height = 887

        pixel_x = center_x * image_width

        pixel_y = center_y * image_height

        matching_slots = [
            index
            for index, slot in enumerate(SYNTHETIC_SHELF_SLOTS)
            if (slot.x1 <= pixel_x < slot.x2 and slot.y1 <= pixel_y < slot.y2)
        ]

        if len(matching_slots) != 1:
            raise ValueError("Object center does not map to exactly one shelf slot.")

        occupied_slots.add(matching_slots[0])

    return occupied_slots


def print_distribution(
    *,
    name: str,
    values: list[float],
) -> None:
    if not values:
        raise ValueError(f"No values available for {name}.")

    array = np.asarray(
        values,
        dtype=np.float64,
    )

    print(
        f"{name:<10} "
        f"min={np.min(array):>8.4f}  "
        f"p05={np.percentile(array, 5):>8.4f}  "
        f"p25={np.percentile(array, 25):>8.4f}  "
        f"median={np.median(array):>8.4f}  "
        f"p75={np.percentile(array, 75):>8.4f}  "
        f"p95={np.percentile(array, 95):>8.4f}  "
        f"max={np.max(array):>8.4f}  "
        f"mean={np.mean(array):>8.4f}"
    )


def main() -> None:
    reference = load_image(EMPTY_REFERENCE_PATH)

    detector = OpenCVNormalizedROIDetector(
        empty_reference=reference,
        regions=[slot.to_region_of_interest() for slot in SYNTHETIC_SHELF_SLOTS],
        difference_threshold=(ANALYSIS_THRESHOLD),
    )

    all_empty_scores: list[float] = []
    all_occupied_scores: list[float] = []

    print()
    print("Normalized OpenCV validation analysis")
    print("=" * 100)

    for scenario in SCENARIOS:
        images_directory = VALIDATION_DIRECTORY / scenario / "images"

        labels_directory = VALIDATION_DIRECTORY / scenario / "labels"

        image_paths = sorted(images_directory.glob("*.jpg"))

        if not image_paths:
            raise ValueError(f"No validation images for scenario: {scenario}")

        empty_scores: list[float] = []
        occupied_scores: list[float] = []

        for image_path in image_paths:
            label_path = labels_directory / f"{image_path.stem}.txt"

            occupied_slots = load_occupied_slots(label_path)

            image = load_image(image_path)

            scores = detector.score_regions(image)

            if len(scores) != len(SYNTHETIC_SHELF_SLOTS):
                raise ValueError("Unexpected number of ROI scores.")

            for index, score in enumerate(scores):
                if index in occupied_slots:
                    occupied_scores.append(score)
                    all_occupied_scores.append(score)
                else:
                    empty_scores.append(score)
                    all_empty_scores.append(score)

        print()
        print(f"Scenario: {scenario}")
        print("-" * 100)
        print(f"Images: {len(image_paths)}")
        print(f"Empty slots: {len(empty_scores)}")
        print(f"Occupied slots: {len(occupied_scores)}")

        print_distribution(
            name="Empty",
            values=empty_scores,
        )

        print_distribution(
            name="Occupied",
            values=occupied_scores,
        )

        highest_empty = max(empty_scores)
        lowest_occupied = min(occupied_scores)

        print(f"Gap: {lowest_occupied - highest_empty:.4f}")

    highest_empty = max(all_empty_scores)
    lowest_occupied = min(all_occupied_scores)

    gap = lowest_occupied - highest_empty

    print()
    print("=" * 100)
    print("Combined validation scenarios")
    print("-" * 100)
    print(f"Empty scores: {len(all_empty_scores)}")
    print(f"Occupied scores: {len(all_occupied_scores)}")

    print_distribution(
        name="Empty",
        values=all_empty_scores,
    )

    print_distribution(
        name="Occupied",
        values=all_occupied_scores,
    )

    print()
    print(f"Highest empty: {highest_empty:.4f}")
    print(f"Lowest occupied: {lowest_occupied:.4f}")
    print(f"Gap: {gap:.4f}")
    print(f"Perfect separation: {'yes' if gap > 0 else 'no'}")


if __name__ == "__main__":
    main()
