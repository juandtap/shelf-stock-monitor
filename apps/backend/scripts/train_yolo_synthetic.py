import os
from pathlib import Path
from time import perf_counter

import mlflow
import torch
from ultralytics import YOLO  # type: ignore[attr-defined]

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATASET_PATH = PROJECT_ROOT / "data" / "yolo" / "dataset.yaml"

RUNS_DIRECTORY = PROJECT_ROOT / "artifacts" / "training" / "yolo"
MLFLOW_DATABASE_PATH = PROJECT_ROOT / "artifacts" / "mlflow" / "mlflow.db"

BASE_MODEL = "yolo11n.pt"
RUN_NAME = "yolo11n-synthetic-v1"
MLFLOW_EXPERIMENT_NAME = "yolo-synthetic-training"

EPOCHS = 50
IMAGE_SIZE = 640
BATCH_SIZE = 8
PATIENCE = 10
RANDOM_SEED = 42
WORKERS = 4


def resolve_device() -> str:
    configured_device = os.getenv("YOLO_TRAIN_DEVICE")

    if configured_device:
        return configured_device

    return "cpu"


def validate_inputs() -> None:
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(f"Dataset configuration not found: {DATASET_PATH}")


def configure_mlflow() -> str:
    MLFLOW_DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tracking_uri = f"sqlite:///{MLFLOW_DATABASE_PATH}"

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    return tracking_uri


def print_training_configuration(
    device: str,
    tracking_uri: str,
) -> None:
    print()
    print("YOLO synthetic fine-tuning")
    print("=" * 60)
    print(f"Dataset: {DATASET_PATH}")
    print(f"Base model: {BASE_MODEL}")
    print(f"Run: {RUN_NAME}")
    print(f"Epochs: {EPOCHS}")
    print(f"Image size: {IMAGE_SIZE}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Patience: {PATIENCE}")
    print(f"Seed: {RANDOM_SEED}")
    print(f"Device: {device}")
    print(f"Training output: {RUNS_DIRECTORY}")
    print(f"MLflow: {tracking_uri}")
    print()


def main() -> None:
    validate_inputs()

    device = resolve_device()
    tracking_uri = configure_mlflow()

    print_training_configuration(
        device=device,
        tracking_uri=tracking_uri,
    )

    model = YOLO(BASE_MODEL)

    started_at = perf_counter()

    with mlflow.start_run(run_name=RUN_NAME):
        mlflow.log_params(
            {
                "base_model": BASE_MODEL,
                "dataset": "synthetic-v1",
                "epochs": EPOCHS,
                "image_size": IMAGE_SIZE,
                "batch_size": BATCH_SIZE,
                "patience": PATIENCE,
                "seed": RANDOM_SEED,
                "workers": WORKERS,
                "device": device,
                "torch_version": torch.__version__,
            }
        )

        model.train(
            data=str(DATASET_PATH),
            epochs=EPOCHS,
            imgsz=IMAGE_SIZE,
            batch=BATCH_SIZE,
            patience=PATIENCE,
            device=device,
            workers=WORKERS,
            seed=RANDOM_SEED,
            deterministic=True,
            project=str(RUNS_DIRECTORY),
            name=RUN_NAME,
            exist_ok=False,
            pretrained=True,
            plots=True,
            verbose=True,
        )

        training_seconds = perf_counter() - started_at

        trainer = model.trainer

        if trainer is None:
            raise RuntimeError("Ultralytics trainer was not created.")

        run_directory = Path(trainer.save_dir)

        best_model_path = run_directory / "weights" / "best.pt"

        last_model_path = run_directory / "weights" / "last.pt"

        if not best_model_path.is_file():
            raise FileNotFoundError(f"best.pt was not found: {best_model_path}")

        mlflow.log_metric(
            "training_seconds",
            training_seconds,
        )

        mlflow.log_artifact(
            str(best_model_path),
            artifact_path="model",
        )

        print()
        print("Training finished")
        print("=" * 60)
        print(f"Run directory: {run_directory}")
        print(f"Best model: {best_model_path}")
        print(f"Last model: {last_model_path}")
        print(f"Training time: {training_seconds:.2f} seconds")
        print("best.pt: OK")


if __name__ == "__main__":
    main()
