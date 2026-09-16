from pathlib import Path

from ultralytics import YOLO  # type: ignore[attr-defined]

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATASET_PATH = PROJECT_ROOT / "data" / "yolo" / "dataset.yaml"

MODEL_PATH = PROJECT_ROOT / "artifacts" / "models" / "yolo" / "yolo11n-synthetic-v1" / "best.pt"

IMAGE_SIZE = 640
DEVICE = "0"


def validate_inputs() -> None:
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(f"Dataset configuration not found: {DATASET_PATH}")

    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")


def main() -> None:
    validate_inputs()

    print()
    print("YOLO synthetic test evaluation")
    print("=" * 60)
    print(f"Dataset: {DATASET_PATH}")
    print(f"Model: {MODEL_PATH}")
    print(f"Image size: {IMAGE_SIZE}")
    print(f"Device: {DEVICE}")
    print()

    model = YOLO(str(MODEL_PATH))

    metrics = model.val(
        data=str(DATASET_PATH),
        split="test",
        imgsz=IMAGE_SIZE,
        device=DEVICE,
        plots=True,
        verbose=True,
    )

    print()
    print("Test results")
    print("=" * 60)
    print(f"Precision: {metrics.box.mp:.6f}")
    print(f"Recall: {metrics.box.mr:.6f}")
    print(f"mAP50: {metrics.box.map50:.6f}")
    print(f"mAP50-95: {metrics.box.map:.6f}")


if __name__ == "__main__":
    main()
