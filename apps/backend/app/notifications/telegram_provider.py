import httpx

from app.db.models.stock_alert import StockAlert


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
        alert: StockAlert,
    ) -> None:
        url = f"{self.API_BASE_URL}/bot{self._bot_token}/sendMessage"

        message = (
            "⚠️ Low stock detected\n"
            f"Stock: {alert.stock_percentage:.2f}%\n"
            f"Threshold: {alert.threshold_percentage:.2f}%\n"
            f"Observation: {alert.stock_observation_id}\n"
            f"Alert: {alert.id}"
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
