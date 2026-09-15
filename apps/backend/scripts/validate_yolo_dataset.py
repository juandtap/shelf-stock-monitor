from dataclasses import dataclass
from pathlib import Path

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET_DIRECTORY = PROJECT_ROOT / "data" / "yolo"

EXPECTED_SPLITS = {
    "train": 210,
    "val": 60,
    "test": 30,
}

VALID_CLASS_IDS = {0, 1, 2}

CLASS_NAMES = {
    0: "coca_cola",
    1: "water",
    2: "shampoo",
}

VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


@dataclass
class SplitStatistics:
    images: int = 0
    labels: int = 0
    objects: int = 0
    empty_images: int = 0


def validate_yolo_line(
    line: str,
    label_path: Path,
    line_number: int,
) -> int:
    parts = line.split()

    if len(parts) != 5:
        raise ValueError(
            f"{label_path}:{line_number}: "
            f"expected 5 values, found {len(parts)}"
        )

    try:
        class_id = int(parts[0])
    except ValueError as exc:
        raise ValueError(
            f"{label_path}:{line_number}: "
            f"invalid class id: {parts[0]}"
        ) from exc

    if class_id not in VALID_CLASS_IDS:
        raise ValueError(
            f"{label_path}:{line_number}: "
            f"unknown class id: {class_id}"
        )

    try:
        center_x, center_y, width, height = (
            float(value)
            for value in parts[1:]
        )
    except ValueError as exc:
        raise ValueError(
            f"{label_path}:{line_number}: "
            "bounding box contains non-numeric values"
        ) from exc

    if not 0.0 <= center_x <= 1.0:
        raise ValueError(
            f"{label_path}:{line_number}: "
            f"center_x outside [0, 1]: {center_x}"
        )

    if not 0.0 <= center_y <= 1.0:
        raise ValueError(
            f"{label_path}:{line_number}: "
            f"center_y outside [0, 1]: {center_y}"
        )

    if not 0.0 < width <= 1.0:
        raise ValueError(
            f"{label_path}:{line_number}: "
            f"width outside (0, 1]: {width}"
        )

    if not 0.0 < height <= 1.0:
        raise ValueError(
            f"{label_path}:{line_number}: "
            f"height outside (0, 1]: {height}"
        )

    x1 = center_x - (width / 2.0)
    y1 = center_y - (height / 2.0)
    x2 = center_x + (width / 2.0)
    y2 = center_y + (height / 2.0)

    tolerance = 1e-5

    if (
        x1 < -tolerance
        or y1 < -tolerance
        or x2 > 1.0 + tolerance
        or y2 > 1.0 + tolerance
    ):
        raise ValueError(
            f"{label_path}:{line_number}: "
            "bounding box extends outside image"
        )

    return class_id


def validate_image(
    image_path: Path,
) -> None:
    image = cv2.imread(
        str(image_path),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(
            f"Unable to read image: {image_path}"
        )

    height, width = image.shape[:2]

    if width <= 0 or height <= 0:
        raise ValueError(
            f"Invalid image dimensions: {image_path}"
        )


def get_images(
    directory: Path,
) -> list[Path]:
    return sorted(
        path
        for path in directory.iterdir()
        if (
            path.is_file()
            and path.suffix.lower()
            in VALID_IMAGE_EXTENSIONS
        )
    )


def validate_split(
    split: str,
    expected_images: int,
    class_counts: dict[int, int],
) -> SplitStatistics:
    image_directory = (
        DATASET_DIRECTORY
        / "images"
        / split
    )

    label_directory = (
        DATASET_DIRECTORY
        / "labels"
        / split
    )

    if not image_directory.is_dir():
        raise ValueError(
            f"Missing image directory: {image_directory}"
        )

    if not label_directory.is_dir():
        raise ValueError(
            f"Missing label directory: {label_directory}"
        )

    images = get_images(image_directory)

    labels = sorted(
        path
        for path in label_directory.glob("*.txt")
        if path.is_file()
    )

    if len(images) != expected_images:
        raise ValueError(
            f"{split}: expected {expected_images} images, "
            f"found {len(images)}"
        )

    if len(labels) != expected_images:
        raise ValueError(
            f"{split}: expected {expected_images} labels, "
            f"found {len(labels)}"
        )

    image_stems = {
        path.stem
        for path in images
    }

    label_stems = {
        path.stem
        for path in labels
    }

    missing_labels = image_stems - label_stems

    if missing_labels:
        raise ValueError(
            f"{split}: images without labels: "
            f"{sorted(missing_labels)}"
        )

    orphan_labels = label_stems - image_stems

    if orphan_labels:
        raise ValueError(
            f"{split}: labels without images: "
            f"{sorted(orphan_labels)}"
        )

    statistics = SplitStatistics(
        images=len(images),
        labels=len(labels),
    )

    for image_path in images:
        validate_image(image_path)

        label_path = (
            label_directory
            / f"{image_path.stem}.txt"
        )

        content = label_path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            statistics.empty_images += 1
            continue

        for line_number, line in enumerate(
            content.splitlines(),
            start=1,
        ):
            class_id = validate_yolo_line(
                line=line,
                label_path=label_path,
                line_number=line_number,
            )

            statistics.objects += 1
            class_counts[class_id] += 1

    return statistics


def validate_dataset_yaml() -> None:
    dataset_yaml = (
        DATASET_DIRECTORY
        / "dataset.yaml"
    )

    if not dataset_yaml.is_file():
        raise ValueError(
            f"Missing dataset.yaml: {dataset_yaml}"
        )


def main() -> None:
    if not DATASET_DIRECTORY.is_dir():
        raise ValueError(
            f"Dataset not found: {DATASET_DIRECTORY}"
        )

    validate_dataset_yaml()

    class_counts = {
        class_id: 0
        for class_id in VALID_CLASS_IDS
    }

    split_statistics: dict[
        str,
        SplitStatistics,
    ] = {}

    for split, expected_images in EXPECTED_SPLITS.items():
        split_statistics[split] = validate_split(
            split=split,
            expected_images=expected_images,
            class_counts=class_counts,
        )

    total_images = sum(
        statistics.images
        for statistics in split_statistics.values()
    )

    total_objects = sum(
        statistics.objects
        for statistics in split_statistics.values()
    )

    total_empty = sum(
        statistics.empty_images
        for statistics in split_statistics.values()
    )

    print()
    print("YOLO dataset validation")
    print("=" * 60)

    for split, statistics in split_statistics.items():
        print(
            f"{split:<6} "
            f"images={statistics.images:<3} "
            f"labels={statistics.labels:<3} "
            f"objects={statistics.objects:<4} "
            f"empty={statistics.empty_images}"
        )

    print()
    print(f"Total images: {total_images}")
    print(f"Total objects: {total_objects}")
    print(f"Empty images: {total_empty}")

    print()
    print("Objects per class")

    for class_id, class_name in CLASS_NAMES.items():
        print(
            f"{class_id} {class_name:<12}: "
            f"{class_counts[class_id]}"
        )

    print()
    print("Validation PASSED")


if __name__ == "__main__":
    main()