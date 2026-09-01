import uuid
from pathlib import Path

import cv2
import numpy as np
import pytest
from sqlalchemy.orm import Session

from app.db.models.camera import Camera
from app.db.models.product import Product
from app.db.models.shelf_configuration import ShelfConfiguration
from app.services.shelf_monitoring import (
    CurrentImageNotFoundError,
    ShelfMonitoringService,
)


def create_configuration(
    db_session: Session,
    reference_path: Path,
) -> ShelfConfiguration:
    camera = Camera(
        name=f"Monitoring Camera {uuid.uuid4()}",
        location="Test Shelf",
    )

    product = Product(
        name="Monitoring Test Product",
        sku=f"MONITORING-{uuid.uuid4()}",
    )

    db_session.add_all([camera, product])
    db_session.commit()
    db_session.refresh(camera)
    db_session.refresh(product)

    configuration = ShelfConfiguration(
        camera_id=camera.id,
        product_id=product.id,
        detector_type="opencv_roi",
        reference_image_path=str(reference_path),
        detector_config={
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
    )

    db_session.add(configuration)
    db_session.commit()
    db_session.refresh(configuration)

    return configuration


def test_process_shelf_image_creates_observation(
    db_session: Session,
    tmp_path: Path,
) -> None:
    reference_image = np.zeros(
        (100, 400, 3),
        dtype=np.uint8,
    )

    current_image = reference_image.copy()

    current_image[:, 0:100] = 255
    current_image[:, 200:300] = 255

    reference_path = tmp_path / "reference.jpg"
    current_path = tmp_path / "current.jpg"

    assert cv2.imwrite(
        str(reference_path),
        reference_image,
    )
    assert cv2.imwrite(
        str(current_path),
        current_image,
    )

    configuration = create_configuration(
        db_session,
        reference_path,
    )

    service = ShelfMonitoringService(db_session)

    observation = service.process(
        configuration=configuration,
        image_path=str(current_path),
    )

    assert observation.camera_id == configuration.camera_id
    assert observation.product_id == configuration.product_id
    assert observation.detected_units == 2
    assert observation.shelf_capacity == 4
    assert observation.stock_percentage == 50.0
    assert observation.detector_name == "opencv_roi"


def test_process_shelf_image_rejects_missing_image(
    db_session: Session,
    tmp_path: Path,
) -> None:
    reference_image = np.zeros(
        (100, 400, 3),
        dtype=np.uint8,
    )

    reference_path = tmp_path / "reference.jpg"

    assert cv2.imwrite(
        str(reference_path),
        reference_image,
    )

    configuration = create_configuration(
        db_session,
        reference_path,
    )

    service = ShelfMonitoringService(db_session)

    with pytest.raises(CurrentImageNotFoundError):
        service.process(
            configuration=configuration,
            image_path=str(tmp_path / "missing.jpg"),
        )
