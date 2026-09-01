import uuid
from collections.abc import Mapping

from loguru import logger
from sqlalchemy.orm import Session

from app.db.models.stock_observation import StockObservation
from app.repositories.shelf_configuration import ShelfConfigurationRepository
from app.services.shelf_monitoring import ShelfMonitoringService
from app.services.stock_alert import StockAlertService


class MonitoringImagePathNotFoundError(Exception):
    pass


class MonitoringCycleService:
    def __init__(
        self,
        db: Session,
    ) -> None:
        self._configuration_repository = ShelfConfigurationRepository(db)
        self._monitoring_service = ShelfMonitoringService(db)
        self._stock_alert_service = StockAlertService(db)

    def run(
        self,
        *,
        image_paths: Mapping[uuid.UUID, str],
    ) -> list[StockObservation]:
        configurations = self._configuration_repository.get_active()

        observations: list[StockObservation] = []

        for configuration in configurations:
            image_path = image_paths.get(configuration.id)

            if image_path is None:
                raise MonitoringImagePathNotFoundError(
                    f"No current image path configured for shelf configuration {configuration.id}."
                )

            logger.info(
                (
                    "Processing shelf configuration | "
                    "configuration_id={} | "
                    "camera_id={} | "
                    "product_id={} | "
                    "detector={}"
                ),
                configuration.id,
                configuration.camera_id,
                configuration.product_id,
                configuration.detector_type,
            )

            observation = self._monitoring_service.process(
                configuration=configuration,
                image_path=image_path,
            )

            self._stock_alert_service.evaluate(
                configuration=configuration,
                observation=observation,
            )

            observations.append(observation)

        return observations
