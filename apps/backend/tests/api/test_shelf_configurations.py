from fastapi import status
from fastapi.testclient import TestClient


def create_camera(client: TestClient) -> str:
    response = client.post(
        "/cameras",
        json={
            "name": "Shelf Config Camera",
            "location": "Aisle 1",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    return str(response.json()["id"])


def create_product(client: TestClient) -> str:
    response = client.post(
        "/products",
        json={
            "name": "Shelf Config Product",
            "sku": "SHELF-CONFIG-001",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    return str(response.json()["id"])


def configuration_payload(
    camera_id: str,
    product_id: str,
) -> dict[str, object]:
    return {
        "camera_id": camera_id,
        "product_id": product_id,
        "detector_type": "opencv_roi",
        "reference_image_path": "data/references/shelf_01_empty.jpg",
        "shelf_capacity": 2,
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
            ],
        },
    }


def test_create_shelf_configuration(
    client: TestClient,
) -> None:
    camera_id = create_camera(client)
    product_id = create_product(client)

    response = client.post(
        "/shelf-configurations",
        json=configuration_payload(
            camera_id,
            product_id,
        ),
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["camera_id"] == camera_id
    assert data["product_id"] == product_id
    assert data["detector_type"] == "opencv_roi"
    assert data["shelf_capacity"] == 2
    assert data["detector_config"]["difference_threshold"] == 30.0
    assert len(data["detector_config"]["regions"]) == 2


def test_configuration_rejects_capacity_different_from_roi_count(
    client: TestClient,
) -> None:
    camera_id = create_camera(client)
    product_id = create_product(client)

    payload = configuration_payload(
        camera_id,
        product_id,
    )
    payload["shelf_capacity"] = 4

    response = client.post(
        "/shelf-configurations",
        json=payload,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_duplicate_configuration_returns_conflict(
    client: TestClient,
) -> None:
    camera_id = create_camera(client)
    product_id = create_product(client)

    payload = configuration_payload(
        camera_id,
        product_id,
    )

    first = client.post(
        "/shelf-configurations",
        json=payload,
    )
    second = client.post(
        "/shelf-configurations",
        json=payload,
    )

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_409_CONFLICT


def test_list_shelf_configurations(
    client: TestClient,
) -> None:
    camera_id = create_camera(client)
    product_id = create_product(client)

    client.post(
        "/shelf-configurations",
        json=configuration_payload(
            camera_id,
            product_id,
        ),
    )

    response = client.get(
        "/shelf-configurations",
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["shelf_capacity"] == 2


def test_configuration_requires_existing_camera(
    client: TestClient,
) -> None:
    product_id = create_product(client)

    payload = configuration_payload(
        "00000000-0000-0000-0000-000000000001",
        product_id,
    )

    response = client.post(
        "/shelf-configurations",
        json=payload,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_configuration_requires_existing_product(
    client: TestClient,
) -> None:
    camera_id = create_camera(client)

    payload = configuration_payload(
        camera_id,
        "00000000-0000-0000-0000-000000000001",
    )

    response = client.post(
        "/shelf-configurations",
        json=payload,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
