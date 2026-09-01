from pathlib import Path

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.db.models.camera import Camera
from app.db.models.product import Product
from app.db.models.shelf_configuration import ShelfConfiguration
from app.services.monitoring_cycle import (
    MonitoringCycleService,
    MonitoringImagePathNotFoundError,
)


def create_configuration(
    *,
    db: Session,
    reference_image_path: Path,
    camera_name: str,
    product_name: str,
    product_sku: str,
    is_active: bool,
) -> ShelfConfiguration:
    camera = Camera(
        name=camera_name,
        location="Test Shelf",
        is_active=True,
    )

    product = Product(
        name=product_name,
        sku=product_sku,
    )

    db.add_all(
        [
            camera,
            product,
        ]
    )
    db.flush()

    configuration = ShelfConfiguration(
        camera_id=camera.id,
        product_id=product.id,
        detector_type="opencv_roi",
        reference_image_path=str(reference_image_path),
        detector_config={
            "difference_threshold": 20.0,
            "regions": [
                {
                    "x": 0,
                    "y": 0,
                    "width": 50,
                    "height": 50,
                },
                {
                    "x": 50,
                    "y": 0,
                    "width": 50,
                    "height": 50,
                },
            ],
        },
        is_active=is_active,
    )

    db.add(configuration)
    db.commit()
    db.refresh(configuration)

    return configuration


def write_test_images(
    *,
    tmp_path: Path,
) -> tuple[Path, Path]:
    reference_path = tmp_path / "reference.png"
    current_path = tmp_path / "current.png"

    reference_image = np.zeros(
        (50, 100, 3),
        dtype=np.uint8,
    )

    current_image = reference_image.copy()

    current_image[
        0:50,
        0:50,
    ] = 255

    assert cv2.imwrite(
        str(reference_path),
        reference_image,
    )

    assert cv2.imwrite(
        str(current_path),
        current_image,
    )

    return reference_path, current_path


def test_run_processes_only_active_configurations(
    db_session: Session,
    tmp_path: Path,
) -> None:
    reference_path, current_path = write_test_images(
        tmp_path=tmp_path,
    )

    active_configuration = create_configuration(
        db=db_session,
        reference_image_path=reference_path,
        camera_name="Active Camera",
        product_name="Active Product",
        product_sku="ACTIVE-001",
        is_active=True,
    )

    create_configuration(
        db=db_session,
        reference_image_path=reference_path,
        camera_name="Inactive Camera",
        product_name="Inactive Product",
        product_sku="INACTIVE-001",
        is_active=False,
    )

    service = MonitoringCycleService(
        db_session,
    )

    observations = service.run(
        image_paths={
            active_configuration.id: str(current_path),
        },
    )

    assert len(observations) == 1

    observation = observations[0]

    assert observation.camera_id == active_configuration.camera_id
    assert observation.product_id == active_configuration.product_id
    assert observation.detected_units == 1
    assert observation.shelf_capacity == 2
    assert observation.stock_percentage == 50.0
    assert observation.detector_name == "opencv_roi"


def test_run_raises_when_active_configuration_has_no_image(
    db_session: Session,
    tmp_path: Path,
) -> None:
    reference_path, _ = write_test_images(
        tmp_path=tmp_path,
    )

    create_configuration(
        db=db_session,
        reference_image_path=reference_path,
        camera_name="Camera Without Image",
        product_name="Product Without Image",
        product_sku="NO-IMAGE-001",
        is_active=True,
    )

    service = MonitoringCycleService(
        db_session,
    )

    try:
        service.run(
            image_paths={},
        )
    except MonitoringImagePathNotFoundError:
        pass
    else:
        raise AssertionError("MonitoringImagePathNotFoundError was not raised.")
