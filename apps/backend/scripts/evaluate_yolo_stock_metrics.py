from collections import Counter
from pathlib import Path

import numpy as np
from ultralytics import YOLO  # type: ignore[attr-defined]

PROJECT_ROOT = Path(__file__).resolve().parents[3]

TEST_IMAGES_DIRECTORY = PROJECT_ROOT / "data" / "yolo" / "images" / "test"

TEST_LABELS_DIRECTORY = PROJECT_ROOT / "data" / "yolo" / "labels" / "test"

MODEL_PATH = PROJECT_ROOT / "artifacts" / "models" / "yolo" / "yolo11n-synthetic-v1" / "best.pt"

CLASS_NAMES = {
    0: "coca_cola",
    1: "water",
    2: "shampoo",
}

IMAGE_SIZE = 640
CONFIDENCE_THRESHOLD = 0.25
IOU_THRESHOLD = 0.70
DEVICE = "0"


def validate_inputs() -> None:
    if not TEST_IMAGES_DIRECTORY.is_dir():
        raise FileNotFoundError(f"Test images not found: {TEST_IMAGES_DIRECTORY}")

    if not TEST_LABELS_DIRECTORY.is_dir():
        raise FileNotFoundError(f"Test labels not found: {TEST_LABELS_DIRECTORY}")

    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")


def read_expected_counts(
    label_path: Path,
) -> Counter[int]:
    counts: Counter[int] = Counter()

    content = label_path.read_text(encoding="utf-8").strip()

    if not content:
        return counts

    for line in content.splitlines():
        fields = line.split()

        if len(fields) != 5:
            raise ValueError(f"Invalid YOLO label in {label_path}: {line}")

        class_id = int(fields[0])

        if class_id not in CLASS_NAMES:
            raise ValueError(f"Unknown class {class_id} in {label_path}")

        counts[class_id] += 1

    return counts


def main() -> None:
    validate_inputs()

    model = YOLO(str(MODEL_PATH))

    image_paths = sorted(TEST_IMAGES_DIRECTORY.glob("*.jpg"))

    if not image_paths:
        raise RuntimeError("No test images found.")

    total_absolute_error = 0
    exact_scenes = 0

    class_absolute_errors = {class_id: 0 for class_id in CLASS_NAMES}

    class_expected_totals = {class_id: 0 for class_id in CLASS_NAMES}

    print()
    print("YOLO stock-count test evaluation")
    print("=" * 80)
    print(
        "image".ljust(18),
        "expected".rjust(10),
        "predicted".rjust(11),
        "abs_error".rjust(11),
    )
    print("-" * 80)

    for image_path in image_paths:
        label_path = TEST_LABELS_DIRECTORY / f"{image_path.stem}.txt"

        if not label_path.is_file():
            raise FileNotFoundError(f"Label not found: {label_path}")

        expected_counts = read_expected_counts(label_path)

        results = model.predict(
            source=str(image_path),
            imgsz=IMAGE_SIZE,
            conf=CONFIDENCE_THRESHOLD,
            iou=IOU_THRESHOLD,
            device=DEVICE,
            verbose=False,
        )

        if len(results) != 1:
            raise RuntimeError(f"Expected one result for {image_path}")

        boxes = results[0].boxes

        predicted_counts: Counter[int] = Counter()

        if boxes is not None and boxes.cls is not None:
            class_ids = boxes.cls.detach().cpu().numpy().astype(np.int64)

            predicted_counts.update(int(class_id) for class_id in class_ids)

        expected_units = sum(expected_counts.values())

        predicted_units = sum(predicted_counts.values())

        absolute_error = abs(expected_units - predicted_units)

        total_absolute_error += absolute_error

        if absolute_error == 0:
            exact_scenes += 1

        for class_id in CLASS_NAMES:
            expected = expected_counts[class_id]
            predicted = predicted_counts[class_id]

            class_expected_totals[class_id] += expected
            class_absolute_errors[class_id] += abs(expected - predicted)

        print(
            image_path.name.ljust(18),
            str(expected_units).rjust(10),
            str(predicted_units).rjust(11),
            str(absolute_error).rjust(11),
        )

    image_count = len(image_paths)

    units_mae = total_absolute_error / image_count

    exact_scene_accuracy = exact_scenes / image_count * 100.0

    print()
    print("Overall stock metrics")
    print("=" * 80)
    print(f"Images: {image_count}")
    print(f"Units MAE: {units_mae:.6f}")
    print(f"Exact-count scenes: {exact_scenes}/{image_count} ({exact_scene_accuracy:.2f}%)")

    print()
    print("Per-class count metrics")
    print("=" * 80)

    for class_id, class_name in CLASS_NAMES.items():
        class_mae = class_absolute_errors[class_id] / image_count

        print(f"{class_name:<12} expected={class_expected_totals[class_id]:>3} MAE={class_mae:.6f}")


if __name__ == "__main__":
    main()
