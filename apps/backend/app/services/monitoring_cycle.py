import uuid
from collections.abc import Mapping

from loguru import logger
from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.models.stock_observation import StockObservation
from app.notifications.provider import NotificationProvider
from app.repositories.shelf_configuration import ShelfConfigurationRepository
from app.repositories.stock_observation import StockObservationRepository
from app.schemas.shelf_configuration import YOLOConfiguration
from app.services.notification import NotificationService
from app.services.shelf_monitoring import ShelfMonitoringService
from app.services.stock_alert import (
    StockAlertPolicy,
    StockAlertService,
)
from app.services.yolo_inventory_detection import YOLOInventoryDetectionService
from app.vision.detector_factory import StockDetectorFactoryProtocol
from app.vision.factory import StockDetectorFactory


class MonitoringImagePathNotFoundError(Exception):
    pass


class InconsistentYOLOConfigurationError(Exception):
    pass


class MonitoringCycleService:
    def __init__(
        self,
        db: Session,
        *,
        alert_policy: StockAlertPolicy,
        notification_provider: NotificationProvider,
        detector_factory: StockDetectorFactoryProtocol | None = None,
    ) -> None:
        self._db = db
        self._configuration_repository = ShelfConfigurationRepository(db)
        self._observation_repository = StockObservationRepository(db)

        self._detector_factory = detector_factory or StockDetectorFactory()

        self._monitoring_service = ShelfMonitoringService(
            db,
            detector_factory=self._detector_factory,
        )

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
        configurations = self._configuration_repository.get_monitorable()

        observations: list[StockObservation] = []

        opencv_configurations = [
            configuration
            for configuration in configurations
            if configuration.detector_type == "opencv_roi"
        ]

        yolo_configurations_by_camera = self._group_yolo_configurations_by_camera(
            configurations,
        )

        for configuration in opencv_configurations:
            image_path = self._get_image_path(
                image_paths=image_paths,
                camera_id=configuration.camera_id,
            )

            logger.info(
                (
                    "Processing OpenCV shelf configuration | "
                    "configuration_id={} | "
                    "camera_id={} | "
                    "product_id={}"
                ),
                configuration.id,
                configuration.camera_id,
                configuration.product_id,
            )

            previous_observation = self._get_previous_observation(
                configuration,
            )

            observation = self._monitoring_service.process(
                configuration=configuration,
                image_path=image_path,
            )

            self._evaluate_observation(
                configuration=configuration,
                observation=observation,
                previous_observation=previous_observation,
            )

            observations.append(observation)

        for (
            camera_id,
            camera_configurations,
        ) in yolo_configurations_by_camera.items():
            image_path = self._get_image_path(
                image_paths=image_paths,
                camera_id=camera_id,
            )

            yolo_config = self._get_shared_yolo_configuration(
                camera_configurations,
            )

            logger.info(
                ("Processing YOLO camera | camera_id={} | model_key={} | products={}"),
                camera_id,
                yolo_config.model_key,
                len(camera_configurations),
            )

            previous_observations = {
                configuration.product_id: (
                    self._get_previous_observation(
                        configuration,
                    )
                )
                for configuration in camera_configurations
            }

            image = self._monitoring_service.load_image(
                image_path,
            )

            detector = self._detector_factory.create(
                camera_configurations[0],
            )

            yolo_service = YOLOInventoryDetectionService(
                db=self._db,
                detector=detector,
            )

            camera_observations = yolo_service.process(
                image=image,
                camera_id=camera_id,
                model_key=yolo_config.model_key,
            )

            configurations_by_product = {
                configuration.product_id: configuration for configuration in camera_configurations
            }

            for observation in camera_observations:
                configuration = configurations_by_product[observation.product_id]

                self._evaluate_observation(
                    configuration=configuration,
                    observation=observation,
                    previous_observation=previous_observations[observation.product_id],
                )

                observations.append(observation)

        return observations

    @staticmethod
    def _group_yolo_configurations_by_camera(
        configurations: list[ShelfConfiguration],
    ) -> dict[uuid.UUID, list[ShelfConfiguration]]:
        grouped: dict[
            uuid.UUID,
            list[ShelfConfiguration],
        ] = {}

        for configuration in configurations:
            if configuration.detector_type != "yolo":
                continue

            grouped.setdefault(
                configuration.camera_id,
                [],
            ).append(configuration)

        return grouped

    @staticmethod
    def _get_shared_yolo_configuration(
        configurations: list[ShelfConfiguration],
    ) -> YOLOConfiguration:
        if not configurations:
            raise ValueError(
                "At least one YOLO configuration is required.",
            )

        adapter = TypeAdapter(
            YOLOConfiguration,
        )

        parsed_configurations = [
            adapter.validate_python(
                configuration.detector_config,
            )
            for configuration in configurations
        ]

        expected = parsed_configurations[0]

        for current in parsed_configurations[1:]:
            if current != expected:
                raise InconsistentYOLOConfigurationError(
                    "All active YOLO shelf configurations for the same "
                    "camera must use the same model and inference settings."
                )

        return expected

    @staticmethod
    def _get_image_path(
        *,
        image_paths: Mapping[uuid.UUID, str],
        camera_id: uuid.UUID,
    ) -> str:
        image_path = image_paths.get(
            camera_id,
        )

        if image_path is None:
            raise MonitoringImagePathNotFoundError(
                f"No current image path configured for camera {camera_id}.",
            )

        return image_path

    def _get_previous_observation(
        self,
        configuration: ShelfConfiguration,
    ) -> StockObservation | None:
        return self._observation_repository.get_latest_for_camera_and_product(
            camera_id=configuration.camera_id,
            product_id=configuration.product_id,
        )

    def _evaluate_observation(
        self,
        *,
        configuration: ShelfConfiguration,
        observation: StockObservation,
        previous_observation: StockObservation | None,
    ) -> None:
        alert = self._stock_alert_service.evaluate(
            configuration=configuration,
            observation=observation,
            previous_observation=previous_observation,
        )

        if alert is not None:
            self._notification_service.notify_low_stock(
                alert=alert,
                configuration=configuration,
                observation=observation,
            )
