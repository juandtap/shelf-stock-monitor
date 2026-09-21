import numpy as np

from app.vision.models import (
    RegionOfInterest,
)
from app.vision.opencv_normalized_roi import (
    OpenCVNormalizedROIDetector,
)


def create_reference_shelf() -> np.ndarray:
    gradient = np.linspace(
        40,
        180,
        400,
        dtype=np.uint8,
    )

    grayscale = np.tile(
        gradient,
        (100, 1),
    )

    return np.stack(
        [
            grayscale,
            grayscale,
            grayscale,
        ],
        axis=2,
    )


def create_regions() -> list[RegionOfInterest]:
    return [
        RegionOfInterest(
            x=0,
            y=0,
            width=100,
            height=100,
        ),
        RegionOfInterest(
            x=100,
            y=0,
            width=100,
            height=100,
        ),
        RegionOfInterest(
            x=200,
            y=0,
            width=100,
            height=100,
        ),
        RegionOfInterest(
            x=300,
            y=0,
            width=100,
            height=100,
        ),
    ]


def test_detects_structural_change() -> None:
    empty_reference = create_reference_shelf()

    current_image = empty_reference.copy()

    current_image[
        20:80,
        120:180,
    ] = 255

    detector = OpenCVNormalizedROIDetector(
        empty_reference=(empty_reference),
        regions=create_regions(),
        difference_threshold=10.0,
    )

    result = detector.detect(current_image)

    assert result.detected_units == 1
    assert result.detector_name == "opencv_roi_normalized"


def test_detects_empty_shelf() -> None:
    empty_reference = create_reference_shelf()

    detector = OpenCVNormalizedROIDetector(
        empty_reference=(empty_reference),
        regions=create_regions(),
        difference_threshold=10.0,
    )

    result = detector.detect(empty_reference.copy())

    assert result.detected_units == 0


def test_is_robust_to_global_brightness_change() -> None:
    empty_reference = create_reference_shelf()

    brighter = np.clip(
        empty_reference.astype(np.float32) * 1.20 + 10.0,
        0,
        255,
    ).astype(np.uint8)

    detector = OpenCVNormalizedROIDetector(
        empty_reference=(empty_reference),
        regions=create_regions(),
        difference_threshold=10.0,
    )

    result = detector.detect(brighter)

    assert result.detected_units == 0


def test_scores_regions() -> None:
    empty_reference = create_reference_shelf()

    current_image = empty_reference.copy()

    current_image[
        20:80,
        220:280,
    ] = 255

    detector = OpenCVNormalizedROIDetector(
        empty_reference=(empty_reference),
        regions=create_regions(),
        difference_threshold=10.0,
    )

    scores = detector.score_regions(current_image)

    assert len(scores) == 4
    assert scores[2] > scores[0]
    assert scores[2] > scores[1]
    assert scores[2] > scores[3]


def test_rejects_roi_outside_image() -> None:
    empty_reference = create_reference_shelf()

    regions = [
        RegionOfInterest(
            x=350,
            y=0,
            width=100,
            height=100,
        ),
    ]

    try:
        OpenCVNormalizedROIDetector(
            empty_reference=(empty_reference),
            regions=regions,
            difference_threshold=10.0,
        )
    except ValueError as error:
        assert str(error) == "ROI exceeds image width."
    else:
        raise AssertionError("Expected ValueError.")


def test_rejects_different_image_dimensions() -> None:
    empty_reference = create_reference_shelf()

    detector = OpenCVNormalizedROIDetector(
        empty_reference=(empty_reference),
        regions=create_regions(),
        difference_threshold=10.0,
    )

    different_image = np.zeros(
        (200, 400, 3),
        dtype=np.uint8,
    )

    try:
        detector.detect(different_image)
    except ValueError as error:
        assert str(error) == ("Input image dimensions must match the empty reference image.")
    else:
        raise AssertionError("Expected ValueError.")


def test_rejects_negative_threshold() -> None:
    try:
        OpenCVNormalizedROIDetector(
            empty_reference=(create_reference_shelf()),
            regions=create_regions(),
            difference_threshold=-1.0,
        )
    except ValueError as error:
        assert str(error) == ("difference_threshold cannot be negative.")
    else:
        raise AssertionError("Expected ValueError.")
