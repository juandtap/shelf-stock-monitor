from fastapi import status
from fastapi.testclient import TestClient


def test_create_product(client: TestClient) -> None:
    response = client.post(
        "/products",
        json={
            "name": "Coca-Cola 500 ml",
            "sku": "COKE-500",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["name"] == "Coca-Cola 500 ml"
    assert data["sku"] == "COKE-500"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_list_products(client: TestClient) -> None:
    client.post(
        "/products",
        json={
            "name": "Pepsi 500 ml",
            "sku": "PEPSI-500",
        },
    )

    response = client.get("/products")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 1
    assert data[0]["sku"] == "PEPSI-500"


def test_get_product_by_id(client: TestClient) -> None:
    create_response = client.post(
        "/products",
        json={
            "name": "Water 1 L",
            "sku": "WATER-1000",
        },
    )

    product_id = create_response.json()["id"]

    response = client.get(f"/products/{product_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == product_id


def test_get_product_not_found(client: TestClient) -> None:
    response = client.get(
        "/products/00000000-0000-0000-0000-000000000001",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Product not found."


def test_create_product_with_duplicate_sku(client: TestClient) -> None:
    first_response = client.post(
        "/products",
        json={
            "name": "Coca-Cola 500 ml",
            "sku": "COKE-500",
        },
    )

    second_response = client.post(
        "/products",
        json={
            "name": "Different Product",
            "sku": "COKE-500",
        },
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_409_CONFLICT
    assert second_response.json()["detail"] == "A product with this SKU already exists."
