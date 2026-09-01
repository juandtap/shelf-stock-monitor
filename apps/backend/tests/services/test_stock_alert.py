from sqlalchemy.orm import Session

from app.db.models.camera import Camera
from app.db.models.product import Product
from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.models.stock_alert import StockAlert
from app.db.models.stock_observation import StockObservation
from app.services.stock_alert import StockAlertService


def create_configuration(
    db_session: Session,
    *,
    threshold: float,
) -> ShelfConfiguration:
    camera = Camera(
        name="Alert Test Camera",
        location="Test Shelf",
    )

    product = Product(
        name="Alert Test Product",
        sku="ALERT-TEST-SKU",
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
                }
            ],
        },
        low_stock_threshold=threshold,
    )

    db_session.add(configuration)
    db_session.flush()

    return configuration


def create_observation(
    db_session: Session,
    *,
    configuration: ShelfConfiguration,
    stock_percentage: float,
) -> StockObservation:
    observation = StockObservation(
        camera_id=configuration.camera_id,
        product_id=configuration.product_id,
        detected_units=1,
        shelf_capacity=4,
        stock_percentage=stock_percentage,
        detector_name="opencv_roi",
    )

    db_session.add(observation)
    db_session.commit()
    db_session.refresh(observation)

    return observation


def test_creates_alert_when_stock_is_below_threshold(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=25.0,
    )

    service = StockAlertService(db_session)

    alert = service.evaluate(
        configuration=configuration,
        observation=observation,
    )

    assert isinstance(alert, StockAlert)
    assert alert.stock_observation_id == observation.id
    assert alert.stock_percentage == 25.0
    assert alert.threshold_percentage == 50.0


def test_does_not_create_alert_when_stock_equals_threshold(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=50.0,
    )

    service = StockAlertService(db_session)

    alert = service.evaluate(
        configuration=configuration,
        observation=observation,
    )

    assert alert is None


def test_does_not_create_alert_when_stock_is_above_threshold(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=75.0,
    )

    service = StockAlertService(db_session)

    alert = service.evaluate(
        configuration=configuration,
        observation=observation,
    )

    assert alert is None


def test_returns_existing_alert_when_observation_is_evaluated_twice(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=25.0,
    )

    service = StockAlertService(db_session)

    first_alert = service.evaluate(
        configuration=configuration,
        observation=observation,
    )

    second_alert = service.evaluate(
        configuration=configuration,
        observation=observation,
    )

    assert first_alert is not None
    assert second_alert is not None
    assert second_alert.id == first_alert.id
