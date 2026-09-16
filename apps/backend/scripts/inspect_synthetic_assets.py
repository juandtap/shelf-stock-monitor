from pathlib import Path

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ASSETS_DIRECTORY = PROJECT_ROOT / "data" / "synthetic" / "assets"

EXPECTED_ASSETS = (
    "shelf_2x4.png",
    "coca_cola.png",
    "water.png",
    "shampoo.png",
)


def inspect_asset(filename: str) -> None:
    path = ASSETS_DIRECTORY / filename

    if not path.is_file():
        print(f"{filename}")
        print("  ERROR: file not found")
        print(f"  path: {path}")
        return

    image = cv2.imread(
        str(path),
        cv2.IMREAD_UNCHANGED,
    )

    if image is None:
        print(f"{filename}")
        print("  ERROR: unable to read image")
        return

    height, width = image.shape[:2]

    channels = image.shape[2] if image.ndim == 3 else 1

    has_alpha = channels == 4

    print(filename)
    print(f"  width: {width}px")
    print(f"  height: {height}px")
    print(f"  channels: {channels}")
    print(f"  alpha: {has_alpha}")
    print(f"  dtype: {image.dtype}")

    if has_alpha:
        alpha_channel = image[:, :, 3]

        transparent_pixels = int((alpha_channel == 0).sum())

        total_pixels = alpha_channel.size

        transparent_percentage = (transparent_pixels / total_pixels) * 100.0

        print(f"  transparent pixels: {transparent_percentage:.2f}%")

    print()


def main() -> None:
    print()
    print("Synthetic dataset assets")
    print("=" * 50)
    print(f"Directory: {ASSETS_DIRECTORY}")
    print()

    for filename in EXPECTED_ASSETS:
        inspect_asset(filename)


if __name__ == "__main__":
    main()
