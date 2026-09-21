import uuid
from datetime import timedelta

from loguru import logger

from app.core.config import get_settings
from app.db.models.camera import Camera
from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.session import SessionLocal
from app.notifications.factory import create_notification_provider
from app.repositories.shelf_configuration import ShelfConfigurationRepository
from app.services.monitoring_cycle import MonitoringCycleService
from app.services.stock_alert import StockAlertPolicy


class CameraSourceNotConfiguredError(Exception):
    pass


class UnsupportedCameraSourceError(Exception):
    pass


def run_monitoring_cycle() -> None:
    settings = get_settings()

    logger.info("Monitoring cycle started")

    try:
        with SessionLocal() as db:
            configuration_repository = ShelfConfigurationRepository(db)

            configurations = configuration_repository.get_monitorable()

            logger.info(
                "Monitorable shelf configurations found | count={}",
                len(configurations),
            )

            if not configurations:
                logger.info(
                    "Monitoring cycle skipped | reason=no_monitorable_configurations",
                )
                return

            cameras_by_id = _get_cameras_by_id(
                configurations,
            )

            image_paths = _build_image_paths(
                cameras_by_id,
            )

            alert_policy = StockAlertPolicy(
                drop_percentage=settings.low_stock_drop_percentage,
                reminder_interval=timedelta(
                    minutes=settings.low_stock_reminder_minutes,
                ),
            )

            notification_provider = create_notification_provider(
                settings,
            )

            monitoring_service = MonitoringCycleService(
                db,
                alert_policy=alert_policy,
                notification_provider=notification_provider,
            )

            observations = monitoring_service.run(
                image_paths=image_paths,
            )

            for observation in observations:
                logger.info(
                    (
                        "Stock observation created | "
                        "camera_id={} | "
                        "product_id={} | "
                        "units={} | "
                        "capacity={} | "
                        "stock_percentage={:.2f} | "
                        "detector={}"
                    ),
                    observation.camera_id,
                    observation.product_id,
                    observation.detected_units,
                    observation.shelf_capacity,
                    observation.stock_percentage,
                    observation.detector_name,
                )

            logger.info(
                "Monitoring cycle completed | observations={}",
                len(observations),
            )

    except Exception:
        logger.exception("Monitoring cycle failed")


def _get_cameras_by_id(
    configurations: list[ShelfConfiguration],
) -> dict[uuid.UUID, Camera]:
    return {configuration.camera.id: configuration.camera for configuration in configurations}


def _build_image_paths(
    cameras_by_id: dict[uuid.UUID, Camera],
) -> dict[uuid.UUID, str]:
    image_paths: dict[uuid.UUID, str] = {}

    for camera_id, camera in cameras_by_id.items():
        if camera.source_type != "file":
            raise UnsupportedCameraSourceError(
                f"Unsupported camera source type '{camera.source_type}' for camera {camera.id}."
            )

        if camera.source_uri is None:
            raise CameraSourceNotConfiguredError(
                f"No source URI configured for camera {camera.id}."
            )

        image_paths[camera_id] = camera.source_uri

    return image_paths
