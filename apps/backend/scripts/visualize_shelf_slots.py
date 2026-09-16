from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

PROJECT_ROOT = Path(__file__).resolve().parents[3]

SHELF_IMAGE_PATH = PROJECT_ROOT / "data" / "synthetic" / "assets" / "shelf_2x4.png"

OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "synthetic" / "diagnostics"

OUTPUT_IMAGE_PATH = OUTPUT_DIRECTORY / "shelf_2x4_grid.png"

ROWS = 2
COLUMNS = 4


ImageArray = NDArray[np.uint8]


def load_image(path: Path) -> ImageArray:
    image = cv2.imread(
        str(path),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(f"Unable to read image: {path}")

    return image


def draw_grid(
    image: ImageArray,
) -> ImageArray:
    output = image.copy()

    height, width = output.shape[:2]

    slot_width = width / COLUMNS
    slot_height = height / ROWS

    line_color = (0, 0, 255)
    text_color = (0, 0, 255)

    for column in range(1, COLUMNS):
        x = round(column * slot_width)

        cv2.line(
            output,
            (x, 0),
            (x, height - 1),
            line_color,
            3,
        )

    for row in range(1, ROWS):
        y = round(row * slot_height)

        cv2.line(
            output,
            (0, y),
            (width - 1, y),
            line_color,
            3,
        )

    slot_index = 0

    for row in range(ROWS):
        for column in range(COLUMNS):
            x1 = round(column * slot_width)
            y1 = round(row * slot_height)

            x2 = round((column + 1) * slot_width)
            y2 = round((row + 1) * slot_height)

            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            label = f"SLOT {slot_index}"

            cv2.putText(
                output,
                label,
                (
                    center_x - 75,
                    center_y,
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                text_color,
                3,
                cv2.LINE_AA,
            )

            cv2.putText(
                output,
                f"({x1},{y1})",
                (
                    x1 + 10,
                    y1 + 30,
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                text_color,
                2,
                cv2.LINE_AA,
            )

            cv2.putText(
                output,
                f"({x2},{y2})",
                (
                    max(x1 + 10, x2 - 125),
                    max(y1 + 55, y2 - 15),
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                text_color,
                2,
                cv2.LINE_AA,
            )

            slot_index += 1

    return output


def main() -> None:
    image = load_image(SHELF_IMAGE_PATH)

    diagnostic_image = draw_grid(image)

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    success = cv2.imwrite(
        str(OUTPUT_IMAGE_PATH),
        diagnostic_image,
    )

    if not success:
        raise RuntimeError("Unable to write diagnostic image.")

    height, width = image.shape[:2]

    print()
    print("Shelf slot diagnostic")
    print("=" * 50)
    print(f"Image: {SHELF_IMAGE_PATH}")
    print(f"Resolution: {width}x{height}")
    print(f"Grid: {ROWS} rows x {COLUMNS} columns")
    print(f"Approximate slot size: {width / COLUMNS:.2f}x{height / ROWS:.2f}px")
    print(f"Output: {OUTPUT_IMAGE_PATH}")


if __name__ == "__main__":
    main()
