from typing import Protocol

from app.db.models.stock_alert import StockAlert


class NotificationProvider(Protocol):
    def send_low_stock_alert(
        self,
        alert: StockAlert,
    ) -> None: ...
