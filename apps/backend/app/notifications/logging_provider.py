from loguru import logger

from app.db.models.stock_alert import StockAlert


class LoggingNotificationProvider:
    def send_low_stock_alert(
        self,
        alert: StockAlert,
    ) -> None:
        logger.warning(
            ("Low stock notification | alert_id={} | stock_percentage={:.2f} | threshold={:.2f}"),
            alert.id,
            alert.stock_percentage,
            alert.threshold_percentage,
        )
