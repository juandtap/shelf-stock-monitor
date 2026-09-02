from app.db.models.stock_alert import StockAlert
from app.notifications.provider import NotificationProvider


class NotificationService:
    def __init__(
        self,
        provider: NotificationProvider,
    ) -> None:
        self._provider = provider

    def notify_low_stock(
        self,
        alert: StockAlert,
    ) -> None:
        self._provider.send_low_stock_alert(alert)
