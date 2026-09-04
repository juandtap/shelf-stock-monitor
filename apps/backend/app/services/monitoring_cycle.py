import uuid
from collections.abc import Mapping

from loguru import logger
from sqlalchemy.orm import Session

from app.db.models.stock_observation import StockObservation
from app.notifications.provider import NotificationProvider
from app.repositories.shelf_configuration import ShelfConfigurationRepository
from app.repositories.stock_observation import StockObservationRepository
from app.services.notification import NotificationService
from app.services.shelf_monitoring import ShelfMonitoringService
from app.services.stock_alert import (
    StockAlertPolicy,
    StockAlertService,
)


class MonitoringImagePathNotFoundError(Exception):
    pass


class MonitoringCycleService:
    def __init__(
        self,
        db: Session,
        *,
        alert_policy: StockAlertPolicy,
        notification_provider: NotificationProvider,
    ) -> None:
        self._configuration_repository = ShelfConfigurationRepository(db)
        self._observation_repository = StockObservationRepository(db)

        self._monitoring_service = ShelfMonitoringService(db)

        self._stock_alert_service = StockAlertService(
            db,
            policy=alert_policy,
        )

        self._notification_service = NotificationService(
            provider=notification_provider,
        )

    def run(
        self,
        *,
        image_paths: Mapping[uuid.UUID, str],
    ) -> list[StockObservation]:
        configurations = self._configuration_repository.get_active()

        observations: list[StockObservation] = []

        for configuration in configurations:
            image_path = image_paths.get(
                configuration.id,
            )

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

            previous_observation = self._observation_repository.get_latest_for_camera_and_product(
                camera_id=configuration.camera_id,
                product_id=configuration.product_id,
            )

            observation = self._monitoring_service.process(
                configuration=configuration,
                image_path=image_path,
            )

            alert = self._stock_alert_service.evaluate(
                configuration=configuration,
                observation=observation,
                previous_observation=previous_observation,
            )

            if alert is not None:
                self._notification_service.notify_low_stock(
                    alert,
                )

            observations.append(observation)

        return observations
