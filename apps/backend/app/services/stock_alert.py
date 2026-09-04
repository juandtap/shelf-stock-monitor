from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy.orm import Session

from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.models.stock_alert import StockAlert
from app.db.models.stock_observation import StockObservation
from app.repositories.stock_alert import StockAlertRepository

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class StockAlertPolicy:
    drop_percentage: float
    reminder_interval: timedelta

    def __post_init__(self) -> None:
        if not 0 < self.drop_percentage <= 100:
            raise ValueError(
                "drop_percentage must be greater than 0 and less than or equal to 100."
            )

        if self.reminder_interval <= timedelta(0):
            raise ValueError("reminder_interval must be greater than zero.")


class StockAlertService:
    def __init__(
        self,
        db: Session,
        *,
        policy: StockAlertPolicy,
        clock: Clock = utc_now,
    ) -> None:
        self._repository = StockAlertRepository(db)
        self._policy = policy
        self._clock = clock

    def evaluate(
        self,
        *,
        configuration: ShelfConfiguration,
        observation: StockObservation,
        previous_observation: StockObservation | None = None,
    ) -> StockAlert | None:
        existing_alert = self._repository.get_by_observation_id(
            observation.id,
        )

        if existing_alert is not None:
            return existing_alert

        if observation.stock_percentage >= configuration.low_stock_threshold:
            logger.info(
                (
                    "Stock level normal | "
                    "configuration_id={} | "
                    "stock_percentage={:.2f} | "
                    "threshold={:.2f}"
                ),
                configuration.id,
                observation.stock_percentage,
                configuration.low_stock_threshold,
            )
            return None

        last_alert = self._repository.get_latest_for_camera_and_product(
            camera_id=configuration.camera_id,
            product_id=configuration.product_id,
        )

        if last_alert is None:
            return self._create_alert(
                configuration=configuration,
                observation=observation,
                reason="initial_low_stock",
            )

        previous_was_normal = (
            previous_observation is not None
            and previous_observation.stock_percentage >= configuration.low_stock_threshold
        )

        if previous_was_normal:
            return self._create_alert(
                configuration=configuration,
                observation=observation,
                reason="entered_low_stock",
            )

        stock_drop = last_alert.stock_percentage - observation.stock_percentage

        if stock_drop >= self._policy.drop_percentage:
            return self._create_alert(
                configuration=configuration,
                observation=observation,
                reason="significant_stock_drop",
            )

        now = self._clock()
        last_alert_at = last_alert.created_at

        if last_alert_at.tzinfo is None:
            last_alert_at = last_alert_at.replace(
                tzinfo=UTC,
            )

        if now - last_alert_at >= self._policy.reminder_interval:
            return self._create_alert(
                configuration=configuration,
                observation=observation,
                reason="low_stock_reminder",
            )

        logger.info(
            (
                "Low stock condition continues | "
                "configuration_id={} | "
                "stock_percentage={:.2f} | "
                "last_alert_percentage={:.2f} | "
                "notification_suppressed=true"
            ),
            configuration.id,
            observation.stock_percentage,
            last_alert.stock_percentage,
        )

        return None

    def _create_alert(
        self,
        *,
        configuration: ShelfConfiguration,
        observation: StockObservation,
        reason: str,
    ) -> StockAlert:
        alert = self._repository.create(
            stock_observation_id=observation.id,
            stock_percentage=observation.stock_percentage,
            threshold_percentage=configuration.low_stock_threshold,
        )

        logger.warning(
            (
                "Low stock detected | "
                "reason={} | "
                "configuration_id={} | "
                "observation_id={} | "
                "stock_percentage={:.2f} | "
                "threshold={:.2f} | "
                "alert_id={}"
            ),
            reason,
            configuration.id,
            observation.id,
            observation.stock_percentage,
            configuration.low_stock_threshold,
            alert.id,
        )

        return alert
