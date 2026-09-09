from pathlib import Path

from app.benchmarking.mlflow_tracker import (
    MLflowBenchmarkTracker,
)
from app.benchmarking.models import BenchmarkSample
from app.benchmarking.runner import BenchmarkRunner
from app.core.config import get_settings
from app.vision.yolo import YOLOStockDetector

PROJECT_ROOT = Path(__file__).resolve().parents[3]

SAMPLES_DIRECTORY = PROJECT_ROOT / "data" / "samples"

MODEL_PATH = Path(__file__).resolve().parents[1] / "yolo11n.pt"

CONFIDENCE_THRESHOLDS = (
    0.10,
    0.15,
    0.20,
    0.25,
)

BOTTLE_CLASS_ID = 39

WARMUP_ITERATIONS = 2


def create_samples() -> list[BenchmarkSample]:
    return [
        BenchmarkSample(
            filename="shelf_01_full.png",
            expected_units=4,
            shelf_capacity=4,
        ),
        BenchmarkSample(
            filename="shelf_01_75.png",
            expected_units=3,
            shelf_capacity=4,
        ),
        BenchmarkSample(
            filename="shelf_01_50.png",
            expected_units=2,
            shelf_capacity=4,
        ),
        BenchmarkSample(
            filename="shelf_01_25.png",
            expected_units=1,
            shelf_capacity=4,
        ),
        BenchmarkSample(
            filename="shelf_01_empty.png",
            expected_units=0,
            shelf_capacity=4,
        ),
    ]


def run_threshold_benchmark(
    *,
    confidence_threshold: float,
    tracker: MLflowBenchmarkTracker,
) -> None:
    detector = YOLOStockDetector(
        model_path=str(MODEL_PATH),
        confidence_threshold=confidence_threshold,
        class_ids=[BOTTLE_CLASS_ID],
        device="cpu",
    )

    runner = BenchmarkRunner(
        detector=detector,
        samples_directory=SAMPLES_DIRECTORY,
        warmup_iterations=WARMUP_ITERATIONS,
    )

    results, summary = runner.run(
        samples=create_samples(),
    )

    run_name = f"yolo11n-bottle-conf-{confidence_threshold:.2f}"

    run_id = tracker.log_run(
        summary=summary,
        results=results,
        parameters={
            "detector": detector.name,
            "model": MODEL_PATH.name,
            "confidence_threshold": (confidence_threshold),
            "class_ids": str(BOTTLE_CLASS_ID),
            "device": "cpu",
            "shelf_capacity": 4,
            "warmup_iterations": (WARMUP_ITERATIONS),
        },
        run_name=run_name,
    )

    print()
    print(f"Threshold: {confidence_threshold:.2f}")
    print(f"Units MAE: {summary.units_mae:.3f}")
    print(f"Stock percentage MAE: {summary.stock_percentage_mae:.3f}")
    print(f"Latency mean: {summary.latency_mean_ms:.2f} ms")
    print(f"MLflow run ID: {run_id}")

    for result in results:
        print(
            f"  {result.filename}: "
            f"expected={result.expected_units}, "
            f"detected={result.detected_units}"
        )


def main() -> None:
    settings = get_settings()

    tracker = MLflowBenchmarkTracker(
        tracking_uri=settings.mlflow_tracking_uri,
        experiment_name=(settings.mlflow_experiment_name),
    )

    for confidence_threshold in CONFIDENCE_THRESHOLDS:
        run_threshold_benchmark(
            confidence_threshold=(confidence_threshold),
            tracker=tracker,
        )


if __name__ == "__main__":
    main()
