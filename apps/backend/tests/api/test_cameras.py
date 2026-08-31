from fastapi import status
from fastapi.testclient import TestClient


def test_create_camera(client: TestClient) -> None:
    response = client.post(
        "/cameras",
        json={
            "name": "Test Camera 01",
            "location": "Test Shelf",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["name"] == "Test Camera 01"
    assert data["location"] == "Test Shelf"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_list_cameras(client: TestClient) -> None:
    client.post(
        "/cameras",
        json={
            "name": "Test Camera 02",
            "location": "Shelf A",
        },
    )

    response = client.get("/cameras")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "Test Camera 02"


def test_get_camera_by_id(client: TestClient) -> None:
    create_response = client.post(
        "/cameras",
        json={
            "name": "Test Camera 03",
            "location": "Shelf B",
        },
    )

    camera_id = create_response.json()["id"]

    response = client.get(f"/cameras/{camera_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == camera_id


def test_get_camera_not_found(client: TestClient) -> None:
    response = client.get(
        "/cameras/00000000-0000-0000-0000-000000000001",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Camera not found."


def test_create_camera_with_duplicate_name(client: TestClient) -> None:
    payload = {
        "name": "Duplicate Camera",
        "location": "Test Shelf",
    }

    first_response = client.post("/cameras", json=payload)
    second_response = client.post("/cameras", json=payload)

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_409_CONFLICT
    assert second_response.json()["detail"] == "A camera with this name already exists."
