from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.vision.opencv_roi import OpenCVROIDetector
from app.vision.shelf_geometry import SYNTHETIC_SHELF_SLOTS

PROJECT_ROOT = Path(__file__).resolve().parents[3]

VALIDATION_IMAGES_DIRECTORY = PROJECT_ROOT / "data" / "yolo" / "images" / "val"

VALIDATION_LABELS_DIRECTORY = PROJECT_ROOT / "data" / "yolo" / "labels" / "val"

EMPTY_REFERENCE_PATH = PROJECT_ROOT / "data" / "synthetic" / "assets" / "shelf_2x4.png"

PLACEHOLDER_THRESHOLD = 0.0


@dataclass(frozen=True)
class SlotScore:
    filename: str
    slot_index: int
    occupied: bool
    score: float


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

        center_x_normalized = float(parts[1])
        center_y_normalized = float(parts[2])

        center_x = center_x_normalized * image_width

        center_y = center_y_normalized * image_height

        matching_slots = [
            index
            for index, slot in enumerate(SYNTHETIC_SHELF_SLOTS)
            if (slot.x1 <= center_x < slot.x2 and slot.y1 <= center_y < slot.y2)
        ]

        if len(matching_slots) != 1:
            raise ValueError(f"Unable to map object to exactly one shelf slot. Label: {line}")

        occupied_slots.add(matching_slots[0])

    return occupied_slots


def collect_scores() -> list[SlotScore]:
    reference = load_image(EMPTY_REFERENCE_PATH)

    detector = OpenCVROIDetector(
        empty_reference=reference,
        regions=[slot.to_region_of_interest() for slot in SYNTHETIC_SHELF_SLOTS],
        difference_threshold=(PLACEHOLDER_THRESHOLD),
    )

    image_paths = sorted(VALIDATION_IMAGES_DIRECTORY.glob("*.jpg"))

    if not image_paths:
        raise ValueError("No validation images were found.")

    scores: list[SlotScore] = []

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
            scores.append(
                SlotScore(
                    filename=image_path.name,
                    slot_index=slot_index,
                    occupied=(slot_index in occupied_slots),
                    score=score,
                )
            )

    return scores


def print_distribution(
    *,
    label: str,
    scores: list[float],
) -> None:
    values = np.asarray(
        scores,
        dtype=np.float64,
    )

    print()
    print(label)
    print("-" * 60)
    print(f"Count: {len(values)}")
    print(f"Min: {np.min(values):.4f}")
    print(f"p05: {np.percentile(values, 5):.4f}")
    print(f"p25: {np.percentile(values, 25):.4f}")
    print(f"Median: {np.median(values):.4f}")
    print(f"p75: {np.percentile(values, 75):.4f}")
    print(f"p95: {np.percentile(values, 95):.4f}")
    print(f"Max: {np.max(values):.4f}")
    print(f"Mean: {np.mean(values):.4f}")


def main() -> None:
    scores = collect_scores()

    empty_scores = [item.score for item in scores if not item.occupied]

    occupied_scores = [item.score for item in scores if item.occupied]

    if not empty_scores:
        raise ValueError("No empty slot samples were found.")

    if not occupied_scores:
        raise ValueError("No occupied slot samples were found.")

    print()
    print("OpenCV ROI validation analysis")
    print("=" * 60)
    print(f"Images: {len(scores) // len(SYNTHETIC_SHELF_SLOTS)}")
    print(f"Total slots: {len(scores)}")
    print(f"Empty slots: {len(empty_scores)}")
    print(f"Occupied slots: {len(occupied_scores)}")

    print_distribution(
        label="Empty slot scores",
        scores=empty_scores,
    )

    print_distribution(
        label="Occupied slot scores",
        scores=occupied_scores,
    )

    empty_max = max(empty_scores)
    occupied_min = min(occupied_scores)

    print()
    print("Separation")
    print("=" * 60)
    print(f"Highest empty score: {empty_max:.4f}")
    print(f"Lowest occupied score: {occupied_min:.4f}")

    if empty_max < occupied_min:
        gap = occupied_min - empty_max

        midpoint = (empty_max + occupied_min) / 2.0

        print("Perfect separation: yes")
        print(f"Gap: {gap:.4f}")
        print(f"Separation midpoint: {midpoint:.4f}")
    else:
        overlap = empty_max - occupied_min

        print("Perfect separation: no")
        print(f"Overlap range: {overlap:.4f}")


if __name__ == "__main__":
    main()
