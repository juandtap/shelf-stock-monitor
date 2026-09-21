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


def create_shelf_configuration(
    client: TestClient,
) -> dict[str, object]:
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

    return dict(response.json())


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


def test_update_shelf_configuration_partial(
    client: TestClient,
) -> None:
    configuration = create_shelf_configuration(client)
    configuration_id = str(configuration["id"])

    response = client.patch(
        f"/shelf-configurations/{configuration_id}",
        json={
            "low_stock_threshold": 35.0,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["low_stock_threshold"] == 35.0
    assert data["detector_type"] == "opencv_roi"
    assert data["reference_image_path"] == ("data/references/shelf_01_empty.jpg")
    assert data["shelf_capacity"] == 2
    assert data["detector_config"]["difference_threshold"] == 30.0


def test_update_shelf_configuration_active_state(
    client: TestClient,
) -> None:
    configuration = create_shelf_configuration(client)
    configuration_id = str(configuration["id"])

    disable_response = client.patch(
        f"/shelf-configurations/{configuration_id}",
        json={
            "is_active": False,
        },
    )

    assert disable_response.status_code == status.HTTP_200_OK
    assert disable_response.json()["is_active"] is False

    enable_response = client.patch(
        f"/shelf-configurations/{configuration_id}",
        json={
            "is_active": True,
        },
    )

    assert enable_response.status_code == status.HTTP_200_OK
    assert enable_response.json()["is_active"] is True


def test_update_shelf_configuration_not_found(
    client: TestClient,
) -> None:
    response = client.patch(
        ("/shelf-configurations/00000000-0000-0000-0000-000000000001"),
        json={
            "low_stock_threshold": 35.0,
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == ("Shelf configuration not found.")


def test_update_shelf_configuration_from_opencv_to_yolo(
    client: TestClient,
) -> None:
    configuration = create_shelf_configuration(client)
    configuration_id = str(configuration["id"])

    response = client.patch(
        f"/shelf-configurations/{configuration_id}",
        json={
            "detector_type": "yolo",
            "reference_image_path": None,
            "detector_config": {
                "model_key": "yolo11n-synthetic-v1",
                "model_path": ("../../artifacts/models/yolo/yolo11n-synthetic-v1/best.pt"),
                "confidence_threshold": 0.25,
                "iou_threshold": 0.7,
                "image_size": 640,
                "class_ids": [
                    0,
                    1,
                    2,
                ],
                "device": None,
            },
            "shelf_capacity": 4,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["detector_type"] == "yolo"
    assert data["reference_image_path"] is None
    assert data["shelf_capacity"] == 4

    detector_config = data["detector_config"]

    assert detector_config["model_key"] == "yolo11n-synthetic-v1"
    assert detector_config["confidence_threshold"] == 0.25
    assert detector_config["iou_threshold"] == 0.7
    assert detector_config["image_size"] == 640
    assert detector_config["class_ids"] == [0, 1, 2]


def test_update_shelf_configuration_rejects_invalid_opencv_capacity(
    client: TestClient,
) -> None:
    configuration = create_shelf_configuration(client)
    configuration_id = str(configuration["id"])

    response = client.patch(
        f"/shelf-configurations/{configuration_id}",
        json={
            "shelf_capacity": 4,
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_update_shelf_configuration_rejects_inconsistent_detector_config(
    client: TestClient,
) -> None:
    configuration = create_shelf_configuration(client)
    configuration_id = str(configuration["id"])

    response = client.patch(
        f"/shelf-configurations/{configuration_id}",
        json={
            "detector_type": "yolo",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
