from fastapi import status
from fastapi.testclient import TestClient


def create_camera(client: TestClient) -> str:
    response = client.post(
        "/cameras",
        json={
            "name": "Observation Test Camera",
            "location": "Test Shelf",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    return str(response.json()["id"])


def create_product(client: TestClient) -> str:
    response = client.post(
        "/products",
        json={
            "name": "Observation Test Product",
            "sku": "OBS-TEST-001",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    return str(response.json()["id"])


def test_create_stock_observation(client: TestClient) -> None:
    camera_id = create_camera(client)
    product_id = create_product(client)

    response = client.post(
        "/stock-observations",
        json={
            "camera_id": camera_id,
            "product_id": product_id,
            "detected_units": 3,
            "shelf_capacity": 6,
            "detector_name": "opencv_roi",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["camera_id"] == camera_id
    assert data["product_id"] == product_id
    assert data["detected_units"] == 3
    assert data["shelf_capacity"] == 6
    assert data["stock_percentage"] == 50.0
    assert data["detector_name"] == "opencv_roi"
    assert "id" in data
    assert "captured_at" in data


def test_calculates_stock_percentage(client: TestClient) -> None:
    camera_id = create_camera(client)
    product_id = create_product(client)

    response = client.post(
        "/stock-observations",
        json={
            "camera_id": camera_id,
            "product_id": product_id,
            "detected_units": 2,
            "shelf_capacity": 8,
            "detector_name": "opencv_roi",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["stock_percentage"] == 25.0


def test_rejects_detected_units_above_capacity(client: TestClient) -> None:
    camera_id = create_camera(client)
    product_id = create_product(client)

    response = client.post(
        "/stock-observations",
        json={
            "camera_id": camera_id,
            "product_id": product_id,
            "detected_units": 7,
            "shelf_capacity": 6,
            "detector_name": "opencv_roi",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_observation_with_unknown_camera(client: TestClient) -> None:
    product_id = create_product(client)

    response = client.post(
        "/stock-observations",
        json={
            "camera_id": "00000000-0000-0000-0000-000000000001",
            "product_id": product_id,
            "detected_units": 3,
            "shelf_capacity": 6,
            "detector_name": "opencv_roi",
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Camera not found."


def test_create_observation_with_unknown_product(client: TestClient) -> None:
    camera_id = create_camera(client)

    response = client.post(
        "/stock-observations",
        json={
            "camera_id": camera_id,
            "product_id": "00000000-0000-0000-0000-000000000001",
            "detected_units": 3,
            "shelf_capacity": 6,
            "detector_name": "opencv_roi",
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Product not found."


def test_list_stock_observations(client: TestClient) -> None:
    camera_id = create_camera(client)
    product_id = create_product(client)

    create_response = client.post(
        "/stock-observations",
        json={
            "camera_id": camera_id,
            "product_id": product_id,
            "detected_units": 4,
            "shelf_capacity": 8,
            "detector_name": "opencv_roi",
        },
    )

    assert create_response.status_code == status.HTTP_201_CREATED

    response = client.get("/stock-observations")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 1
    assert data[0]["stock_percentage"] == 50.0


def test_get_stock_observation_by_id(client: TestClient) -> None:
    camera_id = create_camera(client)
    product_id = create_product(client)

    create_response = client.post(
        "/stock-observations",
        json={
            "camera_id": camera_id,
            "product_id": product_id,
            "detected_units": 1,
            "shelf_capacity": 4,
            "detector_name": "opencv_roi",
        },
    )

    observation_id = create_response.json()["id"]

    response = client.get(
        f"/stock-observations/{observation_id}",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == observation_id


def test_get_stock_observation_not_found(client: TestClient) -> None:
    response = client.get(
        "/stock-observations/00000000-0000-0000-0000-000000000001",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Stock observation not found."
