from loguru import logger
from sqlalchemy.orm import Session

from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.models.stock_alert import StockAlert
from app.db.models.stock_observation import StockObservation
from app.repositories.stock_alert import StockAlertRepository


class StockAlertService:
    def __init__(self, db: Session) -> None:
        self._repository = StockAlertRepository(db)

    def evaluate(
        self,
        *,
        configuration: ShelfConfiguration,
        observation: StockObservation,
    ) -> StockAlert | None:
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

        existing_alert = self._repository.get_by_observation_id(
            observation.id,
        )

        if existing_alert is not None:
            logger.warning(
                ("Stock alert already exists | observation_id={} | alert_id={}"),
                observation.id,
                existing_alert.id,
            )

            return existing_alert

        alert = self._repository.create(
            stock_observation_id=observation.id,
            stock_percentage=observation.stock_percentage,
            threshold_percentage=configuration.low_stock_threshold,
        )

        logger.warning(
            (
                "Low stock detected | "
                "configuration_id={} | "
                "observation_id={} | "
                "stock_percentage={:.2f} | "
                "threshold={:.2f} | "
                "alert_id={}"
            ),
            configuration.id,
            observation.id,
            observation.stock_percentage,
            configuration.low_stock_threshold,
            alert.id,
        )

        return alert
