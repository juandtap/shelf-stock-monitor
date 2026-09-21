from loguru import logger

from app.notifications.models import LowStockNotification


class LoggingNotificationProvider:
    def send_low_stock_alert(
        self,
        notification: LowStockNotification,
    ) -> None:
        logger.warning(
            (
                "Low stock notification | "
                "alert_id={} | "
                "product={} | "
                "camera={} | "
                "units={}/{} | "
                "stock_percentage={:.2f} | "
                "threshold={:.2f}"
            ),
            notification.alert_id,
            notification.product_name,
            notification.camera_name,
            notification.detected_units,
            notification.shelf_capacity,
            notification.stock_percentage,
            notification.threshold_percentage,
        )
