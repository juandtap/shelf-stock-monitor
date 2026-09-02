from typing import cast

from app.db.models.stock_alert import StockAlert
from app.notifications.provider import NotificationProvider
from app.services.notification import NotificationService


class FakeNotificationProvider:
    def __init__(self) -> None:
        self.received_alert: StockAlert | None = None

    def send_low_stock_alert(
        self,
        alert: StockAlert,
    ) -> None:
        self.received_alert = alert


def test_notification_service_sends_alert_to_provider() -> None:
    alert = cast(
        StockAlert,
        object(),
    )

    provider = FakeNotificationProvider()

    service = NotificationService(
        provider=provider,
    )

    service.notify_low_stock(alert)

    assert provider.received_alert is alert


def test_fake_provider_satisfies_notification_protocol() -> None:
    provider: NotificationProvider = FakeNotificationProvider()

    assert isinstance(
        provider,
        FakeNotificationProvider,
    )
