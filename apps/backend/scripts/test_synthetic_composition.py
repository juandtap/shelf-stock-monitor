from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ASSETS_DIRECTORY = PROJECT_ROOT / "data" / "synthetic" / "assets"
OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "synthetic" / "diagnostics"

SHELF_PATH = ASSETS_DIRECTORY / "shelf_2x4.png"

PRODUCT_PATHS = {
    "coca_cola": ASSETS_DIRECTORY / "coca_cola.png",
    "water": ASSETS_DIRECTORY / "water.png",
    "shampoo": ASSETS_DIRECTORY / "shampoo.png",
}

OUTPUT_PATH = OUTPUT_DIRECTORY / "composition_test.png"

ImageArray = NDArray[np.uint8]


@dataclass(frozen=True)
class Slot:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1


@dataclass(frozen=True)
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int


SLOTS = (
    Slot(135, 100, 495, 385),
    Slot(535, 100, 860, 385),
    Slot(870, 100, 1235, 385),
    Slot(1240, 100, 1590, 385),
    Slot(135, 460, 495, 685),
    Slot(535, 460, 860, 685),
    Slot(870, 460, 1235, 685),
    Slot(1240, 460, 1590, 685),
)

# Deliberadamente mezclamos formas y tamaños.
SLOT_PRODUCTS = (
    "coca_cola",
    "water",
    "shampoo",
    "coca_cola",
    "water",
    "shampoo",
    "coca_cola",
    "water",
)

WIDTH_USAGE = 0.52
HEIGHT_USAGE = 0.90
BOTTOM_MARGIN = 3


def load_shelf(path: Path) -> ImageArray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError(f"Unable to read shelf image: {path}")

    return image


def load_product(path: Path) -> ImageArray:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)

    if image is None:
        raise ValueError(f"Unable to read product image: {path}")

    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"Product image must contain an alpha channel: {path}")

    return image


def crop_to_visible_content(image: ImageArray) -> ImageArray:
    alpha = image[:, :, 3]

    visible_y, visible_x = np.where(alpha > 0)

    if visible_x.size == 0 or visible_y.size == 0:
        raise ValueError("Product image contains no visible pixels.")

    x1 = int(visible_x.min())
    x2 = int(visible_x.max()) + 1
    y1 = int(visible_y.min())
    y2 = int(visible_y.max()) + 1

    return image[y1:y2, x1:x2]


def resize_product(
    product: ImageArray,
    slot: Slot,
) -> ImageArray:
    product_height, product_width = product.shape[:2]

    max_width = slot.width * WIDTH_USAGE
    max_height = slot.height * HEIGHT_USAGE

    scale = min(
        max_width / product_width,
        max_height / product_height,
    )

    new_width = max(1, round(product_width * scale))
    new_height = max(1, round(product_height * scale))

    return cv2.resize(
        product,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA,
    )


def place_product(
    background: ImageArray,
    product: ImageArray,
    slot: Slot,
) -> BoundingBox:
    product = crop_to_visible_content(product)
    product = resize_product(product, slot)

    product_height, product_width = product.shape[:2]

    x1 = slot.x1 + ((slot.width - product_width) // 2)
    y2 = slot.y2 - BOTTOM_MARGIN
    y1 = y2 - product_height
    x2 = x1 + product_width

    if x1 < 0 or y1 < 0 or x2 > background.shape[1] or y2 > background.shape[0]:
        raise ValueError("Product placement exceeds image boundaries.")

    foreground = product[:, :, :3].astype(np.float32)
    alpha = (product[:, :, 3].astype(np.float32) / 255.0)[:, :, np.newaxis]

    region = background[y1:y2, x1:x2].astype(np.float32)

    blended = foreground * alpha + region * (1.0 - alpha)

    background[y1:y2, x1:x2] = np.clip(
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


def draw_bounding_box(
    image: ImageArray,
    bounding_box: BoundingBox,
    label: str,
) -> None:
    color = (0, 0, 255)

    cv2.rectangle(
        image,
        (bounding_box.x1, bounding_box.y1),
        (bounding_box.x2, bounding_box.y2),
        color,
        2,
    )

    cv2.putText(
        image,
        label,
        (
            bounding_box.x1,
            max(20, bounding_box.y1 - 8),
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        color,
        2,
        cv2.LINE_AA,
    )


def main() -> None:
    shelf = load_shelf(SHELF_PATH)

    products = {name: load_product(path) for name, path in PRODUCT_PATHS.items()}

    bounding_boxes: list[tuple[str, BoundingBox]] = []

    for slot_index, (slot, product_name) in enumerate(zip(SLOTS, SLOT_PRODUCTS, strict=True)):
        bounding_box = place_product(
            background=shelf,
            product=products[product_name],
            slot=slot,
        )

        bounding_boxes.append((product_name, bounding_box))

        draw_bounding_box(
            shelf,
            bounding_box,
            f"{slot_index}: {product_name}",
        )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    success = cv2.imwrite(
        str(OUTPUT_PATH),
        shelf,
    )

    if not success:
        raise RuntimeError(f"Unable to write output image: {OUTPUT_PATH}")

    print()
    print("Synthetic composition test")
    print("=" * 60)

    for slot_index, (product_name, box) in enumerate(bounding_boxes):
        print(
            f"slot={slot_index} "
            f"product={product_name:<10} "
            f"bbox=({box.x1}, {box.y1}) "
            f"({box.x2}, {box.y2})"
        )

    print()
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
