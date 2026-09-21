from typing import Protocol

from app.notifications.models import LowStockNotification


class NotificationProvider(Protocol):
    def send_low_stock_alert(
        self,
        notification: LowStockNotification,
    ) -> None: ...
