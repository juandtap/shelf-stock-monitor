from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.camera import Camera
from app.db.models.product import Product
from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.models.stock_alert import StockAlert
from app.services.monitoring_cycle import (
    MonitoringCycleService,
    MonitoringImagePathNotFoundError,
)

ImageArray = NDArray[np.uint8]


def create_test_image(
    path: Path,
    *,
    occupied: bool,
) -> None:
    image: ImageArray = np.zeros(
        (100, 200, 3),
        dtype=np.uint8,
    )

    if occupied:
        image[:, :100] = 255

    saved = cv2.imwrite(
        str(path),
        image,
    )

    if not saved:
        raise RuntimeError(f"Could not save test image: {path}")


def create_configuration(
    db_session: Session,
    *,
    reference_path: Path,
    is_active: bool = True,
    low_stock_threshold: float = 50.0,
) -> ShelfConfiguration:
    camera = Camera(
        name=f"Camera {reference_path.stem}",
        location="Test Shelf",
    )

    product = Product(
        name=f"Product {reference_path.stem}",
        sku=f"SKU-{reference_path.stem}",
    )

    db_session.add_all(
        [
            camera,
            product,
        ]
    )

    db_session.flush()

    configuration = ShelfConfiguration(
        camera_id=camera.id,
        product_id=product.id,
        detector_type="opencv_roi",
        reference_image_path=str(reference_path),
        detector_config={
            "difference_threshold": 20.0,
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
        low_stock_threshold=low_stock_threshold,
        is_active=is_active,
    )

    db_session.add(configuration)
    db_session.commit()
    db_session.refresh(configuration)

    return configuration


def test_cycle_processes_only_active_configurations(
    db_session: Session,
    tmp_path: Path,
) -> None:
    active_reference = tmp_path / "active_reference.png"
    inactive_reference = tmp_path / "inactive_reference.png"

    active_current = tmp_path / "active_current.png"
    inactive_current = tmp_path / "inactive_current.png"

    create_test_image(
        active_reference,
        occupied=False,
    )
    create_test_image(
        inactive_reference,
        occupied=False,
    )

    create_test_image(
        active_current,
        occupied=True,
    )
    create_test_image(
        inactive_current,
        occupied=True,
    )

    active_configuration = create_configuration(
        db_session,
        reference_path=active_reference,
        is_active=True,
    )

    inactive_configuration = create_configuration(
        db_session,
        reference_path=inactive_reference,
        is_active=False,
    )

    service = MonitoringCycleService(
        db_session,
    )

    observations = service.run(
        image_paths={
            active_configuration.id: str(active_current),
            inactive_configuration.id: str(inactive_current),
        }
    )

    assert len(observations) == 1

    observation = observations[0]

    assert observation.camera_id == active_configuration.camera_id
    assert observation.detected_units == 1
    assert observation.shelf_capacity == 2
    assert observation.stock_percentage == 50.0


def test_cycle_raises_when_active_configuration_has_no_image(
    db_session: Session,
    tmp_path: Path,
) -> None:
    reference = tmp_path / "reference.png"

    create_test_image(
        reference,
        occupied=False,
    )

    create_configuration(
        db_session,
        reference_path=reference,
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
        return

    raise AssertionError("MonitoringImagePathNotFoundError was not raised.")


def test_cycle_creates_low_stock_alert(
    db_session: Session,
    tmp_path: Path,
) -> None:
    reference = tmp_path / "alert_reference.png"
    current = tmp_path / "alert_current.png"

    create_test_image(
        reference,
        occupied=False,
    )

    create_test_image(
        current,
        occupied=False,
    )

    configuration = create_configuration(
        db_session,
        reference_path=reference,
        is_active=True,
        low_stock_threshold=50.0,
    )

    service = MonitoringCycleService(
        db_session,
    )

    observations = service.run(
        image_paths={
            configuration.id: str(current),
        }
    )

    assert len(observations) == 1

    observation = observations[0]

    assert observation.detected_units == 0
    assert observation.stock_percentage == 0.0

    statement = select(StockAlert).where(
        StockAlert.stock_observation_id == observation.id,
    )

    alert = db_session.scalar(statement)

    assert alert is not None
    assert alert.stock_percentage == 0.0
    assert alert.threshold_percentage == 50.0


def test_cycle_does_not_create_alert_at_threshold(
    db_session: Session,
    tmp_path: Path,
) -> None:
    reference = tmp_path / "normal_reference.png"
    current = tmp_path / "normal_current.png"

    create_test_image(
        reference,
        occupied=False,
    )

    create_test_image(
        current,
        occupied=True,
    )

    configuration = create_configuration(
        db_session,
        reference_path=reference,
        is_active=True,
        low_stock_threshold=50.0,
    )

    service = MonitoringCycleService(
        db_session,
    )

    observations = service.run(
        image_paths={
            configuration.id: str(current),
        }
    )

    assert len(observations) == 1

    observation = observations[0]

    assert observation.stock_percentage == 50.0

    statement = select(StockAlert).where(
        StockAlert.stock_observation_id == observation.id,
    )

    alert = db_session.scalar(statement)

    assert alert is None
