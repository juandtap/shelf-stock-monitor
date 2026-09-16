from pathlib import Path

from ultralytics import YOLO  # type: ignore[attr-defined]

from app.benchmarking.mlflow_tracker import (
    MLflowBenchmarkTracker,
)
from app.benchmarking.models import BenchmarkSample
from app.benchmarking.runner import BenchmarkRunner
from app.core.config import get_settings
from app.vision.yolo import YOLOStockDetector

PROJECT_ROOT = Path(__file__).resolve().parents[3]

SAMPLES_DIRECTORY = PROJECT_ROOT / "data" / "samples"

MODEL_NAME = "yolo11n.pt"

MODEL_CACHE_DIRECTORY = PROJECT_ROOT / "artifacts" / "models" / "pretrained"

CONFIDENCE_THRESHOLDS = (
    0.10,
    0.15,
    0.20,
    0.25,
)

BOTTLE_CLASS_ID = 39
SHELF_CAPACITY = 4
WARMUP_ITERATIONS = 2


def ensure_model() -> Path:
    MODEL_CACHE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    model_path = MODEL_CACHE_DIRECTORY / MODEL_NAME

    if model_path.is_file():
        return model_path

    model = YOLO(MODEL_NAME)

    source_path = Path(model.ckpt_path)

    if not source_path.is_file():
        raise FileNotFoundError(f"Downloaded model not found: {source_path}")

    model_path.write_bytes(source_path.read_bytes())

    return model_path


def create_samples() -> list[BenchmarkSample]:
    return [
        BenchmarkSample(
            filename="shelf_01_full.png",
            expected_units=4,
            shelf_capacity=SHELF_CAPACITY,
        ),
        BenchmarkSample(
            filename="shelf_01_75.png",
            expected_units=3,
            shelf_capacity=SHELF_CAPACITY,
        ),
        BenchmarkSample(
            filename="shelf_01_50.png",
            expected_units=2,
            shelf_capacity=SHELF_CAPACITY,
        ),
        BenchmarkSample(
            filename="shelf_01_25.png",
            expected_units=1,
            shelf_capacity=SHELF_CAPACITY,
        ),
        BenchmarkSample(
            filename="shelf_01_empty.png",
            expected_units=0,
            shelf_capacity=SHELF_CAPACITY,
        ),
    ]


def run_threshold_benchmark(
    *,
    model_path: Path,
    confidence_threshold: float,
    tracker: MLflowBenchmarkTracker,
) -> None:
    detector = YOLOStockDetector(
        model_path=str(model_path),
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
            "model": MODEL_NAME,
            "training": "pretrained",
            "confidence_threshold": confidence_threshold,
            "class_ids": str(BOTTLE_CLASS_ID),
            "device": "cpu",
            "shelf_capacity": SHELF_CAPACITY,
            "warmup_iterations": WARMUP_ITERATIONS,
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

    model_path = ensure_model()

    tracker = MLflowBenchmarkTracker(
        tracking_uri=settings.mlflow_tracking_uri,
        experiment_name=settings.mlflow_experiment_name,
    )

    for confidence_threshold in CONFIDENCE_THRESHOLDS:
        run_threshold_benchmark(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            tracker=tracker,
        )


if __name__ == "__main__":
    main()
