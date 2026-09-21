from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.models.stock_alert import StockAlert
from app.db.models.stock_observation import StockObservation
from app.notifications.models import LowStockNotification
from app.notifications.provider import NotificationProvider


class NotificationService:
    def __init__(
        self,
        provider: NotificationProvider,
    ) -> None:
        self._provider = provider

    def notify_low_stock(
        self,
        *,
        alert: StockAlert,
        configuration: ShelfConfiguration,
        observation: StockObservation,
    ) -> None:
        notification = LowStockNotification(
            alert_id=alert.id,
            observation_id=observation.id,
            product_name=configuration.product.name,
            camera_name=configuration.camera.name,
            detected_units=observation.detected_units,
            shelf_capacity=observation.shelf_capacity,
            stock_percentage=observation.stock_percentage,
            threshold_percentage=configuration.low_stock_threshold,
        )

        self._provider.send_low_stock_alert(
            notification,
        )
