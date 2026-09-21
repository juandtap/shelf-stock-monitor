from fastapi import status
from fastapi.testclient import TestClient


def create_product(
    client: TestClient,
    *,
    name: str,
    sku: str,
) -> str:
    response = client.post(
        "/products",
        json={
            "name": name,
            "sku": sku,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    return str(response.json()["id"])


def test_create_model_class_mapping(
    client: TestClient,
) -> None:
    product_id = create_product(
        client,
        name="Coca-Cola 500 ml",
        sku="COKE-500",
    )

    response = client.post(
        "/model-class-mappings",
        json={
            "model_key": "yolo11n-synthetic-v1",
            "class_id": 0,
            "product_id": product_id,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["model_key"] == "yolo11n-synthetic-v1"
    assert data["class_id"] == 0
    assert data["product_id"] == product_id
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_list_model_class_mappings_ordered_by_class_id(
    client: TestClient,
) -> None:
    coca_cola_id = create_product(
        client,
        name="Coca-Cola 500 ml",
        sku="COKE-500",
    )
    water_id = create_product(
        client,
        name="Water 500 ml",
        sku="WATER-500",
    )
    shampoo_id = create_product(
        client,
        name="Shampoo",
        sku="SHAMPOO-001",
    )

    mappings = [
        {
            "model_key": "yolo11n-synthetic-v1",
            "class_id": 2,
            "product_id": shampoo_id,
        },
        {
            "model_key": "yolo11n-synthetic-v1",
            "class_id": 0,
            "product_id": coca_cola_id,
        },
        {
            "model_key": "yolo11n-synthetic-v1",
            "class_id": 1,
            "product_id": water_id,
        },
    ]

    for mapping in mappings:
        response = client.post(
            "/model-class-mappings",
            json=mapping,
        )

        assert response.status_code == status.HTTP_201_CREATED

    response = client.get(
        "/model-class-mappings/yolo11n-synthetic-v1",
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 3
    assert [mapping["class_id"] for mapping in data] == [
        0,
        1,
        2,
    ]
    assert data[0]["product_id"] == coca_cola_id
    assert data[1]["product_id"] == water_id
    assert data[2]["product_id"] == shampoo_id


def test_create_model_class_mapping_product_not_found(
    client: TestClient,
) -> None:
    response = client.post(
        "/model-class-mappings",
        json={
            "model_key": "yolo11n-synthetic-v1",
            "class_id": 0,
            "product_id": "00000000-0000-0000-0000-000000000001",
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Product not found."


def test_create_duplicate_model_class_mapping(
    client: TestClient,
) -> None:
    coca_cola_id = create_product(
        client,
        name="Coca-Cola 500 ml",
        sku="COKE-500",
    )
    water_id = create_product(
        client,
        name="Water 500 ml",
        sku="WATER-500",
    )

    first_response = client.post(
        "/model-class-mappings",
        json={
            "model_key": "yolo11n-synthetic-v1",
            "class_id": 0,
            "product_id": coca_cola_id,
        },
    )

    second_response = client.post(
        "/model-class-mappings",
        json={
            "model_key": "yolo11n-synthetic-v1",
            "class_id": 0,
            "product_id": water_id,
        },
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_409_CONFLICT
    assert second_response.json()["detail"] == "This model class is already mapped to a product."


def test_create_duplicate_product_mapping_for_model(
    client: TestClient,
) -> None:
    product_id = create_product(
        client,
        name="Coca-Cola 500 ml",
        sku="COKE-500",
    )

    first_response = client.post(
        "/model-class-mappings",
        json={
            "model_key": "yolo11n-synthetic-v1",
            "class_id": 0,
            "product_id": product_id,
        },
    )

    second_response = client.post(
        "/model-class-mappings",
        json={
            "model_key": "yolo11n-synthetic-v1",
            "class_id": 1,
            "product_id": product_id,
        },
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_409_CONFLICT
    assert second_response.json()["detail"] == "This product is already mapped for this model."


def test_same_class_can_be_used_by_different_models(
    client: TestClient,
) -> None:
    first_product_id = create_product(
        client,
        name="Coca-Cola 500 ml",
        sku="COKE-500",
    )
    second_product_id = create_product(
        client,
        name="Pepsi 500 ml",
        sku="PEPSI-500",
    )

    first_response = client.post(
        "/model-class-mappings",
        json={
            "model_key": "yolo11n-synthetic-v1",
            "class_id": 0,
            "product_id": first_product_id,
        },
    )

    second_response = client.post(
        "/model-class-mappings",
        json={
            "model_key": "another-model-v1",
            "class_id": 0,
            "product_id": second_product_id,
        },
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_201_CREATED
