from pathlib import Path

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray

from app.benchmarking.models import BenchmarkSample
from app.benchmarking.runner import BenchmarkRunner
from app.vision.detector import ImageArray
from app.vision.models import StockDetectionResult


class FakeStockDetector:
    def __init__(
        self,
        *,
        detected_units: int,
        name: str = "fake_detector",
    ) -> None:
        self._detected_units = detected_units
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def detect(
        self,
        image: ImageArray,
    ) -> StockDetectionResult:
        return StockDetectionResult(
            detected_units=self._detected_units,
            detector_name=self._name,
        )


class SequenceStockDetector:
    def __init__(
        self,
        *,
        detections: list[int],
    ) -> None:
        self._detections = detections
        self._index = 0

    @property
    def name(self) -> str:
        return "sequence_detector"

    def detect(
        self,
        image: ImageArray,
    ) -> StockDetectionResult:
        detected_units = self._detections[self._index]

        self._index += 1

        return StockDetectionResult(
            detected_units=detected_units,
            detector_name=self.name,
        )


def create_test_image(
    path: Path,
) -> None:
    image: NDArray[np.uint8] = np.zeros(
        (20, 20, 3),
        dtype=np.uint8,
    )

    saved = cv2.imwrite(
        str(path),
        image,
    )

    if not saved:
        raise RuntimeError(f"Could not save test image: {path}")


def test_runner_calculates_zero_error_for_exact_detection(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "sample.png"

    create_test_image(
        image_path,
    )

    detector = FakeStockDetector(
        detected_units=2,
    )

    runner = BenchmarkRunner(
        detector=detector,
        samples_directory=tmp_path,
    )

    samples = [
        BenchmarkSample(
            filename="sample.png",
            expected_units=2,
            shelf_capacity=4,
        )
    ]

    results, summary = runner.run(
        samples=samples,
    )

    assert len(results) == 1

    result = results[0]

    assert result.expected_units == 2
    assert result.detected_units == 2
    assert result.expected_stock_percentage == 50.0
    assert result.detected_stock_percentage == 50.0
    assert result.absolute_units_error == 0
    assert result.absolute_stock_percentage_error == 0.0

    assert summary.detector_name == "fake_detector"
    assert summary.sample_count == 1
    assert summary.units_mae == 0.0
    assert summary.stock_percentage_mae == 0.0
    assert summary.latency_mean_ms >= 0.0
    assert summary.latency_p50_ms >= 0.0
    assert summary.latency_p95_ms >= 0.0


def test_runner_calculates_units_mae(
    tmp_path: Path,
) -> None:
    filenames = [
        "sample_1.png",
        "sample_2.png",
        "sample_3.png",
    ]

    for filename in filenames:
        create_test_image(
            tmp_path / filename,
        )

    detector = SequenceStockDetector(
        detections=[1, 1, 4],
    )

    runner = BenchmarkRunner(
        detector=detector,
        samples_directory=tmp_path,
    )

    samples = [
        BenchmarkSample(
            filename="sample_1.png",
            expected_units=0,
            shelf_capacity=4,
        ),
        BenchmarkSample(
            filename="sample_2.png",
            expected_units=2,
            shelf_capacity=4,
        ),
        BenchmarkSample(
            filename="sample_3.png",
            expected_units=4,
            shelf_capacity=4,
        ),
    ]

    _, summary = runner.run(
        samples=samples,
    )

    assert summary.units_mae == pytest.approx(
        2 / 3,
    )


def test_runner_calculates_stock_percentage_mae(
    tmp_path: Path,
) -> None:
    filenames = [
        "sample_1.png",
        "sample_2.png",
    ]

    for filename in filenames:
        create_test_image(
            tmp_path / filename,
        )

    detector = SequenceStockDetector(
        detections=[1, 4],
    )

    runner = BenchmarkRunner(
        detector=detector,
        samples_directory=tmp_path,
    )

    samples = [
        BenchmarkSample(
            filename="sample_1.png",
            expected_units=0,
            shelf_capacity=4,
        ),
        BenchmarkSample(
            filename="sample_2.png",
            expected_units=2,
            shelf_capacity=4,
        ),
    ]

    _, summary = runner.run(
        samples=samples,
    )

    assert summary.stock_percentage_mae == pytest.approx(
        37.5,
    )


def test_runner_rejects_empty_dataset(
    tmp_path: Path,
) -> None:
    detector = FakeStockDetector(
        detected_units=0,
    )

    runner = BenchmarkRunner(
        detector=detector,
        samples_directory=tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="samples cannot be empty",
    ):
        runner.run(
            samples=[],
        )


def test_runner_calculates_latency_percentiles(
    tmp_path: Path,
) -> None:
    filenames = [
        "sample_1.png",
        "sample_2.png",
        "sample_3.png",
    ]

    for filename in filenames:
        create_test_image(
            tmp_path / filename,
        )

    detector = SequenceStockDetector(
        detections=[0, 1, 2],
    )

    runner = BenchmarkRunner(
        detector=detector,
        samples_directory=tmp_path,
    )

    samples = [
        BenchmarkSample(
            filename=filename,
            expected_units=index,
            shelf_capacity=4,
        )
        for index, filename in enumerate(filenames)
    ]

    _, summary = runner.run(
        samples=samples,
    )

    assert summary.latency_mean_ms >= 0.0
    assert summary.latency_p50_ms >= 0.0
    assert summary.latency_p95_ms >= 0.0
    assert summary.latency_p95_ms >= summary.latency_p50_ms


def test_runner_works_with_stock_detector_protocol(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "sample.png"

    create_test_image(
        image_path,
    )

    detector = FakeStockDetector(
        detected_units=3,
        name="custom_detector",
    )

    runner = BenchmarkRunner(
        detector=detector,
        samples_directory=tmp_path,
    )

    samples = [
        BenchmarkSample(
            filename="sample.png",
            expected_units=3,
            shelf_capacity=4,
        )
    ]

    results, summary = runner.run(
        samples=samples,
    )

    assert results[0].detector_name == "custom_detector"
    assert summary.detector_name == "custom_detector"
