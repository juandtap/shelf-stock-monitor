import os
from pathlib import Path

import torch
from ultralytics import YOLO  # type: ignore[attr-defined]


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "dataset.yaml"
)

RUNS_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "runs"
)

BASE_MODEL = "yolo11n.pt"

RUN_NAME = "yolo11n-synthetic-v1"

EPOCHS = 50
IMAGE_SIZE = 640
BATCH_SIZE = 8
PATIENCE = 10
RANDOM_SEED = 42
WORKERS = 4


def resolve_device() -> str:
    configured_device = os.getenv(
        "YOLO_TRAIN_DEVICE"
    )

    if configured_device:
        return configured_device

    return "cpu"


def validate_inputs() -> None:
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(
            f"Dataset configuration not found: {DATASET_PATH}"
        )


def print_training_configuration(
    device: str,
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
    print(f"Output: {RUNS_DIRECTORY}")
    print()


def main() -> None:
    validate_inputs()

    device = resolve_device()

    print_training_configuration(
        device=device,
    )

    model = YOLO(BASE_MODEL)

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

    trainer = model.trainer

    if trainer is None:
        raise RuntimeError(
            "Ultralytics trainer was not created."
        )

    run_directory = Path(trainer.save_dir)

    best_model_path = (
        run_directory
        / "weights"
        / "best.pt"
    )

    last_model_path = (
        run_directory
        / "weights"
        / "last.pt"
    )

    print()
    print("Training finished")
    print("=" * 60)
    print(f"Run directory: {run_directory}")
    print(f"Best model: {best_model_path}")
    print(f"Last model: {last_model_path}")

    if not best_model_path.is_file():
        raise FileNotFoundError(
            f"best.pt was not found: {best_model_path}"
        )

    print("best.pt: OK")


if __name__ == "__main__":
    main()