from fastapi import status
from fastapi.testclient import TestClient


def create_camera(client: TestClient) -> str:
    response = client.post(
        "/cameras",
        json={
            "name": "Inventory API Camera",
            "location": "Test Shelf",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    return str(response.json()["id"])


def create_product(client: TestClient) -> str:
    response = client.post(
        "/products",
        json={
            "name": "Inventory API Product",
            "sku": "INVENTORY-API-001",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    return str(response.json()["id"])


def create_configuration(
    client: TestClient,
    *,
    camera_id: str,
    product_id: str,
    low_stock_threshold: float = 50.0,
) -> None:
    response = client.post(
        "/shelf-configurations",
        json={
            "camera_id": camera_id,
            "product_id": product_id,
            "detector_type": "opencv_roi",
            "reference_image_path": "data/references/shelf_01_empty.jpg",
            "shelf_capacity": 4,
            "detector_config": {
                "difference_threshold": 30.0,
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
            "low_stock_threshold": low_stock_threshold,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED


def create_observation(
    client: TestClient,
    *,
    camera_id: str,
    product_id: str,
    detected_units: int,
) -> None:
    response = client.post(
        "/stock-observations",
        json={
            "camera_id": camera_id,
            "product_id": product_id,
            "detected_units": detected_units,
            "shelf_capacity": 4,
            "detector_name": "opencv_roi",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_get_inventory_status_returns_unknown_without_observation(
    client: TestClient,
) -> None:
    camera_id = create_camera(client)
    product_id = create_product(client)

    create_configuration(
        client,
        camera_id=camera_id,
        product_id=product_id,
    )

    response = client.get(
        "/inventory/status",
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 1

    inventory = data[0]

    assert inventory["camera_id"] == camera_id
    assert inventory["product_id"] == product_id
    assert inventory["detected_units"] is None
    assert inventory["shelf_capacity"] == 4
    assert inventory["stock_percentage"] is None
    assert inventory["status"] == "unknown"
    assert inventory["detector_name"] is None
    assert inventory["captured_at"] is None


def test_get_inventory_status_returns_latest_stock_state(
    client: TestClient,
) -> None:
    camera_id = create_camera(client)
    product_id = create_product(client)

    create_configuration(
        client,
        camera_id=camera_id,
        product_id=product_id,
        low_stock_threshold=50.0,
    )

    create_observation(
        client,
        camera_id=camera_id,
        product_id=product_id,
        detected_units=3,
    )

    create_observation(
        client,
        camera_id=camera_id,
        product_id=product_id,
        detected_units=1,
    )

    response = client.get(
        "/inventory/status",
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 1

    inventory = data[0]

    assert inventory["camera_id"] == camera_id
    assert inventory["product_id"] == product_id
    assert inventory["detected_units"] == 1
    assert inventory["shelf_capacity"] == 4
    assert inventory["stock_percentage"] == 25.0
    assert inventory["low_stock_threshold"] == 50.0
    assert inventory["status"] == "low_stock"
    assert inventory["detector_name"] == "opencv_roi"
    assert inventory["captured_at"] is not None
