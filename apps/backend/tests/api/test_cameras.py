from fastapi import status
from fastapi.testclient import TestClient


def test_create_camera(client: TestClient) -> None:
    response = client.post(
        "/cameras",
        json={
            "name": "Test Camera 01",
            "location": "Test Shelf",
            "source_type": "file",
            "source_uri": "../../data/samples/shelf_01_100.png",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["name"] == "Test Camera 01"
    assert data["location"] == "Test Shelf"
    assert data["source_type"] == "file"
    assert data["source_uri"] == "../../data/samples/shelf_01_100.png"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_camera_uses_default_source_type(
    client: TestClient,
) -> None:
    response = client.post(
        "/cameras",
        json={
            "name": "Default Source Camera",
            "location": "Test Shelf",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["source_type"] == "file"
    assert data["source_uri"] is None


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
            "source_uri": "../../data/samples/shelf_01_100.png",
        },
    )

    camera_id = create_response.json()["id"]

    response = client.get(f"/cameras/{camera_id}")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["id"] == camera_id
    assert data["source_type"] == "file"
    assert data["source_uri"] == "../../data/samples/shelf_01_100.png"


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

    first_response = client.post(
        "/cameras",
        json=payload,
    )
    second_response = client.post(
        "/cameras",
        json=payload,
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_409_CONFLICT
    assert second_response.json()["detail"] == "A camera with this name already exists."


def test_update_camera_source_uri(client: TestClient) -> None:
    create_response = client.post(
        "/cameras",
        json={
            "name": "Stock Simulation Camera",
            "location": "Shelf C",
            "source_uri": "../../data/samples/shelf_01_100.png",
        },
    )

    camera_id = create_response.json()["id"]

    response = client.patch(
        f"/cameras/{camera_id}",
        json={
            "source_uri": "../../data/samples/shelf_01_25.png",
        },
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["source_uri"] == "../../data/samples/shelf_01_25.png"
    assert data["name"] == "Stock Simulation Camera"
    assert data["location"] == "Shelf C"
    assert data["source_type"] == "file"


def test_partial_update_preserves_other_camera_fields(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/cameras",
        json={
            "name": "Partial Update Camera",
            "location": "Original Location",
            "source_uri": "../../data/samples/shelf_01_100.png",
        },
    )

    camera_id = create_response.json()["id"]

    response = client.patch(
        f"/cameras/{camera_id}",
        json={
            "location": "Updated Location",
        },
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["name"] == "Partial Update Camera"
    assert data["location"] == "Updated Location"
    assert data["source_type"] == "file"
    assert data["source_uri"] == "../../data/samples/shelf_01_100.png"
    assert data["is_active"] is True


def test_update_camera_active_state(client: TestClient) -> None:
    create_response = client.post(
        "/cameras",
        json={
            "name": "Active State Camera",
            "location": "Shelf D",
        },
    )

    camera_id = create_response.json()["id"]

    deactivate_response = client.patch(
        f"/cameras/{camera_id}",
        json={
            "is_active": False,
        },
    )

    assert deactivate_response.status_code == status.HTTP_200_OK
    assert deactivate_response.json()["is_active"] is False

    activate_response = client.patch(
        f"/cameras/{camera_id}",
        json={
            "is_active": True,
        },
    )

    assert activate_response.status_code == status.HTTP_200_OK
    assert activate_response.json()["is_active"] is True


def test_update_camera_not_found(client: TestClient) -> None:
    response = client.patch(
        "/cameras/00000000-0000-0000-0000-000000000001",
        json={
            "source_uri": "../../data/samples/shelf_01_25.png",
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Camera not found."


def test_update_camera_with_duplicate_name(
    client: TestClient,
) -> None:
    first_response = client.post(
        "/cameras",
        json={
            "name": "Camera Alpha",
        },
    )

    second_response = client.post(
        "/cameras",
        json={
            "name": "Camera Beta",
        },
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_201_CREATED

    second_camera_id = second_response.json()["id"]

    response = client.patch(
        f"/cameras/{second_camera_id}",
        json={
            "name": "Camera Alpha",
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "A camera with this name already exists."


def test_update_camera_can_clear_source_uri(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/cameras",
        json={
            "name": "Clear Source Camera",
            "source_uri": "../../data/samples/shelf_01_100.png",
        },
    )

    camera_id = create_response.json()["id"]

    response = client.patch(
        f"/cameras/{camera_id}",
        json={
            "source_uri": None,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["source_uri"] is None
