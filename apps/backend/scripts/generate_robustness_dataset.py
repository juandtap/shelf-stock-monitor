import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import cv2
import numpy as np
from numpy.typing import NDArray

PROJECT_ROOT = Path(__file__).resolve().parents[3]

SOURCE_DATASET_DIRECTORY = PROJECT_ROOT / "data" / "yolo"

OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "robustness" / "synthetic-v1"

DATASET_SPLITS = (
    "val",
    "test",
)

RANDOM_SEED = 2026

ImageArray = NDArray[np.uint8]
Transform = Callable[
    [ImageArray, np.random.Generator],
    ImageArray,
]


@dataclass(frozen=True)
class RobustnessScenario:
    name: str
    transform: Transform | None
    description: str


def load_image(
    path: Path,
) -> ImageArray:
    image = cv2.imread(
        str(path),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(f"Unable to read image: {path}")

    return cast(
        ImageArray,
        image,
    )


def brightness_low(
    image: ImageArray,
    rng: np.random.Generator,
) -> ImageArray:
    del rng

    transformed = cv2.convertScaleAbs(
        image,
        alpha=0.65,
        beta=0.0,
    )

    return cast(
        ImageArray,
        transformed,
    )


def brightness_high(
    image: ImageArray,
    rng: np.random.Generator,
) -> ImageArray:
    del rng

    transformed = cv2.convertScaleAbs(
        image,
        alpha=1.25,
        beta=15.0,
    )

    return cast(
        ImageArray,
        transformed,
    )


def contrast_low(
    image: ImageArray,
    rng: np.random.Generator,
) -> ImageArray:
    del rng

    image_float = image.astype(np.float32)

    mean = np.mean(
        image_float,
        axis=(0, 1),
        keepdims=True,
    )

    transformed = mean + 0.55 * (image_float - mean)

    transformed_uint8 = np.clip(
        transformed,
        0,
        255,
    ).astype(np.uint8)

    return cast(
        ImageArray,
        transformed_uint8,
    )


def gaussian_noise(
    image: ImageArray,
    rng: np.random.Generator,
) -> ImageArray:
    noise = rng.normal(
        loc=0.0,
        scale=12.0,
        size=image.shape,
    ).astype(np.float32)

    transformed = image.astype(np.float32) + noise

    transformed_uint8 = np.clip(
        transformed,
        0,
        255,
    ).astype(np.uint8)

    return cast(
        ImageArray,
        transformed_uint8,
    )


def blur(
    image: ImageArray,
    rng: np.random.Generator,
) -> ImageArray:
    del rng

    transformed = cv2.GaussianBlur(
        image,
        (9, 9),
        sigmaX=0.0,
    )

    return cast(
        ImageArray,
        transformed,
    )


SCENARIOS = (
    RobustnessScenario(
        name="baseline",
        transform=None,
        description="Exact copy of frozen source image",
    ),
    RobustnessScenario(
        name="brightness_low",
        transform=brightness_low,
        description=("Brightness scaling alpha=0.65"),
    ),
    RobustnessScenario(
        name="brightness_high",
        transform=brightness_high,
        description=("Brightness alpha=1.25 beta=15"),
    ),
    RobustnessScenario(
        name="contrast_low",
        transform=contrast_low,
        description=("Contrast compressed to 55% around image mean"),
    ),
    RobustnessScenario(
        name="gaussian_noise",
        transform=gaussian_noise,
        description=("Gaussian noise sigma=12"),
    ),
    RobustnessScenario(
        name="blur",
        transform=blur,
        description=("Gaussian blur kernel=9x9"),
    ),
)


def get_source_images_directory(
    split: str,
) -> Path:
    return SOURCE_DATASET_DIRECTORY / "images" / split


def get_source_labels_directory(
    split: str,
) -> Path:
    return SOURCE_DATASET_DIRECTORY / "labels" / split


def validate_source_split(
    split: str,
) -> list[Path]:
    images_directory = get_source_images_directory(split)

    labels_directory = get_source_labels_directory(split)

    if not images_directory.is_dir():
        raise FileNotFoundError(f"Source images not found: {images_directory}")

    if not labels_directory.is_dir():
        raise FileNotFoundError(f"Source labels not found: {labels_directory}")

    image_paths = sorted(images_directory.glob("*.jpg"))

    if not image_paths:
        raise ValueError(f"No source images found for split: {split}")

    for image_path in image_paths:
        label_path = labels_directory / f"{image_path.stem}.txt"

        if not label_path.is_file():
            raise FileNotFoundError(f"Missing label for image: {image_path.name}")

    return image_paths


def prepare_output_directory() -> None:
    if OUTPUT_DIRECTORY.exists():
        shutil.rmtree(OUTPUT_DIRECTORY)

    for split in DATASET_SPLITS:
        for scenario in SCENARIOS:
            (OUTPUT_DIRECTORY / split / scenario.name / "images").mkdir(
                parents=True,
                exist_ok=True,
            )

            (OUTPUT_DIRECTORY / split / scenario.name / "labels").mkdir(
                parents=True,
                exist_ok=True,
            )


def write_image(
    *,
    path: Path,
    image: ImageArray,
) -> None:
    success = cv2.imwrite(
        str(path),
        image,
        [
            cv2.IMWRITE_JPEG_QUALITY,
            95,
        ],
    )

    if not success:
        raise RuntimeError(f"Unable to write image: {path}")


def generate_scenario(
    *,
    split: str,
    scenario: RobustnessScenario,
    image_paths: list[Path],
    scenario_index: int,
    split_index: int,
) -> None:
    images_output = OUTPUT_DIRECTORY / split / scenario.name / "images"

    labels_output = OUTPUT_DIRECTORY / split / scenario.name / "labels"

    source_labels_directory = get_source_labels_directory(split)

    for image_index, image_path in enumerate(image_paths):
        output_image_path = images_output / image_path.name

        if scenario.transform is None:
            shutil.copy2(
                image_path,
                output_image_path,
            )
        else:
            image = load_image(image_path)

            seed = RANDOM_SEED + split_index * 100_000 + scenario_index * 10_000 + image_index

            rng = np.random.default_rng(seed)

            transformed = scenario.transform(
                image,
                rng,
            )

            write_image(
                path=output_image_path,
                image=transformed,
            )

        source_label_path = source_labels_directory / f"{image_path.stem}.txt"

        output_label_path = labels_output / source_label_path.name

        shutil.copy2(
            source_label_path,
            output_label_path,
        )


def main() -> None:
    source_images: dict[
        str,
        list[Path],
    ] = {}

    for split in DATASET_SPLITS:
        source_images[split] = validate_source_split(split)

    prepare_output_directory()

    print()
    print("Generating robustness dataset")
    print("=" * 70)
    print(f"Random seed: {RANDOM_SEED}")
    print()

    total_images = 0

    for split_index, split in enumerate(DATASET_SPLITS):
        image_paths = source_images[split]

        print(f"Split: {split}")
        print(f"Source images: {len(image_paths)}")

        for (
            scenario_index,
            scenario,
        ) in enumerate(SCENARIOS):
            generate_scenario(
                split=split,
                scenario=scenario,
                image_paths=image_paths,
                scenario_index=(scenario_index),
                split_index=split_index,
            )

            generated_count = len(image_paths)

            total_images += generated_count

            print(f"{scenario.name:<20} {generated_count:>3} images  {scenario.description}")

        print()

    print(f"Splits: {len(DATASET_SPLITS)}")
    print(f"Scenarios per split: {len(SCENARIOS)}")
    print(f"Generated images: {total_images}")
    print(f"Output: {OUTPUT_DIRECTORY}")


if __name__ == "__main__":
    main()
