import uuid

from sqlalchemy.orm import Session

from app.db.models.camera import Camera
from app.db.models.product import Product
from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.models.stock_observation import StockObservation
from app.services.inventory_status import InventoryStatusService


def create_configuration(
    db_session: Session,
    *,
    threshold: float = 50.0,
    is_active: bool = True,
) -> ShelfConfiguration:
    unique_id = uuid.uuid4()

    camera = Camera(
        name=f"Inventory Camera {unique_id}",
        location="Test Shelf",
    )

    product = Product(
        name=f"Inventory Product {unique_id}",
        sku=f"INVENTORY-{unique_id}",
    )

    db_session.add_all(
        [
            camera,
            product,
        ]
    )
    db_session.flush()

    configuration = ShelfConfiguration(
        camera_id=camera.id,
        product_id=product.id,
        detector_type="opencv_roi",
        reference_image_path="reference.png",
        detector_config={
            "difference_threshold": 20.0,
            "regions": [
                {
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                },
                {
                    "x": 100,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                },
                {
                    "x": 200,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                },
                {
                    "x": 300,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                },
            ],
        },
        shelf_capacity=4,
        low_stock_threshold=threshold,
        is_active=is_active,
    )

    db_session.add(configuration)
    db_session.commit()
    db_session.refresh(configuration)

    return configuration


def create_observation(
    db_session: Session,
    *,
    configuration: ShelfConfiguration,
    detected_units: int,
    stock_percentage: float,
) -> StockObservation:
    observation = StockObservation(
        camera_id=configuration.camera_id,
        product_id=configuration.product_id,
        detected_units=detected_units,
        shelf_capacity=configuration.shelf_capacity,
        stock_percentage=stock_percentage,
        detector_name="opencv_roi",
    )

    db_session.add(observation)
    db_session.commit()
    db_session.refresh(observation)

    return observation


def test_returns_unknown_when_configuration_has_no_observation(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
    )

    service = InventoryStatusService(
        db_session,
    )

    statuses = service.get_statuses()

    assert len(statuses) == 1

    status = statuses[0]

    assert status.configuration_id == configuration.id
    assert status.detected_units is None
    assert status.shelf_capacity == 4
    assert status.stock_percentage is None
    assert status.status == "unknown"
    assert status.detector_name is None
    assert status.captured_at is None


def test_returns_low_stock_for_latest_low_observation(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    create_observation(
        db_session,
        configuration=configuration,
        detected_units=1,
        stock_percentage=25.0,
    )

    service = InventoryStatusService(
        db_session,
    )

    statuses = service.get_statuses()

    assert len(statuses) == 1

    status = statuses[0]

    assert status.detected_units == 1
    assert status.shelf_capacity == 4
    assert status.stock_percentage == 25.0
    assert status.low_stock_threshold == 50.0
    assert status.status == "low_stock"
    assert status.detector_name == "opencv_roi"
    assert status.captured_at is not None


def test_returns_ok_when_stock_equals_threshold(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    create_observation(
        db_session,
        configuration=configuration,
        detected_units=2,
        stock_percentage=50.0,
    )

    service = InventoryStatusService(
        db_session,
    )

    statuses = service.get_statuses()

    assert len(statuses) == 1
    assert statuses[0].status == "ok"


def test_ignores_inactive_configurations(
    db_session: Session,
) -> None:
    create_configuration(
        db_session,
        is_active=False,
    )

    service = InventoryStatusService(
        db_session,
    )

    statuses = service.get_statuses()

    assert statuses == []
