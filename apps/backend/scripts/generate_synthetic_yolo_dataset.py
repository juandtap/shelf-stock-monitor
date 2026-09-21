import random
import shutil
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from app.vision.shelf_geometry import (
    SYNTHETIC_SHELF_SLOTS,
    ShelfSlot,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ASSETS_DIRECTORY = PROJECT_ROOT / "data" / "synthetic" / "assets"
OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "yolo"

SHELF_PATH = ASSETS_DIRECTORY / "shelf_2x4.png"

PRODUCT_PATHS = {
    0: ASSETS_DIRECTORY / "coca_cola.png",
    1: ASSETS_DIRECTORY / "water.png",
    2: ASSETS_DIRECTORY / "shampoo.png",
}

CLASS_NAMES = {
    0: "coca_cola",
    1: "water",
    2: "shampoo",
}

TOTAL_IMAGES = 300
TRAIN_IMAGES = 210
VAL_IMAGES = 60
TEST_IMAGES = 30

RANDOM_SEED = 42

MIN_OCCUPIED_SLOTS = 0
MAX_OCCUPIED_SLOTS = len(SYNTHETIC_SHELF_SLOTS)

MIN_SCALE_FACTOR = 0.85
MAX_SCALE_FACTOR = 1.00

MAX_HORIZONTAL_OFFSET_RATIO = 0.10

BASE_WIDTH_USAGE = 0.52
BASE_HEIGHT_USAGE = 0.90

BOTTOM_MARGIN = 3

DIAGNOSTIC_IMAGES = 12

ImageArray = NDArray[np.uint8]


@dataclass(frozen=True)
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int


def load_image(
    path: Path,
    flags: int,
) -> ImageArray:
    image = cv2.imread(str(path), flags)

    if image is None:
        raise ValueError(f"Unable to read image: {path}")

    return image


def load_assets() -> tuple[
    ImageArray,
    dict[int, ImageArray],
]:
    shelf = load_image(
        SHELF_PATH,
        cv2.IMREAD_COLOR,
    )

    products: dict[int, ImageArray] = {}

    for class_id, path in PRODUCT_PATHS.items():
        product = load_image(
            path,
            cv2.IMREAD_UNCHANGED,
        )

        if product.ndim != 3 or product.shape[2] != 4:
            raise ValueError(f"Product must contain an alpha channel: {path}")

        products[class_id] = crop_to_visible_content(product)

    return shelf, products


def crop_to_visible_content(
    image: ImageArray,
) -> ImageArray:
    alpha = image[:, :, 3]

    visible_y, visible_x = np.where(alpha > 0)

    if visible_x.size == 0 or visible_y.size == 0:
        raise ValueError("Product contains no visible pixels.")

    x1 = int(visible_x.min())
    x2 = int(visible_x.max()) + 1
    y1 = int(visible_y.min())
    y2 = int(visible_y.max()) + 1

    return image[
        y1:y2,
        x1:x2,
    ]


def resize_product(
    product: ImageArray,
    slot: ShelfSlot,
    scale_factor: float,
) -> ImageArray:
    product_height, product_width = product.shape[:2]

    max_width = slot.width * BASE_WIDTH_USAGE
    max_height = slot.height * BASE_HEIGHT_USAGE

    base_scale = min(
        max_width / product_width,
        max_height / product_height,
    )

    scale = base_scale * scale_factor

    new_width = max(
        1,
        round(product_width * scale),
    )

    new_height = max(
        1,
        round(product_height * scale),
    )

    return cv2.resize(
        product,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA,
    )


def place_product(
    background: ImageArray,
    product: ImageArray,
    slot: ShelfSlot,
    rng: random.Random,
) -> BoundingBox:
    scale_factor = rng.uniform(
        MIN_SCALE_FACTOR,
        MAX_SCALE_FACTOR,
    )

    resized = resize_product(
        product,
        slot,
        scale_factor,
    )

    product_height, product_width = resized.shape[:2]

    centered_x = slot.x1 + ((slot.width - product_width) // 2)

    max_offset = round(slot.width * MAX_HORIZONTAL_OFFSET_RATIO)

    horizontal_offset = rng.randint(
        -max_offset,
        max_offset,
    )

    x1 = centered_x + horizontal_offset

    x1 = max(
        slot.x1,
        min(
            x1,
            slot.x2 - product_width,
        ),
    )

    x2 = x1 + product_width

    y2 = slot.y2 - BOTTOM_MARGIN
    y1 = y2 - product_height

    if y1 < slot.y1:
        raise ValueError("Product exceeds the vertical slot boundary.")

    foreground = resized[
        :,
        :,
        :3,
    ].astype(np.float32)

    alpha = (
        resized[
            :,
            :,
            3,
        ].astype(np.float32)
        / 255.0
    )[
        :,
        :,
        np.newaxis,
    ]

    region = background[
        y1:y2,
        x1:x2,
    ].astype(np.float32)

    blended = foreground * alpha + region * (1.0 - alpha)

    background[
        y1:y2,
        x1:x2,
    ] = np.clip(
        blended,
        0,
        255,
    ).astype(np.uint8)

    return BoundingBox(
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
    )


def to_yolo_label(
    class_id: int,
    box: BoundingBox,
    image_width: int,
    image_height: int,
) -> str:
    center_x = ((box.x1 + box.x2) / 2.0) / image_width

    center_y = ((box.y1 + box.y2) / 2.0) / image_height

    width = (box.x2 - box.x1) / image_width

    height = (box.y2 - box.y1) / image_height

    return f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}"


def draw_diagnostic_box(
    image: ImageArray,
    class_id: int,
    box: BoundingBox,
) -> None:
    color = (0, 0, 255)

    cv2.rectangle(
        image,
        (box.x1, box.y1),
        (box.x2, box.y2),
        color,
        2,
    )

    cv2.putText(
        image,
        CLASS_NAMES[class_id],
        (
            box.x1,
            max(
                20,
                box.y1 - 8,
            ),
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        2,
        cv2.LINE_AA,
    )


def generate_scene(
    shelf: ImageArray,
    products: dict[int, ImageArray],
    rng: random.Random,
) -> tuple[
    ImageArray,
    list[str],
    list[tuple[int, BoundingBox]],
]:
    scene = shelf.copy()

    occupied_count = rng.randint(
        MIN_OCCUPIED_SLOTS,
        MAX_OCCUPIED_SLOTS,
    )

    occupied_slots = set(
        rng.sample(
            range(len(SYNTHETIC_SHELF_SLOTS)),
            occupied_count,
        )
    )

    labels: list[str] = []
    annotations: list[tuple[int, BoundingBox]] = []

    image_height, image_width = scene.shape[:2]

    for slot_index, slot in enumerate(SYNTHETIC_SHELF_SLOTS):
        if slot_index not in occupied_slots:
            continue

        class_id = rng.choice(list(PRODUCT_PATHS.keys()))

        box = place_product(
            background=scene,
            product=products[class_id],
            slot=slot,
            rng=rng,
        )

        labels.append(
            to_yolo_label(
                class_id=class_id,
                box=box,
                image_width=image_width,
                image_height=image_height,
            )
        )

        annotations.append(
            (
                class_id,
                box,
            )
        )

    return scene, labels, annotations


def prepare_output_directory() -> None:
    if OUTPUT_DIRECTORY.exists():
        shutil.rmtree(OUTPUT_DIRECTORY)

    for split in (
        "train",
        "val",
        "test",
    ):
        (OUTPUT_DIRECTORY / "images" / split).mkdir(
            parents=True,
            exist_ok=True,
        )

        (OUTPUT_DIRECTORY / "labels" / split).mkdir(
            parents=True,
            exist_ok=True,
        )

    (OUTPUT_DIRECTORY / "diagnostics").mkdir(
        parents=True,
        exist_ok=True,
    )


def determine_split(
    index: int,
) -> str:
    if index < TRAIN_IMAGES:
        return "train"

    if index < TRAIN_IMAGES + VAL_IMAGES:
        return "val"

    return "test"


def write_dataset_yaml() -> None:
    dataset_root = OUTPUT_DIRECTORY.resolve()

    content = (
        f"path: {dataset_root}\n"
        "\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n"
        "\n"
        "names:\n"
        "  0: coca_cola\n"
        "  1: water\n"
        "  2: shampoo\n"
    )

    path = OUTPUT_DIRECTORY / "dataset.yaml"

    path.write_text(
        content,
        encoding="utf-8",
    )


def main() -> None:
    if TRAIN_IMAGES + VAL_IMAGES + TEST_IMAGES != TOTAL_IMAGES:
        raise ValueError("Dataset split counts must equal TOTAL_IMAGES.")

    rng = random.Random(RANDOM_SEED)

    shelf, products = load_assets()

    prepare_output_directory()

    total_objects = 0

    class_counts = {class_id: 0 for class_id in CLASS_NAMES}

    empty_images = 0

    for index in range(TOTAL_IMAGES):
        split = determine_split(index)

        scene, labels, annotations = generate_scene(
            shelf=shelf,
            products=products,
            rng=rng,
        )

        filename = f"shelf_{index:04d}"

        image_path = OUTPUT_DIRECTORY / "images" / split / f"{filename}.jpg"

        label_path = OUTPUT_DIRECTORY / "labels" / split / f"{filename}.txt"

        success = cv2.imwrite(
            str(image_path),
            scene,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                95,
            ],
        )

        if not success:
            raise RuntimeError(f"Unable to write image: {image_path}")

        label_path.write_text(
            "\n".join(labels),
            encoding="utf-8",
        )

        if not annotations:
            empty_images += 1

        for class_id, _ in annotations:
            total_objects += 1
            class_counts[class_id] += 1

        if index < DIAGNOSTIC_IMAGES:
            diagnostic = scene.copy()

            for class_id, box in annotations:
                draw_diagnostic_box(
                    diagnostic,
                    class_id,
                    box,
                )

            diagnostic_path = OUTPUT_DIRECTORY / "diagnostics" / f"{filename}.jpg"

            success = cv2.imwrite(
                str(diagnostic_path),
                diagnostic,
            )

            if not success:
                raise RuntimeError(f"Unable to write diagnostic image: {diagnostic_path}")

    write_dataset_yaml()

    print()
    print("Synthetic YOLO dataset generated")
    print("=" * 60)
    print(f"Seed: {RANDOM_SEED}")
    print(f"Total images: {TOTAL_IMAGES}")
    print(f"Train: {TRAIN_IMAGES}")
    print(f"Validation: {VAL_IMAGES}")
    print(f"Test: {TEST_IMAGES}")
    print(f"Empty images: {empty_images}")
    print(f"Total objects: {total_objects}")
    print()

    for (
        class_id,
        class_name,
    ) in CLASS_NAMES.items():
        print(f"{class_name:<12}: {class_counts[class_id]} objects")

    print()
    print(f"Dataset: {OUTPUT_DIRECTORY}")
    print(f"Diagnostics: {OUTPUT_DIRECTORY / 'diagnostics'}")


if __name__ == "__main__":
    main()
