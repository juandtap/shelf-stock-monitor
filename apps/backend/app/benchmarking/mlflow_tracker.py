from collections.abc import Mapping
from typing import cast

import mlflow

from app.benchmarking.models import (
    BenchmarkResult,
    BenchmarkSummary,
)


class MLflowBenchmarkTracker:
    def __init__(
        self,
        *,
        tracking_uri: str,
        experiment_name: str,
    ) -> None:
        if not tracking_uri.strip():
            raise ValueError("tracking_uri cannot be empty.")

        if not experiment_name.strip():
            raise ValueError("experiment_name cannot be empty.")

        self._tracking_uri = tracking_uri
        self._experiment_name = experiment_name

    def log_run(
        self,
        *,
        summary: BenchmarkSummary,
        results: list[BenchmarkResult],
        parameters: Mapping[str, str | int | float | bool],
    ) -> str:
        if not results:
            raise ValueError("results cannot be empty.")

        mlflow.set_tracking_uri(self._tracking_uri)

        mlflow.set_experiment(
            self._experiment_name,
        )

        with mlflow.start_run(
            run_name=summary.detector_name,
        ) as run:
            mlflow.log_params(dict(parameters))

            mlflow.log_metrics(
                {
                    "units_mae": summary.units_mae,
                    "stock_percentage_mae": (summary.stock_percentage_mae),
                    "latency_mean_ms": (summary.latency_mean_ms),
                    "latency_p50_ms": (summary.latency_p50_ms),
                    "latency_p95_ms": (summary.latency_p95_ms),
                    "sample_count": float(summary.sample_count),
                }
            )

            for index, result in enumerate(results):
                mlflow.log_metrics(
                    {
                        "detected_units": float(result.detected_units),
                        "expected_units": float(result.expected_units),
                        "absolute_units_error": float(result.absolute_units_error),
                        "absolute_stock_percentage_error": (result.absolute_stock_percentage_error),
                        "latency_ms": result.latency_ms,
                    },
                    step=index,
                )

            return cast(str, run.info.run_id)
