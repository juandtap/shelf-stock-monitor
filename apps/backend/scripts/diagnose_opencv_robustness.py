import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.vision.opencv_roi import OpenCVROIDetector
from app.vision.shelf_geometry import SYNTHETIC_SHELF_SLOTS

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ROBUSTNESS_DIRECTORY = PROJECT_ROOT / "data" / "robustness" / "synthetic-v1"

EMPTY_REFERENCE_PATH = PROJECT_ROOT / "data" / "synthetic" / "assets" / "shelf_2x4.png"

CALIBRATION_PATH = PROJECT_ROOT / "artifacts" / "calibration" / "opencv_roi_synthetic_v1.json"

SCENARIOS = (
    "baseline",
    "brightness_low",
    "brightness_high",
    "contrast_low",
    "gaussian_noise",
    "blur",
)


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


def load_threshold() -> float:
    if not CALIBRATION_PATH.is_file():
        raise FileNotFoundError(f"Calibration not found: {CALIBRATION_PATH}")

    data: Any = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("Calibration must contain a JSON object.")

    threshold = data.get("difference_threshold")

    if not isinstance(
        threshold,
        int | float,
    ):
        raise ValueError("Invalid difference threshold.")

    return float(threshold)


def count_expected_units(
    label_path: Path,
) -> int:
    if not label_path.is_file():
        raise FileNotFoundError(f"Label not found: {label_path}")

    content = label_path.read_text(encoding="utf-8").strip()

    if not content:
        return 0

    return len(content.splitlines())


def main() -> None:
    threshold = load_threshold()

    reference = load_image(EMPTY_REFERENCE_PATH)

    detector = OpenCVROIDetector(
        empty_reference=reference,
        regions=[slot.to_region_of_interest() for slot in SYNTHETIC_SHELF_SLOTS],
        difference_threshold=threshold,
    )

    print()
    print("OpenCV robustness diagnosis")
    print("=" * 72)
    print(f"Threshold: {threshold:.4f}")
    print()

    for scenario in SCENARIOS:
        images_directory = ROBUSTNESS_DIRECTORY / scenario / "images"

        labels_directory = ROBUSTNESS_DIRECTORY / scenario / "labels"

        image_paths = sorted(images_directory.glob("*.jpg"))

        if not image_paths:
            raise ValueError(f"No images found for scenario: {scenario}")

        expected_counts: list[int] = []
        detected_counts: list[int] = []
        all_scores: list[float] = []

        for image_path in image_paths:
            image = load_image(image_path)

            label_path = labels_directory / f"{image_path.stem}.txt"

            expected = count_expected_units(label_path)

            scores = detector.score_regions(image)

            detected = sum(score >= threshold for score in scores)

            expected_counts.append(expected)

            detected_counts.append(detected)

            all_scores.extend(scores)

        exact_matches = sum(
            expected == detected
            for expected, detected in zip(
                expected_counts,
                detected_counts,
                strict=True,
            )
        )

        unique_predictions = sorted(set(detected_counts))

        print(scenario)
        print("-" * 72)
        print(f"Expected count range: {min(expected_counts)}..{max(expected_counts)}")
        print(f"Detected count range: {min(detected_counts)}..{max(detected_counts)}")
        print(f"Unique predictions: {unique_predictions}")
        print(f"Mean detected units: {np.mean(detected_counts):.3f}")
        print(f"Exact scenes: {exact_matches}/{len(image_paths)}")
        print(f"ROI score min: {min(all_scores):.4f}")
        print(f"ROI score median: {np.median(all_scores):.4f}")
        print(f"ROI score max: {max(all_scores):.4f}")
        print()


if __name__ == "__main__":
    main()
