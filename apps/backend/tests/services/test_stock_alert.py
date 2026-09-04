from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models.camera import Camera
from app.db.models.product import Product
from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.models.stock_alert import StockAlert
from app.db.models.stock_observation import StockObservation
from app.services.stock_alert import (
    StockAlertPolicy,
    StockAlertService,
)


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

    db_session.add_all([camera, product])
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


def create_alert_policy() -> StockAlertPolicy:
    return StockAlertPolicy(
        drop_percentage=15.0,
        reminder_interval=timedelta(minutes=60),
    )


def create_service(
    db_session: Session,
    *,
    clock: Callable[[], datetime] | None = None,
) -> StockAlertService:
    policy = create_alert_policy()

    if clock is None:
        return StockAlertService(
            db_session,
            policy=policy,
        )

    return StockAlertService(
        db_session,
        policy=policy,
        clock=clock,
    )


def test_creates_alert_when_first_observation_is_low(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=40.0,
    )

    service = create_service(db_session)

    alert = service.evaluate(
        configuration=configuration,
        observation=observation,
    )

    assert isinstance(alert, StockAlert)
    assert alert.stock_percentage == 40.0
    assert alert.threshold_percentage == 50.0


def test_creates_alert_when_stock_enters_low_state(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    previous_observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=75.0,
    )

    observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=40.0,
    )

    service = create_service(db_session)

    alert = service.evaluate(
        configuration=configuration,
        observation=observation,
        previous_observation=previous_observation,
    )

    assert alert is not None
    assert alert.stock_observation_id == observation.id


def test_does_not_create_alert_when_low_state_continues(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    first_low_observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=40.0,
    )

    service = create_service(db_session)

    first_alert = service.evaluate(
        configuration=configuration,
        observation=first_low_observation,
    )

    assert first_alert is not None

    current_observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=35.0,
    )

    alert = service.evaluate(
        configuration=configuration,
        observation=current_observation,
        previous_observation=first_low_observation,
    )

    assert alert is None


def test_creates_alert_after_significant_stock_drop(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    first_low_observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=49.0,
    )

    service = create_service(db_session)

    first_alert = service.evaluate(
        configuration=configuration,
        observation=first_low_observation,
    )

    assert first_alert is not None

    current_observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=34.0,
    )

    alert = service.evaluate(
        configuration=configuration,
        observation=current_observation,
        previous_observation=first_low_observation,
    )

    assert alert is not None
    assert alert.stock_percentage == 34.0


def test_creates_reminder_when_reminder_interval_has_elapsed(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    first_low_observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=40.0,
    )

    fixed_now = datetime.now(UTC)

    service = create_service(
        db_session,
        clock=lambda: fixed_now,
    )

    first_alert = service.evaluate(
        configuration=configuration,
        observation=first_low_observation,
    )

    assert first_alert is not None

    first_alert.created_at = fixed_now - timedelta(minutes=60)
    db_session.commit()

    current_observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=40.0,
    )

    reminder_alert = service.evaluate(
        configuration=configuration,
        observation=current_observation,
        previous_observation=first_low_observation,
    )

    assert reminder_alert is not None
    assert reminder_alert.stock_percentage == 40.0


def test_does_not_create_reminder_before_interval_has_elapsed(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    first_low_observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=40.0,
    )

    fixed_now = datetime.now(UTC)

    service = create_service(
        db_session,
        clock=lambda: fixed_now,
    )

    first_alert = service.evaluate(
        configuration=configuration,
        observation=first_low_observation,
    )

    assert first_alert is not None

    first_alert.created_at = fixed_now - timedelta(minutes=59)
    db_session.commit()

    current_observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=40.0,
    )

    reminder_alert = service.evaluate(
        configuration=configuration,
        observation=current_observation,
        previous_observation=first_low_observation,
    )

    assert reminder_alert is None


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

    service = create_service(db_session)

    alert = service.evaluate(
        configuration=configuration,
        observation=observation,
    )

    assert alert is None


def test_creates_new_alert_after_stock_recovers_and_drops_again(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    initial_low = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=40.0,
    )

    service = create_service(db_session)

    first_alert = service.evaluate(
        configuration=configuration,
        observation=initial_low,
    )

    assert first_alert is not None

    recovered_observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=75.0,
    )

    recovery_result = service.evaluate(
        configuration=configuration,
        observation=recovered_observation,
        previous_observation=initial_low,
    )

    assert recovery_result is None

    new_low_observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=40.0,
    )

    new_alert = service.evaluate(
        configuration=configuration,
        observation=new_low_observation,
        previous_observation=recovered_observation,
    )

    assert new_alert is not None
    assert new_alert.id != first_alert.id


def test_returns_existing_alert_when_same_observation_is_evaluated_twice(
    db_session: Session,
) -> None:
    configuration = create_configuration(
        db_session,
        threshold=50.0,
    )

    observation = create_observation(
        db_session,
        configuration=configuration,
        stock_percentage=40.0,
    )

    service = create_service(db_session)

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
