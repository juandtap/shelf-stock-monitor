import httpx

from app.notifications.models import LowStockNotification


class TelegramNotificationProvider:
    API_BASE_URL = "https://api.telegram.org"

    def __init__(
        self,
        *,
        bot_token: str,
        chat_id: str,
        timeout_seconds: float,
    ) -> None:
        if not bot_token:
            raise ValueError("Telegram bot token is required.")

        if not chat_id:
            raise ValueError("Telegram chat ID is required.")

        self._bot_token = bot_token
        self._chat_id = chat_id
        self._timeout_seconds = timeout_seconds

    def send_low_stock_alert(
        self,
        notification: LowStockNotification,
    ) -> None:
        url = f"{self.API_BASE_URL}/bot{self._bot_token}/sendMessage"

        message = (
            "⚠️ Low stock detected\n\n"
            f"Product: {notification.product_name}\n"
            f"Stock: {notification.stock_percentage:.2f}% "
            f"({notification.detected_units}/"
            f"{notification.shelf_capacity} units)\n"
            f"Threshold: {notification.threshold_percentage:.2f}%\n"
            f"Camera: {notification.camera_name}"
        )

        response = httpx.post(
            url,
            json={
                "chat_id": self._chat_id,
                "text": message,
            },
            timeout=self._timeout_seconds,
        )

        response.raise_for_status()
