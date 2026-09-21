import uuid

from app.db.models.camera import Camera
from app.db.models.product import Product
from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.models.stock_alert import StockAlert
from app.db.models.stock_observation import StockObservation
from app.notifications.models import LowStockNotification
from app.notifications.provider import NotificationProvider
from app.services.notification import NotificationService


class FakeNotificationProvider:
    def __init__(self) -> None:
        self.received_notification: LowStockNotification | None = None

    def send_low_stock_alert(
        self,
        notification: LowStockNotification,
    ) -> None:
        self.received_notification = notification


def test_notification_service_sends_notification_to_provider() -> None:
    camera = Camera(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        name="Shelf Camera 01",
    )

    product = Product(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        name="Shampoo",
        sku="SHAMPOO-001",
    )

    configuration = ShelfConfiguration(
        id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        camera_id=camera.id,
        product_id=product.id,
        detector_type="yolo",
        detector_config={},
        shelf_capacity=4,
        low_stock_threshold=50.0,
    )
    configuration.camera = camera
    configuration.product = product

    observation = StockObservation(
        id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        camera_id=camera.id,
        product_id=product.id,
        detected_units=1,
        shelf_capacity=4,
        stock_percentage=25.0,
        detector_name="yolo",
    )

    alert = StockAlert(
        id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        stock_observation_id=observation.id,
        stock_percentage=25.0,
        threshold_percentage=50.0,
    )

    provider = FakeNotificationProvider()

    service = NotificationService(
        provider=provider,
    )

    service.notify_low_stock(
        alert=alert,
        configuration=configuration,
        observation=observation,
    )

    notification = provider.received_notification

    assert notification is not None
    assert notification.alert_id == alert.id
    assert notification.observation_id == observation.id
    assert notification.product_name == "Shampoo"
    assert notification.camera_name == "Shelf Camera 01"
    assert notification.detected_units == 1
    assert notification.shelf_capacity == 4
    assert notification.stock_percentage == 25.0
    assert notification.threshold_percentage == 50.0


def test_fake_provider_satisfies_notification_protocol() -> None:
    provider: NotificationProvider = FakeNotificationProvider()

    assert isinstance(
        provider,
        FakeNotificationProvider,
    )
