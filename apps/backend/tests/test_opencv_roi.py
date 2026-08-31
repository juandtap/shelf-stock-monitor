import numpy as np

from app.vision.models import RegionOfInterest
from app.vision.opencv_roi import OpenCVROIDetector


def create_empty_shelf() -> np.ndarray:
    return np.zeros(
        (100, 400, 3),
        dtype=np.uint8,
    )


def create_regions() -> list[RegionOfInterest]:
    return [
        RegionOfInterest(x=0, y=0, width=100, height=100),
        RegionOfInterest(x=100, y=0, width=100, height=100),
        RegionOfInterest(x=200, y=0, width=100, height=100),
        RegionOfInterest(x=300, y=0, width=100, height=100),
    ]


def test_detects_occupied_slots() -> None:
    empty_reference = create_empty_shelf()
    current_image = empty_reference.copy()

    current_image[:, 0:100] = 255
    current_image[:, 200:300] = 255

    detector = OpenCVROIDetector(
        empty_reference=empty_reference,
        regions=create_regions(),
        difference_threshold=30.0,
    )

    result = detector.detect(current_image)

    assert result.detected_units == 2
    assert result.shelf_capacity == 4
    assert result.detector_name == "opencv_roi"


def test_detects_empty_shelf() -> None:
    empty_reference = create_empty_shelf()

    detector = OpenCVROIDetector(
        empty_reference=empty_reference,
        regions=create_regions(),
        difference_threshold=30.0,
    )

    result = detector.detect(empty_reference.copy())

    assert result.detected_units == 0
    assert result.shelf_capacity == 4


def test_detects_full_shelf() -> None:
    empty_reference = create_empty_shelf()

    current_image = np.full(
        empty_reference.shape,
        255,
        dtype=np.uint8,
    )

    detector = OpenCVROIDetector(
        empty_reference=empty_reference,
        regions=create_regions(),
        difference_threshold=30.0,
    )

    result = detector.detect(current_image)

    assert result.detected_units == 4
    assert result.shelf_capacity == 4


def test_rejects_roi_outside_image() -> None:
    empty_reference = create_empty_shelf()

    regions = [
        RegionOfInterest(
            x=350,
            y=0,
            width=100,
            height=100,
        ),
    ]

    try:
        OpenCVROIDetector(
            empty_reference=empty_reference,
            regions=regions,
            difference_threshold=30.0,
        )
    except ValueError as error:
        assert str(error) == "ROI exceeds image width."
    else:
        raise AssertionError("Expected ValueError.")


def test_rejects_different_image_dimensions() -> None:
    empty_reference = create_empty_shelf()

    detector = OpenCVROIDetector(
        empty_reference=empty_reference,
        regions=create_regions(),
        difference_threshold=30.0,
    )

    different_image = np.zeros(
        (200, 400, 3),
        dtype=np.uint8,
    )

    try:
        detector.detect(different_image)
    except ValueError as error:
        assert str(error) == "Input image dimensions must match the empty reference image."
    else:
        raise AssertionError("Expected ValueError.")
