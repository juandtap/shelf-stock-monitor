from datetime import timedelta

from loguru import logger

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.notifications.factory import create_notification_provider
from app.repositories.shelf_configuration import ShelfConfigurationRepository
from app.services.monitoring_cycle import MonitoringCycleService
from app.services.stock_alert import StockAlertPolicy


def run_monitoring_cycle() -> None:
    settings = get_settings()

    logger.info("Monitoring cycle started")

    try:
        with SessionLocal() as db:
            configuration_repository = ShelfConfigurationRepository(db)

            active_configurations = configuration_repository.get_active()

            logger.info(
                "Active shelf configurations found | count={}",
                len(active_configurations),
            )

            if not active_configurations:
                logger.info("Monitoring cycle skipped | reason=no_active_configurations")
                return

            if settings.monitoring_image_path is None:
                raise RuntimeError(
                    "MONITORING_IMAGE_PATH is required when active shelf configurations exist."
                )

            image_paths = {
                configuration.id: settings.monitoring_image_path
                for configuration in active_configurations
            }

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
