import json
from pathlib import Path

import cv2
import numpy as np

from app.vision.opencv_roi import OpenCVROIDetector
from app.vision.shelf_geometry import SYNTHETIC_SHELF_SLOTS

PROJECT_ROOT = Path(__file__).resolve().parents[3]

VALIDATION_IMAGES_DIRECTORY = PROJECT_ROOT / "data" / "yolo" / "images" / "val"

VALIDATION_LABELS_DIRECTORY = PROJECT_ROOT / "data" / "yolo" / "labels" / "val"

EMPTY_REFERENCE_PATH = PROJECT_ROOT / "data" / "synthetic" / "assets" / "shelf_2x4.png"

CALIBRATION_PATH = PROJECT_ROOT / "artifacts" / "calibration" / "opencv_roi_synthetic_v1.json"

DATASET_NAME = "synthetic-v1"
CALIBRATION_SPLIT = "val"

PLACEHOLDER_THRESHOLD = 0.0


def load_image(
    path: Path,
) -> np.ndarray:
    image = cv2.imread(
        str(path),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(f"Unable to read image: {path}")

    return image


def load_occupied_slots(
    *,
    label_path: Path,
    image_width: int,
    image_height: int,
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
            raise ValueError(f"Invalid YOLO label: {line}")

        center_x = float(parts[1]) * image_width

        center_y = float(parts[2]) * image_height

        matching_slots = [
            index
            for index, slot in enumerate(SYNTHETIC_SHELF_SLOTS)
            if (slot.x1 <= center_x < slot.x2 and slot.y1 <= center_y < slot.y2)
        ]

        if len(matching_slots) != 1:
            raise ValueError(f"Unable to map object to exactly one shelf slot. Label: {line}")

        occupied_slots.add(matching_slots[0])

    return occupied_slots


def collect_validation_scores() -> tuple[
    list[float],
    list[float],
    int,
]:
    reference = load_image(EMPTY_REFERENCE_PATH)

    detector = OpenCVROIDetector(
        empty_reference=reference,
        regions=[slot.to_region_of_interest() for slot in SYNTHETIC_SHELF_SLOTS],
        difference_threshold=(PLACEHOLDER_THRESHOLD),
    )

    image_paths = sorted(VALIDATION_IMAGES_DIRECTORY.glob("*.jpg"))

    if not image_paths:
        raise ValueError("No validation images were found.")

    empty_scores: list[float] = []
    occupied_scores: list[float] = []

    for image_path in image_paths:
        image = load_image(image_path)

        image_height, image_width = image.shape[:2]

        label_path = VALIDATION_LABELS_DIRECTORY / f"{image_path.stem}.txt"

        occupied_slots = load_occupied_slots(
            label_path=label_path,
            image_width=image_width,
            image_height=image_height,
        )

        region_scores = detector.score_regions(image)

        if len(region_scores) != len(SYNTHETIC_SHELF_SLOTS):
            raise ValueError("Unexpected number of ROI scores.")

        for slot_index, score in enumerate(region_scores):
            if slot_index in occupied_slots:
                occupied_scores.append(score)
            else:
                empty_scores.append(score)

    return (
        empty_scores,
        occupied_scores,
        len(image_paths),
    )


def calculate_threshold(
    *,
    empty_scores: list[float],
    occupied_scores: list[float],
) -> tuple[
    float,
    float,
    float,
]:
    if not empty_scores:
        raise ValueError("No empty slot scores were found.")

    if not occupied_scores:
        raise ValueError("No occupied slot scores were found.")

    empty_max = max(empty_scores)
    occupied_min = min(occupied_scores)

    if empty_max >= occupied_min:
        raise ValueError(
            "Validation scores are not perfectly "
            "separable. A midpoint threshold cannot "
            "be selected safely."
        )

    threshold = (empty_max + occupied_min) / 2.0

    return (
        empty_max,
        occupied_min,
        threshold,
    )


def write_calibration(
    *,
    empty_max: float,
    occupied_min: float,
    threshold: float,
    image_count: int,
    empty_count: int,
    occupied_count: int,
) -> None:
    CALIBRATION_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    calibration = {
        "dataset": DATASET_NAME,
        "calibration_split": CALIBRATION_SPLIT,
        "image_count": image_count,
        "shelf_capacity": len(SYNTHETIC_SHELF_SLOTS),
        "validation_slots": (empty_count + occupied_count),
        "empty_slots": empty_count,
        "occupied_slots": occupied_count,
        "empty_max_score": empty_max,
        "occupied_min_score": (occupied_min),
        "separation_gap": (occupied_min - empty_max),
        "difference_threshold": (threshold),
    }

    CALIBRATION_PATH.write_text(
        json.dumps(
            calibration,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    (
        empty_scores,
        occupied_scores,
        image_count,
    ) = collect_validation_scores()

    (
        empty_max,
        occupied_min,
        threshold,
    ) = calculate_threshold(
        empty_scores=empty_scores,
        occupied_scores=occupied_scores,
    )

    write_calibration(
        empty_max=empty_max,
        occupied_min=occupied_min,
        threshold=threshold,
        image_count=image_count,
        empty_count=len(empty_scores),
        occupied_count=len(occupied_scores),
    )

    print()
    print("OpenCV ROI calibration")
    print("=" * 60)
    print(f"Dataset: {DATASET_NAME}")
    print(f"Split: {CALIBRATION_SPLIT}")
    print(f"Images: {image_count}")
    print(f"Validation slots: {len(empty_scores) + len(occupied_scores)}")
    print(f"Empty slots: {len(empty_scores)}")
    print(f"Occupied slots: {len(occupied_scores)}")
    print(f"Highest empty score: {empty_max:.4f}")
    print(f"Lowest occupied score: {occupied_min:.4f}")
    print(f"Separation gap: {occupied_min - empty_max:.4f}")
    print(f"Selected threshold: {threshold:.4f}")
    print(f"Calibration: {CALIBRATION_PATH}")


if __name__ == "__main__":
    main()
