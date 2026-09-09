from pathlib import Path
from time import perf_counter
from typing import cast

import cv2
import numpy as np

from app.benchmarking.models import (
    BenchmarkResult,
    BenchmarkSample,
    BenchmarkSummary,
)
from app.vision.detector import ImageArray, StockDetector


class BenchmarkImageNotFoundError(Exception):
    pass


class InvalidBenchmarkImageError(Exception):
    pass


def load_benchmark_image(
    path: Path,
) -> ImageArray:
    if not path.is_file():
        raise BenchmarkImageNotFoundError(f"Benchmark image not found: {path}")

    image_raw = cv2.imread(
        str(path),
        cv2.IMREAD_COLOR,
    )

    if image_raw is None:
        raise InvalidBenchmarkImageError(f"Unable to read benchmark image: {path}")

    return cast(
        ImageArray,
        image_raw,
    )


def percentile(
    values: list[float],
    percentile_value: float,
) -> float:
    if not values:
        raise ValueError(
            "values cannot be empty.",
        )

    return float(
        np.percentile(
            np.asarray(
                values,
                dtype=np.float64,
            ),
            percentile_value,
        )
    )


class BenchmarkRunner:
    def __init__(
        self,
        *,
        detector: StockDetector,
        samples_directory: Path,
        warmup_iterations: int = 0,
    ) -> None:
        if warmup_iterations < 0:
            raise ValueError(
                "warmup_iterations cannot be negative.",
            )

        self._detector = detector
        self._samples_directory = samples_directory
        self._warmup_iterations = warmup_iterations

    def run(
        self,
        *,
        samples: list[BenchmarkSample],
    ) -> tuple[
        list[BenchmarkResult],
        BenchmarkSummary,
    ]:
        if not samples:
            raise ValueError(
                "samples cannot be empty.",
            )

        self._warmup(
            samples[0],
        )

        results: list[BenchmarkResult] = []

        for sample in samples:
            image = load_benchmark_image(self._samples_directory / sample.filename)

            started_at = perf_counter()

            detection_result = self._detector.detect(image)

            latency_ms = (perf_counter() - started_at) * 1000.0

            detected_stock_percentage = (
                detection_result.detected_units / sample.shelf_capacity
            ) * 100.0

            absolute_units_error = abs(sample.expected_units - detection_result.detected_units)

            absolute_stock_percentage_error = abs(
                sample.expected_stock_percentage - detected_stock_percentage
            )

            results.append(
                BenchmarkResult(
                    filename=sample.filename,
                    detector_name=(detection_result.detector_name),
                    expected_units=(sample.expected_units),
                    detected_units=(detection_result.detected_units),
                    shelf_capacity=(sample.shelf_capacity),
                    expected_stock_percentage=(sample.expected_stock_percentage),
                    detected_stock_percentage=(detected_stock_percentage),
                    absolute_units_error=(absolute_units_error),
                    absolute_stock_percentage_error=(absolute_stock_percentage_error),
                    latency_ms=latency_ms,
                )
            )

        units_errors = [float(result.absolute_units_error) for result in results]

        stock_percentage_errors = [result.absolute_stock_percentage_error for result in results]

        latencies = [result.latency_ms for result in results]

        summary = BenchmarkSummary(
            detector_name=self._detector.name,
            sample_count=len(results),
            units_mae=(sum(units_errors) / len(units_errors)),
            stock_percentage_mae=(sum(stock_percentage_errors) / len(stock_percentage_errors)),
            latency_mean_ms=(sum(latencies) / len(latencies)),
            latency_p50_ms=percentile(
                latencies,
                50.0,
            ),
            latency_p95_ms=percentile(
                latencies,
                95.0,
            ),
        )

        return results, summary

    def _warmup(
        self,
        sample: BenchmarkSample,
    ) -> None:
        if self._warmup_iterations == 0:
            return

        image = load_benchmark_image(self._samples_directory / sample.filename)

        for _ in range(self._warmup_iterations):
            self._detector.detect(
                image,
            )
