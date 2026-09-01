import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.camera import Camera
from app.db.models.product import Product
from app.db.models.stock_alert import StockAlert
from app.db.models.stock_observation import StockObservation


def create_stock_alert(
    db_session: Session,
) -> StockAlert:
    camera = Camera(
        name="Stock Alert API Camera",
        location="Test Shelf",
    )

    product = Product(
        name="Stock Alert API Product",
        sku="STOCK-ALERT-API",
    )

    db_session.add_all(
        [
            camera,
            product,
        ]
    )

    db_session.flush()

    observation = StockObservation(
        camera_id=camera.id,
        product_id=product.id,
        detected_units=1,
        shelf_capacity=4,
        stock_percentage=25.0,
        detector_name="opencv_roi",
    )

    db_session.add(observation)
    db_session.flush()

    alert = StockAlert(
        stock_observation_id=observation.id,
        stock_percentage=25.0,
        threshold_percentage=50.0,
    )

    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    return alert


def test_get_stock_alerts(
    client: TestClient,
    db_session: Session,
) -> None:
    alert = create_stock_alert(
        db_session,
    )

    response = client.get("/stock-alerts")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == str(alert.id)
    assert data[0]["stock_observation_id"] == str(alert.stock_observation_id)
    assert data[0]["stock_percentage"] == 25.0
    assert data[0]["threshold_percentage"] == 50.0


def test_get_stock_alert_by_id(
    client: TestClient,
    db_session: Session,
) -> None:
    alert = create_stock_alert(
        db_session,
    )

    response = client.get(f"/stock-alerts/{alert.id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(alert.id)
    assert data["stock_observation_id"] == str(alert.stock_observation_id)
    assert data["stock_percentage"] == 25.0
    assert data["threshold_percentage"] == 50.0


def test_get_stock_alert_returns_404_when_not_found(
    client: TestClient,
) -> None:
    missing_alert_id = uuid.uuid4()

    response = client.get(f"/stock-alerts/{missing_alert_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Stock alert not found."}
