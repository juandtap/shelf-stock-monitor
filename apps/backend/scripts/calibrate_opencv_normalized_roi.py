import json
from dataclasses import asdict, dataclass
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

OUTPUT_PATH = PROJECT_ROOT / "artifacts" / "calibration" / "opencv_roi_normalized_synthetic_v1.json"

SCENARIOS = (
    "baseline",
    "brightness_low",
    "brightness_high",
    "contrast_low",
    "gaussian_noise",
    "blur",
)

IMAGE_WIDTH = 1774
IMAGE_HEIGHT = 887

ANALYSIS_THRESHOLD = 0.0


@dataclass(frozen=True)
class SlotScore:
    score: float
    occupied: bool


@dataclass(frozen=True)
class ThresholdEvaluation:
    threshold: float
    errors: int
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    accuracy: float
    balanced_accuracy: float


@dataclass(frozen=True)
class CalibrationArtifact:
    dataset: str
    calibration_split: str
    detector: str
    scenarios: list[str]
    validation_images: int
    validation_slots: int
    empty_slots: int
    occupied_slots: int
    difference_threshold: float
    classification_errors: int
    accuracy: float
    balanced_accuracy: float
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int


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

        pixel_x = center_x * IMAGE_WIDTH
        pixel_y = center_y * IMAGE_HEIGHT

        matching_slots = [
            index
            for index, slot in enumerate(SYNTHETIC_SHELF_SLOTS)
            if (slot.x1 <= pixel_x < slot.x2 and slot.y1 <= pixel_y < slot.y2)
        ]

        if len(matching_slots) != 1:
            raise ValueError("Object center does not map to exactly one shelf slot.")

        occupied_slots.add(matching_slots[0])

    return occupied_slots


def collect_validation_scores(
    detector: OpenCVNormalizedROIDetector,
) -> tuple[list[SlotScore], int]:
    slot_scores: list[SlotScore] = []
    image_count = 0

    for scenario in SCENARIOS:
        images_directory = VALIDATION_DIRECTORY / scenario / "images"

        labels_directory = VALIDATION_DIRECTORY / scenario / "labels"

        image_paths = sorted(images_directory.glob("*.jpg"))

        if not image_paths:
            raise ValueError(f"No validation images for scenario: {scenario}")

        image_count += len(image_paths)

        for image_path in image_paths:
            label_path = labels_directory / f"{image_path.stem}.txt"

            occupied_slots = load_occupied_slots(label_path)

            image = load_image(image_path)

            scores = detector.score_regions(image)

            if len(scores) != len(SYNTHETIC_SHELF_SLOTS):
                raise ValueError("Unexpected number of ROI scores.")

            for index, score in enumerate(scores):
                slot_scores.append(
                    SlotScore(
                        score=score,
                        occupied=(index in occupied_slots),
                    )
                )

    return slot_scores, image_count


def calculate_balanced_accuracy(
    *,
    true_positives: int,
    true_negatives: int,
    false_positives: int,
    false_negatives: int,
) -> float:
    positive_count = true_positives + false_negatives

    negative_count = true_negatives + false_positives

    if positive_count == 0:
        raise ValueError("No positive validation samples.")

    if negative_count == 0:
        raise ValueError("No negative validation samples.")

    true_positive_rate = true_positives / positive_count

    true_negative_rate = true_negatives / negative_count

    return (true_positive_rate + true_negative_rate) / 2.0


def evaluate_threshold(
    *,
    threshold: float,
    slot_scores: list[SlotScore],
) -> ThresholdEvaluation:
    true_positives = 0
    true_negatives = 0
    false_positives = 0
    false_negatives = 0

    for slot_score in slot_scores:
        predicted_occupied = slot_score.score >= threshold

        if predicted_occupied and slot_score.occupied:
            true_positives += 1
        elif not predicted_occupied and not slot_score.occupied:
            true_negatives += 1
        elif predicted_occupied:
            false_positives += 1
        else:
            false_negatives += 1

    errors = false_positives + false_negatives

    accuracy = (true_positives + true_negatives) / len(slot_scores)

    balanced_accuracy = calculate_balanced_accuracy(
        true_positives=true_positives,
        true_negatives=true_negatives,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )

    return ThresholdEvaluation(
        threshold=threshold,
        errors=errors,
        true_positives=true_positives,
        true_negatives=true_negatives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        accuracy=accuracy,
        balanced_accuracy=(balanced_accuracy),
    )


def generate_candidate_thresholds(
    slot_scores: list[SlotScore],
) -> list[float]:
    unique_scores = sorted({slot_score.score for slot_score in slot_scores})

    if not unique_scores:
        raise ValueError("No validation scores available.")

    if len(unique_scores) == 1:
        return unique_scores

    candidates: list[float] = [unique_scores[0]]

    for left, right in zip(
        unique_scores,
        unique_scores[1:],
        strict=False,
    ):
        candidates.append((left + right) / 2.0)

    candidates.append(
        float(
            np.nextafter(
                unique_scores[-1],
                np.inf,
            )
        )
    )

    return candidates


def select_best_threshold(
    slot_scores: list[SlotScore],
) -> ThresholdEvaluation:
    candidates = generate_candidate_thresholds(slot_scores)

    evaluations = [
        evaluate_threshold(
            threshold=threshold,
            slot_scores=slot_scores,
        )
        for threshold in candidates
    ]

    return min(
        evaluations,
        key=lambda evaluation: (
            evaluation.errors,
            -evaluation.balanced_accuracy,
            evaluation.threshold,
        ),
    )


def main() -> None:
    reference = load_image(EMPTY_REFERENCE_PATH)

    detector = OpenCVNormalizedROIDetector(
        empty_reference=reference,
        regions=[slot.to_region_of_interest() for slot in SYNTHETIC_SHELF_SLOTS],
        difference_threshold=(ANALYSIS_THRESHOLD),
    )

    (
        slot_scores,
        image_count,
    ) = collect_validation_scores(detector)

    occupied_count = sum(slot_score.occupied for slot_score in slot_scores)

    empty_count = len(slot_scores) - occupied_count

    best = select_best_threshold(slot_scores)

    artifact = CalibrationArtifact(
        dataset=("synthetic-v1-robustness"),
        calibration_split="val",
        detector=("opencv_roi_normalized"),
        scenarios=list(SCENARIOS),
        validation_images=image_count,
        validation_slots=len(slot_scores),
        empty_slots=empty_count,
        occupied_slots=occupied_count,
        difference_threshold=(best.threshold),
        classification_errors=(best.errors),
        accuracy=best.accuracy,
        balanced_accuracy=(best.balanced_accuracy),
        true_positives=(best.true_positives),
        true_negatives=(best.true_negatives),
        false_positives=(best.false_positives),
        false_negatives=(best.false_negatives),
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            asdict(artifact),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("Normalized OpenCV calibration")
    print("=" * 70)
    print(f"Dataset: {artifact.dataset}")
    print(f"Split: {artifact.calibration_split}")
    print(f"Scenarios: {len(artifact.scenarios)}")
    print(f"Validation images: {artifact.validation_images}")
    print(f"Validation slots: {artifact.validation_slots}")
    print(f"Empty slots: {artifact.empty_slots}")
    print(f"Occupied slots: {artifact.occupied_slots}")
    print()
    print(f"Selected threshold: {artifact.difference_threshold:.6f}")
    print(f"Classification errors: {artifact.classification_errors}")
    print(f"Accuracy: {artifact.accuracy * 100:.4f}%")
    print(f"Balanced accuracy: {artifact.balanced_accuracy * 100:.4f}%")
    print()
    print("Confusion matrix:")
    print(f"  TP: {artifact.true_positives}")
    print(f"  TN: {artifact.true_negatives}")
    print(f"  FP: {artifact.false_positives}")
    print(f"  FN: {artifact.false_negatives}")
    print()
    print(f"Calibration: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
