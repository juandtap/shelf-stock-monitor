from collections.abc import Callable
from typing import cast

from apscheduler.schedulers.background import (  # type: ignore[import-untyped]
    BackgroundScheduler,
)
from loguru import logger


class MonitoringScheduler:
    JOB_ID = "shelf-monitoring-cycle"

    def __init__(
        self,
        *,
        enabled: bool,
        interval_minutes: int,
        job: Callable[[], None],
    ) -> None:
        if interval_minutes <= 0:
            raise ValueError("Monitoring interval must be greater than zero.")

        self._enabled = enabled
        self._interval_minutes = interval_minutes
        self._job = job
        self._scheduler = BackgroundScheduler(
            timezone="UTC",
        )

    @property
    def running(self) -> bool:
        return cast(bool, self._scheduler.running)

    def start(self) -> None:
        if not self._enabled:
            logger.info("Monitoring scheduler disabled")
            return

        if self.running:
            return

        self._scheduler.add_job(
            self._job,
            trigger="interval",
            minutes=self._interval_minutes,
            id=self.JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        self._scheduler.start()

        logger.info(
            "Monitoring scheduler started | interval_minutes={}",
            self._interval_minutes,
        )

    def shutdown(self) -> None:
        if not self.running:
            return

        self._scheduler.shutdown(
            wait=False,
        )

        logger.info("Monitoring scheduler stopped")
