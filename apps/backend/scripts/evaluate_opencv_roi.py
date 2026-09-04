from pathlib import Path

from app.benchmarking.mlflow_tracker import MLflowBenchmarkTracker
from app.benchmarking.models import BenchmarkSample
from app.benchmarking.runner import (
    BenchmarkRunner,
    load_benchmark_image,
)
from app.core.config import get_settings
from app.vision.models import RegionOfInterest
from app.vision.opencv_roi import OpenCVROIDetector

REFERENCE_IMAGE = Path("../../data/references/shelf_01_empty.png")

SAMPLES_DIRECTORY = Path("../../data/samples")

DIFFERENCE_THRESHOLD = 20.0

SHELF_CAPACITY = 4


def create_regions(
    *,
    width: int,
    height: int,
) -> list[RegionOfInterest]:
    slot_width = width // SHELF_CAPACITY
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
        for index in range(SHELF_CAPACITY)
    ]


def create_samples() -> list[BenchmarkSample]:
    return [
        BenchmarkSample(
            filename="shelf_01_empty.png",
            expected_units=0,
            shelf_capacity=SHELF_CAPACITY,
        ),
        BenchmarkSample(
            filename="shelf_01_25.png",
            expected_units=1,
            shelf_capacity=SHELF_CAPACITY,
        ),
        BenchmarkSample(
            filename="shelf_01_50.png",
            expected_units=2,
            shelf_capacity=SHELF_CAPACITY,
        ),
        BenchmarkSample(
            filename="shelf_01_75.png",
            expected_units=3,
            shelf_capacity=SHELF_CAPACITY,
        ),
        BenchmarkSample(
            filename="shelf_01_full.png",
            expected_units=4,
            shelf_capacity=SHELF_CAPACITY,
        ),
    ]


def main() -> None:
    settings = get_settings()

    reference_image = load_benchmark_image(REFERENCE_IMAGE)

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

    runner = BenchmarkRunner(
        detector=detector,
        samples_directory=SAMPLES_DIRECTORY,
    )

    samples = create_samples()

    results, summary = runner.run(
        samples=samples,
    )

    print()
    print("Stock detector benchmark")
    print("-" * 106)
    print(
        f"{'Image':<22}"
        f"{'Expected':>10}"
        f"{'Detected':>10}"
        f"{'Expected %':>12}"
        f"{'Detected %':>12}"
        f"{'Abs Error':>12}"
        f"{'Latency ms':>14}"
    )
    print("-" * 106)

    for result in results:
        print(
            f"{result.filename:<22}"
            f"{result.expected_units:>10}"
            f"{result.detected_units:>10}"
            f"{result.expected_stock_percentage:>12.2f}"
            f"{result.detected_stock_percentage:>12.2f}"
            f"{result.absolute_units_error:>12}"
            f"{result.latency_ms:>14.2f}"
        )

    print("-" * 106)
    print(f"Detector: {summary.detector_name}")
    print(f"Samples: {summary.sample_count}")
    print(f"Units MAE: {summary.units_mae:.2f}")
    print(f"Stock percentage MAE: {summary.stock_percentage_mae:.2f}%")
    print(f"Mean latency: {summary.latency_mean_ms:.2f} ms")
    print(f"Latency p50: {summary.latency_p50_ms:.2f} ms")
    print(f"Latency p95: {summary.latency_p95_ms:.2f} ms")
    print(f"Difference threshold: {DIFFERENCE_THRESHOLD:.2f}")

    tracker = MLflowBenchmarkTracker(
        tracking_uri=settings.mlflow_tracking_uri,
        experiment_name=settings.mlflow_experiment_name,
    )

    run_id = tracker.log_run(
        summary=summary,
        results=results,
        parameters={
            "detector": detector.name,
            "difference_threshold": DIFFERENCE_THRESHOLD,
            "shelf_capacity": SHELF_CAPACITY,
            "reference_image": str(REFERENCE_IMAGE),
        },
    )

    print(f"MLflow run ID: {run_id}")


if __name__ == "__main__":
    main()
