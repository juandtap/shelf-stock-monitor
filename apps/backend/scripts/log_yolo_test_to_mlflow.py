from pathlib import Path

import mlflow

from app.core.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]

MODEL_PATH = PROJECT_ROOT / "artifacts" / "models" / "yolo" / "yolo11n-synthetic-v1" / "best.pt"

RUN_NAME = "yolo11n-finetuned-synthetic-v1-test"

TEST_IMAGES = 30
TEST_OBJECTS = 122

PRECISION = 0.998654
RECALL = 1.0
MAP50 = 0.995
MAP50_95 = 0.995

UNITS_MAE = 0.0
EXACT_COUNT_ACCURACY = 1.0

COCA_COLA_COUNT_MAE = 0.0
WATER_COUNT_MAE = 0.0
SHAMPOO_COUNT_MAE = 0.0

CONFIDENCE_THRESHOLD = 0.25
IOU_THRESHOLD = 0.70
IMAGE_SIZE = 640
SHELF_CAPACITY = 8


def validate_inputs() -> None:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")


def main() -> None:
    validate_inputs()

    settings = get_settings()

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

    mlflow.set_experiment(settings.mlflow_experiment_name)

    with mlflow.start_run(
        run_name=RUN_NAME,
    ) as run:
        mlflow.log_params(
            {
                "detector": "yolo",
                "model": "yolo11n",
                "training": "fine_tuned",
                "dataset": "synthetic-v1",
                "evaluation_split": "test",
                "test_images": TEST_IMAGES,
                "test_objects": TEST_OBJECTS,
                "confidence_threshold": CONFIDENCE_THRESHOLD,
                "iou_threshold": IOU_THRESHOLD,
                "image_size": IMAGE_SIZE,
                "shelf_capacity": SHELF_CAPACITY,
            }
        )

        mlflow.log_metrics(
            {
                "precision": PRECISION,
                "recall": RECALL,
                "map50": MAP50,
                "map50_95": MAP50_95,
                "units_mae": UNITS_MAE,
                "exact_count_accuracy": EXACT_COUNT_ACCURACY,
                "coca_cola_count_mae": COCA_COLA_COUNT_MAE,
                "water_count_mae": WATER_COUNT_MAE,
                "shampoo_count_mae": SHAMPOO_COUNT_MAE,
            }
        )

        mlflow.log_artifact(
            str(MODEL_PATH),
            artifact_path="model",
        )

        print()
        print("MLflow evaluation logged")
        print("=" * 60)
        print(f"Tracking URI: {settings.mlflow_tracking_uri}")
        print(f"Experiment: {settings.mlflow_experiment_name}")
        print(f"Run: {RUN_NAME}")
        print(f"Run ID: {run.info.run_id}")
        print(f"Model artifact: {MODEL_PATH}")


if __name__ == "__main__":
    main()
