from collections.abc import Mapping
from types import TracebackType
from typing import Literal

import mlflow
import pytest

from app.benchmarking.mlflow_tracker import MLflowBenchmarkTracker
from app.benchmarking.models import BenchmarkResult, BenchmarkSummary


class FakeRunInfo:
    def __init__(
        self,
        *,
        run_id: str,
    ) -> None:
        self.run_id = run_id


class FakeRun:
    def __init__(
        self,
        *,
        run_id: str,
    ) -> None:
        self.info = FakeRunInfo(
            run_id=run_id,
        )


class FakeRunContext:
    def __init__(
        self,
        *,
        run_id: str,
    ) -> None:
        self._run = FakeRun(
            run_id=run_id,
        )

    def __enter__(self) -> FakeRun:
        return self._run

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        return False


def create_summary() -> BenchmarkSummary:
    return BenchmarkSummary(
        detector_name="opencv_roi",
        sample_count=2,
        units_mae=0.5,
        stock_percentage_mae=12.5,
        latency_mean_ms=3.0,
        latency_p50_ms=2.5,
        latency_p95_ms=4.0,
    )


def create_results() -> list[BenchmarkResult]:
    return [
        BenchmarkResult(
            filename="sample_1.png",
            detector_name="opencv_roi",
            expected_units=1,
            detected_units=1,
            shelf_capacity=4,
            expected_stock_percentage=25.0,
            detected_stock_percentage=25.0,
            absolute_units_error=0,
            absolute_stock_percentage_error=0.0,
            latency_ms=2.0,
        ),
        BenchmarkResult(
            filename="sample_2.png",
            detector_name="opencv_roi",
            expected_units=2,
            detected_units=1,
            shelf_capacity=4,
            expected_stock_percentage=50.0,
            detected_stock_percentage=25.0,
            absolute_units_error=1,
            absolute_stock_percentage_error=25.0,
            latency_ms=4.0,
        ),
    ]


def test_tracker_rejects_empty_tracking_uri() -> None:
    with pytest.raises(
        ValueError,
        match="tracking_uri cannot be empty",
    ):
        MLflowBenchmarkTracker(
            tracking_uri=" ",
            experiment_name="test-experiment",
        )


def test_tracker_rejects_empty_experiment_name() -> None:
    with pytest.raises(
        ValueError,
        match="experiment_name cannot be empty",
    ):
        MLflowBenchmarkTracker(
            tracking_uri="sqlite:///test.db",
            experiment_name=" ",
        )


def test_tracker_rejects_empty_results() -> None:
    tracker = MLflowBenchmarkTracker(
        tracking_uri="sqlite:///test.db",
        experiment_name="test-experiment",
    )

    with pytest.raises(
        ValueError,
        match="results cannot be empty",
    ):
        tracker.log_run(
            summary=create_summary(),
            results=[],
            parameters={},
        )


def test_tracker_logs_benchmark_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracking_uris: list[str] = []
    experiment_names: list[str] = []
    run_names: list[str] = []
    logged_parameters: list[dict[str, str | int | float | bool]] = []
    logged_metrics: list[tuple[dict[str, float], int | None]] = []

    def fake_set_tracking_uri(
        tracking_uri: str,
    ) -> None:
        tracking_uris.append(tracking_uri)

    def fake_set_experiment(
        experiment_name: str,
    ) -> None:
        experiment_names.append(experiment_name)

    def fake_start_run(
        *,
        run_name: str,
    ) -> FakeRunContext:
        run_names.append(run_name)

        return FakeRunContext(
            run_id="test-run-id",
        )

    def fake_log_params(
        parameters: Mapping[
            str,
            str | int | float | bool,
        ],
    ) -> None:
        logged_parameters.append(dict(parameters))

    def fake_log_metrics(
        metrics: Mapping[str, float],
        *,
        step: int | None = None,
    ) -> None:
        logged_metrics.append(
            (
                dict(metrics),
                step,
            )
        )

    monkeypatch.setattr(
        mlflow,
        "set_tracking_uri",
        fake_set_tracking_uri,
    )

    monkeypatch.setattr(
        mlflow,
        "set_experiment",
        fake_set_experiment,
    )

    monkeypatch.setattr(
        mlflow,
        "start_run",
        fake_start_run,
    )

    monkeypatch.setattr(
        mlflow,
        "log_params",
        fake_log_params,
    )

    monkeypatch.setattr(
        mlflow,
        "log_metrics",
        fake_log_metrics,
    )

    tracker = MLflowBenchmarkTracker(
        tracking_uri="sqlite:///test.db",
        experiment_name="test-experiment",
    )

    parameters: dict[str, str | int | float | bool] = {
        "detector": "opencv_roi",
        "difference_threshold": 20.0,
        "shelf_capacity": 4,
    }

    run_id = tracker.log_run(
        summary=create_summary(),
        results=create_results(),
        parameters=parameters,
    )

    assert run_id == "test-run-id"

    assert tracking_uris == ["sqlite:///test.db"]

    assert experiment_names == ["test-experiment"]

    assert run_names == ["opencv_roi"]

    assert logged_parameters == [parameters]

    assert len(logged_metrics) == 3

    summary_metrics, summary_step = logged_metrics[0]

    assert summary_step is None

    assert summary_metrics == {
        "units_mae": 0.5,
        "stock_percentage_mae": 12.5,
        "latency_mean_ms": 3.0,
        "latency_p50_ms": 2.5,
        "latency_p95_ms": 4.0,
        "sample_count": 2.0,
    }

    first_result_metrics, first_step = logged_metrics[1]

    assert first_step == 0

    assert first_result_metrics == {
        "detected_units": 1.0,
        "expected_units": 1.0,
        "absolute_units_error": 0.0,
        "absolute_stock_percentage_error": 0.0,
        "latency_ms": 2.0,
    }

    second_result_metrics, second_step = logged_metrics[2]

    assert second_step == 1

    assert second_result_metrics == {
        "detected_units": 1.0,
        "expected_units": 2.0,
        "absolute_units_error": 1.0,
        "absolute_stock_percentage_error": 25.0,
        "latency_ms": 4.0,
    }
