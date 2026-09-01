from collections.abc import Callable

import pytest

from app.scheduler.monitoring_scheduler import MonitoringScheduler


def noop_job() -> None:
    pass


def test_scheduler_remains_stopped_when_disabled() -> None:
    scheduler = MonitoringScheduler(
        enabled=False,
        interval_minutes=30,
        job=noop_job,
    )

    scheduler.start()

    assert scheduler.running is False

    scheduler.shutdown()


def test_scheduler_starts_when_enabled() -> None:
    scheduler = MonitoringScheduler(
        enabled=True,
        interval_minutes=30,
        job=noop_job,
    )

    try:
        scheduler.start()

        assert scheduler.running is True
    finally:
        scheduler.shutdown()

    assert scheduler.running is False


def test_scheduler_rejects_invalid_interval() -> None:
    job: Callable[[], None] = noop_job

    with pytest.raises(
        ValueError,
        match="Monitoring interval must be greater than zero",
    ):
        MonitoringScheduler(
            enabled=True,
            interval_minutes=0,
            job=job,
        )
