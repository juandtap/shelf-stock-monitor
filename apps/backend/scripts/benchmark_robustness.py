import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, cast

import cv2
import mlflow
import numpy as np

from app.benchmarking.mlflow_tracker import MLflowBenchmarkTracker
from app.benchmarking.models import BenchmarkResult, BenchmarkSummary
from app.core.config import get_settings
from app.vision.detector import ImageArray, StockDetector
from app.vision.opencv_normalized_roi import (
    OpenCVNormalizedROIDetector,
)
from app.vision.opencv_roi import OpenCVROIDetector
from app.vision.shelf_geometry import SYNTHETIC_SHELF_SLOTS
from app.vision.yolo import YOLOStockDetector

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ROBUSTNESS_TEST_DIRECTORY = PROJECT_ROOT / "data" / "robustness" / "synthetic-v1" / "test"

EMPTY_REFERENCE_PATH = PROJECT_ROOT / "data" / "synthetic" / "assets" / "shelf_2x4.png"

OPENCV_CALIBRATION_PATH = (
    PROJECT_ROOT / "artifacts" / "calibration" / "opencv_roi_synthetic_v1.json"
)

OPENCV_NORMALIZED_CALIBRATION_PATH = (
    PROJECT_ROOT / "artifacts" / "calibration" / "opencv_roi_normalized_synthetic_v1.json"
)

YOLO_MODEL_PATH = (
    PROJECT_ROOT / "artifacts" / "models" / "yolo" / "yolo11n-synthetic-v1" / "best.pt"
)

SCENARIOS = (
    "baseline",
    "brightness_low",
    "brightness_high",
    "contrast_low",
    "gaussian_noise",
    "blur",
)

SHELF_CAPACITY = len(SYNTHETIC_SHELF_SLOTS)

YOLO_CONFIDENCE_THRESHOLD = 0.25
YOLO_IOU_THRESHOLD = 0.70
YOLO_IMAGE_SIZE = 640
YOLO_DEVICE = "cpu"

WARMUP_ITERATIONS = 2

BENCHMARK_DATASET = "synthetic-v1-robustness"

BENCHMARK_SPLIT = "test"


@dataclass(frozen=True)
class TestSample:
    image_path: Path
    expected_units: int


@dataclass(frozen=True)
class OpenCVCalibration:
    dataset: str
    calibration_split: str
    difference_threshold: float


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


def load_calibration(
    *,
    path: Path,
    expected_dataset: str,
) -> OpenCVCalibration:
    if not path.is_file():
        raise FileNotFoundError(f"OpenCV calibration not found: {path}")

    raw_data: Any = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(
        raw_data,
        dict,
    ):
        raise ValueError("Calibration must contain a JSON object.")

    dataset = raw_data.get("dataset")

    calibration_split = raw_data.get("calibration_split")

    threshold = raw_data.get("difference_threshold")

    if not isinstance(
        dataset,
        str,
    ):
        raise ValueError("Invalid calibration dataset.")

    if not isinstance(
        calibration_split,
        str,
    ):
        raise ValueError("Invalid calibration split.")

    if not isinstance(
        threshold,
        int | float,
    ):
        raise ValueError("Invalid calibration threshold.")

    if dataset != expected_dataset:
        raise ValueError(f"Unexpected calibration dataset: {dataset}")

    if calibration_split != "val":
        raise ValueError("OpenCV threshold must originate from the validation split.")

    return OpenCVCalibration(
        dataset=dataset,
        calibration_split=(calibration_split),
        difference_threshold=float(threshold),
    )


def count_ground_truth_objects(
    label_path: Path,
) -> int:
    if not label_path.is_file():
        raise FileNotFoundError(f"Label not found: {label_path}")

    content = label_path.read_text(encoding="utf-8").strip()

    if not content:
        return 0

    return len(content.splitlines())


def load_scenario_samples(
    scenario: str,
) -> list[TestSample]:
    scenario_directory = ROBUSTNESS_TEST_DIRECTORY / scenario

    images_directory = scenario_directory / "images"

    labels_directory = scenario_directory / "labels"

    if not images_directory.is_dir():
        raise FileNotFoundError(f"Scenario images not found: {images_directory}")

    if not labels_directory.is_dir():
        raise FileNotFoundError(f"Scenario labels not found: {labels_directory}")

    image_paths = sorted(images_directory.glob("*.jpg"))

    if not image_paths:
        raise ValueError(f"No images found for scenario: {scenario}")

    samples: list[TestSample] = []

    for image_path in image_paths:
        label_path = labels_directory / f"{image_path.stem}.txt"

        samples.append(
            TestSample(
                image_path=image_path,
                expected_units=(count_ground_truth_objects(label_path)),
            )
        )

    return samples


def create_opencv_detector(
    calibration: OpenCVCalibration,
) -> OpenCVROIDetector:
    reference = load_image(EMPTY_REFERENCE_PATH)

    return OpenCVROIDetector(
        empty_reference=reference,
        regions=[slot.to_region_of_interest() for slot in SYNTHETIC_SHELF_SLOTS],
        difference_threshold=(calibration.difference_threshold),
    )


def create_opencv_normalized_detector(
    calibration: OpenCVCalibration,
) -> OpenCVNormalizedROIDetector:
    reference = load_image(EMPTY_REFERENCE_PATH)

    return OpenCVNormalizedROIDetector(
        empty_reference=reference,
        regions=[slot.to_region_of_interest() for slot in SYNTHETIC_SHELF_SLOTS],
        difference_threshold=(calibration.difference_threshold),
    )


def create_yolo_detector() -> YOLOStockDetector:
    if not YOLO_MODEL_PATH.is_file():
        raise FileNotFoundError(f"YOLO model not found: {YOLO_MODEL_PATH}")

    return YOLOStockDetector(
        model_path=str(YOLO_MODEL_PATH),
        confidence_threshold=(YOLO_CONFIDENCE_THRESHOLD),
        iou_threshold=(YOLO_IOU_THRESHOLD),
        image_size=YOLO_IMAGE_SIZE,
        device=YOLO_DEVICE,
    )


def warm_up_detector(
    *,
    detector: StockDetector,
    image: ImageArray,
) -> None:
    for _ in range(WARMUP_ITERATIONS):
        detector.detect(image)


def run_detector(
    *,
    detector: StockDetector,
    samples: list[TestSample],
) -> tuple[
    list[BenchmarkResult],
    BenchmarkSummary,
]:
    first_image = load_image(samples[0].image_path)

    warm_up_detector(
        detector=detector,
        image=first_image,
    )

    results: list[BenchmarkResult] = []

    for sample in samples:
        image = load_image(sample.image_path)

        start = perf_counter()

        detection = detector.detect(image)

        latency_ms = (perf_counter() - start) * 1000.0

        expected_percentage = (sample.expected_units / SHELF_CAPACITY) * 100.0

        detected_percentage = (detection.detected_units / SHELF_CAPACITY) * 100.0

        results.append(
            BenchmarkResult(
                filename=(sample.image_path.name),
                detector_name=(detector.name),
                expected_units=(sample.expected_units),
                detected_units=(detection.detected_units),
                shelf_capacity=(SHELF_CAPACITY),
                expected_stock_percentage=(expected_percentage),
                detected_stock_percentage=(detected_percentage),
                absolute_units_error=abs(sample.expected_units - detection.detected_units),
                absolute_stock_percentage_error=abs(expected_percentage - detected_percentage),
                latency_ms=latency_ms,
            )
        )

    units_errors = [result.absolute_units_error for result in results]

    percentage_errors = [result.absolute_stock_percentage_error for result in results]

    latencies = [result.latency_ms for result in results]

    summary = BenchmarkSummary(
        detector_name=detector.name,
        sample_count=len(results),
        units_mae=float(np.mean(units_errors)),
        stock_percentage_mae=float(np.mean(percentage_errors)),
        latency_mean_ms=float(np.mean(latencies)),
        latency_p50_ms=float(
            np.percentile(
                latencies,
                50,
            )
        ),
        latency_p95_ms=float(
            np.percentile(
                latencies,
                95,
            )
        ),
    )

    return results, summary


def calculate_exact_count_accuracy(
    results: list[BenchmarkResult],
) -> float:
    exact_matches = sum(result.detected_units == result.expected_units for result in results)

    return exact_matches / len(results)


def log_run(
    *,
    tracker: MLflowBenchmarkTracker,
    scenario: str,
    summary: BenchmarkSummary,
    results: list[BenchmarkResult],
    exact_count_accuracy: float,
    parameters: dict[
        str,
        str | int | float | bool,
    ],
) -> str:
    run_name = f"{summary.detector_name}-robustness-{scenario}-{BENCHMARK_SPLIT}"

    run_id = tracker.log_run(
        summary=summary,
        results=results,
        parameters={
            **parameters,
            "benchmark_dataset": (BENCHMARK_DATASET),
            "benchmark_split": (BENCHMARK_SPLIT),
            "scenario": scenario,
            "shelf_capacity": (SHELF_CAPACITY),
            "warmup_iterations": (WARMUP_ITERATIONS),
        },
        run_name=run_name,
    )

    with mlflow.start_run(
        run_id=run_id,
    ):
        mlflow.log_metric(
            "exact_count_accuracy",
            exact_count_accuracy,
        )

    return run_id


def print_result(
    *,
    scenario: str,
    detector_name: str,
    summary: BenchmarkSummary,
    exact_count_accuracy: float,
    run_id: str,
) -> None:
    print(
        f"{scenario:<20} "
        f"{detector_name:<24} "
        f"MAE={summary.units_mae:>6.3f}  "
        f"Exact="
        f"{exact_count_accuracy * 100:>6.2f}%  "
        f"Mean="
        f"{summary.latency_mean_ms:>7.2f} ms  "
        f"p95="
        f"{summary.latency_p95_ms:>7.2f} ms"
    )

    print(f"{'':<20} {'':<24} MLflow={run_id}")


def main() -> None:
    settings = get_settings()

    opencv_calibration = load_calibration(
        path=OPENCV_CALIBRATION_PATH,
        expected_dataset=("synthetic-v1"),
    )

    normalized_calibration = load_calibration(
        path=(OPENCV_NORMALIZED_CALIBRATION_PATH),
        expected_dataset=("synthetic-v1-robustness"),
    )

    opencv_detector = create_opencv_detector(opencv_calibration)

    normalized_detector = create_opencv_normalized_detector(normalized_calibration)

    yolo_detector = create_yolo_detector()

    tracker = MLflowBenchmarkTracker(
        tracking_uri=(settings.mlflow_tracking_uri),
        experiment_name=(settings.mlflow_experiment_name),
    )

    print()
    print("Detector robustness benchmark")
    print("=" * 110)
    print(f"Dataset: {BENCHMARK_DATASET}")
    print(f"Evaluation split: {BENCHMARK_SPLIT}")
    print(
        "OpenCV threshold: "
        f"{opencv_calibration.difference_threshold:.6f} "
        f"({opencv_calibration.dataset}/"
        f"{opencv_calibration.calibration_split})"
    )
    print(
        "Normalized OpenCV threshold: "
        f"{normalized_calibration.difference_threshold:.6f} "
        f"({normalized_calibration.dataset}/"
        f"{normalized_calibration.calibration_split})"
    )
    print(f"YOLO confidence: {YOLO_CONFIDENCE_THRESHOLD:.2f}")
    print(f"Device: {YOLO_DEVICE}")
    print()

    for scenario in SCENARIOS:
        samples = load_scenario_samples(scenario)

        (
            opencv_results,
            opencv_summary,
        ) = run_detector(
            detector=opencv_detector,
            samples=samples,
        )

        opencv_exact = calculate_exact_count_accuracy(opencv_results)

        opencv_run_id = log_run(
            tracker=tracker,
            scenario=scenario,
            summary=opencv_summary,
            results=opencv_results,
            exact_count_accuracy=(opencv_exact),
            parameters={
                "detector": "opencv_roi",
                "difference_threshold": (opencv_calibration.difference_threshold),
                "calibration_dataset": (opencv_calibration.dataset),
                "calibration_split": (opencv_calibration.calibration_split),
            },
        )

        print_result(
            scenario=scenario,
            detector_name=(opencv_detector.name),
            summary=opencv_summary,
            exact_count_accuracy=(opencv_exact),
            run_id=opencv_run_id,
        )

        (
            normalized_results,
            normalized_summary,
        ) = run_detector(
            detector=normalized_detector,
            samples=samples,
        )

        normalized_exact = calculate_exact_count_accuracy(normalized_results)

        normalized_run_id = log_run(
            tracker=tracker,
            scenario=scenario,
            summary=normalized_summary,
            results=normalized_results,
            exact_count_accuracy=(normalized_exact),
            parameters={
                "detector": ("opencv_roi_normalized"),
                "difference_threshold": (normalized_calibration.difference_threshold),
                "calibration_dataset": (normalized_calibration.dataset),
                "calibration_split": (normalized_calibration.calibration_split),
            },
        )

        print_result(
            scenario=scenario,
            detector_name=(normalized_detector.name),
            summary=normalized_summary,
            exact_count_accuracy=(normalized_exact),
            run_id=(normalized_run_id),
        )

        (
            yolo_results,
            yolo_summary,
        ) = run_detector(
            detector=yolo_detector,
            samples=samples,
        )

        yolo_exact = calculate_exact_count_accuracy(yolo_results)

        yolo_run_id = log_run(
            tracker=tracker,
            scenario=scenario,
            summary=yolo_summary,
            results=yolo_results,
            exact_count_accuracy=(yolo_exact),
            parameters={
                "detector": "yolo",
                "model": (YOLO_MODEL_PATH.name),
                "training": "fine_tuned",
                "confidence_threshold": (YOLO_CONFIDENCE_THRESHOLD),
                "iou_threshold": (YOLO_IOU_THRESHOLD),
                "image_size": (YOLO_IMAGE_SIZE),
                "device": YOLO_DEVICE,
            },
        )

        print_result(
            scenario=scenario,
            detector_name=(yolo_detector.name),
            summary=yolo_summary,
            exact_count_accuracy=(yolo_exact),
            run_id=yolo_run_id,
        )

        print()


if __name__ == "__main__":
    main()
