import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import cv2
import mlflow
import numpy as np

from app.benchmarking.mlflow_tracker import MLflowBenchmarkTracker
from app.benchmarking.models import BenchmarkResult, BenchmarkSummary
from app.core.config import get_settings
from app.vision.detector import StockDetector
from app.vision.opencv_roi import OpenCVROIDetector
from app.vision.shelf_geometry import SYNTHETIC_SHELF_SLOTS
from app.vision.yolo import YOLOStockDetector

PROJECT_ROOT = Path(__file__).resolve().parents[3]

TEST_IMAGES_DIRECTORY = PROJECT_ROOT / "data" / "yolo" / "images" / "test"

TEST_LABELS_DIRECTORY = PROJECT_ROOT / "data" / "yolo" / "labels" / "test"

EMPTY_REFERENCE_PATH = PROJECT_ROOT / "data" / "synthetic" / "assets" / "shelf_2x4.png"

OPENCV_CALIBRATION_PATH = (
    PROJECT_ROOT / "artifacts" / "calibration" / "opencv_roi_synthetic_v1.json"
)

YOLO_MODEL_PATH = (
    PROJECT_ROOT / "artifacts" / "models" / "yolo" / "yolo11n-synthetic-v1" / "best.pt"
)

SHELF_CAPACITY = len(SYNTHETIC_SHELF_SLOTS)

YOLO_CONFIDENCE_THRESHOLD = 0.25
YOLO_IOU_THRESHOLD = 0.70
YOLO_IMAGE_SIZE = 640
YOLO_DEVICE = "cpu"

WARMUP_ITERATIONS = 2

BENCHMARK_DATASET = "synthetic-v1-common-test"


@dataclass(frozen=True)
class TestSample:
    image_path: Path
    expected_units: int


@dataclass(frozen=True)
class OpenCVCalibration:
    dataset: str
    calibration_split: str
    difference_threshold: float


def load_image(path: Path) -> np.ndarray:
    image = cv2.imread(
        str(path),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(f"Unable to read image: {path}")

    return image


def load_opencv_calibration() -> OpenCVCalibration:
    if not OPENCV_CALIBRATION_PATH.is_file():
        raise FileNotFoundError(f"OpenCV calibration not found: {OPENCV_CALIBRATION_PATH}")

    raw_data: Any = json.loads(OPENCV_CALIBRATION_PATH.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("OpenCV calibration must contain a JSON object.")

    dataset = raw_data.get("dataset")
    calibration_split = raw_data.get("calibration_split")
    threshold = raw_data.get("difference_threshold")

    if not isinstance(dataset, str):
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

    if dataset != "synthetic-v1":
        raise ValueError(f"Unexpected calibration dataset: {dataset}")

    if calibration_split != "val":
        raise ValueError("OpenCV threshold must be calibrated using the validation split.")

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


def load_test_samples() -> list[TestSample]:
    image_paths = sorted(TEST_IMAGES_DIRECTORY.glob("*.jpg"))

    if not image_paths:
        raise ValueError("No test images were found.")

    samples: list[TestSample] = []

    for image_path in image_paths:
        label_path = TEST_LABELS_DIRECTORY / f"{image_path.stem}.txt"

        samples.append(
            TestSample(
                image_path=image_path,
                expected_units=(count_ground_truth_objects(label_path)),
            )
        )

    return samples


def validate_inputs() -> None:
    if not EMPTY_REFERENCE_PATH.is_file():
        raise FileNotFoundError(f"Empty shelf reference not found: {EMPTY_REFERENCE_PATH}")

    if not OPENCV_CALIBRATION_PATH.is_file():
        raise FileNotFoundError(f"OpenCV calibration not found: {OPENCV_CALIBRATION_PATH}")

    if not YOLO_MODEL_PATH.is_file():
        raise FileNotFoundError(f"Fine-tuned YOLO model not found: {YOLO_MODEL_PATH}")

    if not TEST_IMAGES_DIRECTORY.is_dir():
        raise FileNotFoundError(f"Test images directory not found: {TEST_IMAGES_DIRECTORY}")

    if not TEST_LABELS_DIRECTORY.is_dir():
        raise FileNotFoundError(f"Test labels directory not found: {TEST_LABELS_DIRECTORY}")


def create_opencv_detector(
    calibration: OpenCVCalibration,
) -> OpenCVROIDetector:
    reference = load_image(EMPTY_REFERENCE_PATH)

    regions = [slot.to_region_of_interest() for slot in SYNTHETIC_SHELF_SLOTS]

    return OpenCVROIDetector(
        empty_reference=reference,
        regions=regions,
        difference_threshold=(calibration.difference_threshold),
    )


def create_yolo_detector() -> YOLOStockDetector:
    return YOLOStockDetector(
        model_path=str(YOLO_MODEL_PATH),
        confidence_threshold=(YOLO_CONFIDENCE_THRESHOLD),
        iou_threshold=YOLO_IOU_THRESHOLD,
        image_size=YOLO_IMAGE_SIZE,
        device=YOLO_DEVICE,
    )


def warm_up_detector(
    *,
    detector: StockDetector,
    image: np.ndarray,
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
                filename=sample.image_path.name,
                detector_name=detector.name,
                expected_units=(sample.expected_units),
                detected_units=(detection.detected_units),
                shelf_capacity=SHELF_CAPACITY,
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


def print_summary(
    *,
    summary: BenchmarkSummary,
    exact_count_accuracy: float,
) -> None:
    print()
    print(summary.detector_name)
    print("=" * 60)
    print(f"Samples: {summary.sample_count}")
    print(f"Units MAE: {summary.units_mae:.4f}")
    print(f"Stock percentage MAE: {summary.stock_percentage_mae:.4f}%")
    print(f"Exact-count accuracy: {exact_count_accuracy * 100:.2f}%")
    print(f"Latency mean: {summary.latency_mean_ms:.2f} ms")
    print(f"Latency p50: {summary.latency_p50_ms:.2f} ms")
    print(f"Latency p95: {summary.latency_p95_ms:.2f} ms")


def log_benchmark(
    *,
    tracker: MLflowBenchmarkTracker,
    summary: BenchmarkSummary,
    results: list[BenchmarkResult],
    exact_count_accuracy: float,
    parameters: dict[
        str,
        str | int | float | bool,
    ],
    run_name: str,
) -> str:
    run_id = tracker.log_run(
        summary=summary,
        results=results,
        parameters={
            **parameters,
            "benchmark_dataset": (BENCHMARK_DATASET),
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


def main() -> None:
    validate_inputs()

    settings = get_settings()

    calibration = load_opencv_calibration()

    print()
    print(f"OpenCV calibrated threshold: {calibration.difference_threshold:.4f}")
    print(f"Calibration source: {calibration.dataset}/{calibration.calibration_split}")

    samples = load_test_samples()

    tracker = MLflowBenchmarkTracker(
        tracking_uri=(settings.mlflow_tracking_uri),
        experiment_name=(settings.mlflow_experiment_name),
    )

    opencv_detector = create_opencv_detector(calibration)

    yolo_detector = create_yolo_detector()

    (
        opencv_results,
        opencv_summary,
    ) = run_detector(
        detector=opencv_detector,
        samples=samples,
    )

    opencv_exact_accuracy = calculate_exact_count_accuracy(opencv_results)

    print_summary(
        summary=opencv_summary,
        exact_count_accuracy=(opencv_exact_accuracy),
    )

    opencv_run_id = log_benchmark(
        tracker=tracker,
        summary=opencv_summary,
        results=opencv_results,
        exact_count_accuracy=(opencv_exact_accuracy),
        parameters={
            "detector": "opencv_roi",
            "difference_threshold": (calibration.difference_threshold),
            "calibration_dataset": (calibration.dataset),
            "calibration_split": (calibration.calibration_split),
            "calibration_artifact": (OPENCV_CALIBRATION_PATH.name),
            "reference_image": (EMPTY_REFERENCE_PATH.name),
        },
        run_name=("opencv-roi-calibrated-synthetic-v1-common-test"),
    )

    print(f"MLflow run ID: {opencv_run_id}")

    (
        yolo_results,
        yolo_summary,
    ) = run_detector(
        detector=yolo_detector,
        samples=samples,
    )

    yolo_exact_accuracy = calculate_exact_count_accuracy(yolo_results)

    print_summary(
        summary=yolo_summary,
        exact_count_accuracy=(yolo_exact_accuracy),
    )

    yolo_run_id = log_benchmark(
        tracker=tracker,
        summary=yolo_summary,
        results=yolo_results,
        exact_count_accuracy=(yolo_exact_accuracy),
        parameters={
            "detector": "yolo",
            "model": YOLO_MODEL_PATH.name,
            "training": "fine_tuned",
            "confidence_threshold": (YOLO_CONFIDENCE_THRESHOLD),
            "iou_threshold": (YOLO_IOU_THRESHOLD),
            "image_size": YOLO_IMAGE_SIZE,
            "device": YOLO_DEVICE,
        },
        run_name=("yolo-finetuned-synthetic-v1-common-test"),
    )

    print(f"MLflow run ID: {yolo_run_id}")


if __name__ == "__main__":
    main()
