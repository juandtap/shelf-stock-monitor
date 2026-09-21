import uuid
from datetime import timedelta
from pathlib import Path

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.camera import Camera
from app.db.models.product import Product
from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.models.stock_alert import StockAlert
from app.repositories.model_class_mapping import ModelClassMappingRepository
from app.services.monitoring_cycle import (
    InconsistentYOLOConfigurationError,
    MonitoringCycleService,
    MonitoringImagePathNotFoundError,
)
from app.services.stock_alert import StockAlertPolicy
from app.vision.detector import ImageArray, StockDetector
from app.vision.models import ClassDetection, StockDetectionResult

ImageArrayND = NDArray[np.uint8]

TEST_MODEL_KEY = "test-model"


class FakeNotificationProvider:
    def __init__(self) -> None:
        self.sent_alerts: list[StockAlert] = []

    def send_low_stock_alert(
        self,
        alert: StockAlert,
    ) -> None:
        self.sent_alerts.append(alert)


class FakeMulticlassDetector:
    def __init__(
        self,
        class_detections: tuple[ClassDetection, ...],
    ) -> None:
        self._class_detections = class_detections
        self.call_count = 0

    @property
    def name(self) -> str:
        return "yolo"

    def detect(
        self,
        image: ImageArray,
    ) -> StockDetectionResult:
        self.call_count += 1

        return StockDetectionResult(
            detected_units=sum(detection.detected_units for detection in self._class_detections),
            detector_name=self.name,
            class_detections=self._class_detections,
        )


class FakeDetectorFactory:
    def __init__(
        self,
        detector: StockDetector,
    ) -> None:
        self._detector = detector
        self.call_count = 0

    def create(
        self,
        configuration: ShelfConfiguration,
    ) -> StockDetector:
        self.call_count += 1
        return self._detector


def create_alert_policy() -> StockAlertPolicy:
    return StockAlertPolicy(
        drop_percentage=15.0,
        reminder_interval=timedelta(minutes=60),
    )


def create_monitoring_service(
    db_session: Session,
    *,
    detector_factory: FakeDetectorFactory | None = None,
) -> tuple[MonitoringCycleService, FakeNotificationProvider]:
    notification_provider = FakeNotificationProvider()

    service = MonitoringCycleService(
        db_session,
        alert_policy=create_alert_policy(),
        notification_provider=notification_provider,
        detector_factory=detector_factory,
    )

    return service, notification_provider


def create_test_image(
    path: Path,
    *,
    occupied: bool,
) -> None:
    image: ImageArrayND = np.zeros(
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
        raise RuntimeError(
            f"Could not save test image: {path}",
        )


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
        shelf_capacity=2,
        low_stock_threshold=low_stock_threshold,
        is_active=is_active,
    )

    db_session.add(configuration)
    db_session.commit()
    db_session.refresh(configuration)

    return configuration


def create_camera(
    db_session: Session,
) -> Camera:
    camera = Camera(
        name=f"YOLO Camera {uuid.uuid4()}",
        location="Test Shelf",
    )

    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)

    return camera


def create_product(
    db_session: Session,
    *,
    name: str,
) -> Product:
    product = Product(
        name=name,
        sku=f"YOLO-{uuid.uuid4()}",
    )

    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    return product


def create_yolo_configuration(
    db_session: Session,
    *,
    camera: Camera,
    product: Product,
    shelf_capacity: int,
    low_stock_threshold: float = 50.0,
    model_key: str = TEST_MODEL_KEY,
    confidence_threshold: float = 0.25,
) -> ShelfConfiguration:
    configuration = ShelfConfiguration(
        camera_id=camera.id,
        product_id=product.id,
        detector_type="yolo",
        reference_image_path=None,
        detector_config={
            "model_key": model_key,
            "model_path": "models/test-model.pt",
            "confidence_threshold": confidence_threshold,
            "iou_threshold": 0.7,
            "image_size": 640,
            "class_ids": None,
            "device": "cpu",
        },
        shelf_capacity=shelf_capacity,
        low_stock_threshold=low_stock_threshold,
        is_active=True,
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

    service, notification_provider = create_monitoring_service(
        db_session,
    )

    observations = service.run(
        image_paths={
            active_configuration.camera_id: str(active_current),
            inactive_configuration.camera_id: str(inactive_current),
        }
    )

    assert len(observations) == 1

    observation = observations[0]

    assert observation.camera_id == active_configuration.camera_id
    assert observation.detected_units == 1
    assert observation.shelf_capacity == 2
    assert observation.stock_percentage == 50.0

    assert notification_provider.sent_alerts == []


def test_cycle_raises_when_active_camera_has_no_image(
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

    service, _ = create_monitoring_service(
        db_session,
    )

    try:
        service.run(
            image_paths={},
        )
    except MonitoringImagePathNotFoundError:
        return

    raise AssertionError(
        "MonitoringImagePathNotFoundError was not raised.",
    )


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

    service, notification_provider = create_monitoring_service(
        db_session,
    )

    observations = service.run(
        image_paths={
            configuration.camera_id: str(current),
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

    assert len(notification_provider.sent_alerts) == 1
    assert notification_provider.sent_alerts[0].id == alert.id


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

    service, notification_provider = create_monitoring_service(
        db_session,
    )

    observations = service.run(
        image_paths={
            configuration.camera_id: str(current),
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
    assert notification_provider.sent_alerts == []


def test_cycle_runs_yolo_once_for_multiple_products(
    db_session: Session,
    tmp_path: Path,
) -> None:
    current = tmp_path / "yolo_current.png"

    create_test_image(
        current,
        occupied=True,
    )

    camera = create_camera(
        db_session,
    )

    coca_cola = create_product(
        db_session,
        name="Coca-Cola",
    )

    water = create_product(
        db_session,
        name="Water",
    )

    create_yolo_configuration(
        db_session,
        camera=camera,
        product=coca_cola,
        shelf_capacity=4,
        low_stock_threshold=50.0,
    )

    create_yolo_configuration(
        db_session,
        camera=camera,
        product=water,
        shelf_capacity=4,
        low_stock_threshold=60.0,
    )

    mapping_repository = ModelClassMappingRepository(
        db_session,
    )

    mapping_repository.create(
        model_key=TEST_MODEL_KEY,
        class_id=0,
        product_id=coca_cola.id,
    )

    mapping_repository.create(
        model_key=TEST_MODEL_KEY,
        class_id=1,
        product_id=water.id,
    )

    detector = FakeMulticlassDetector(
        (
            ClassDetection(
                class_id=0,
                detected_units=3,
            ),
            ClassDetection(
                class_id=1,
                detected_units=2,
            ),
        )
    )

    detector_factory = FakeDetectorFactory(
        detector,
    )

    service, notification_provider = create_monitoring_service(
        db_session,
        detector_factory=detector_factory,
    )

    observations = service.run(
        image_paths={
            camera.id: str(current),
        }
    )

    observations_by_product = {observation.product_id: observation for observation in observations}

    assert len(observations) == 2

    assert detector_factory.call_count == 1
    assert detector.call_count == 1

    coca_cola_observation = observations_by_product[coca_cola.id]
    water_observation = observations_by_product[water.id]

    assert coca_cola_observation.detected_units == 3
    assert coca_cola_observation.stock_percentage == 75.0

    assert water_observation.detected_units == 2
    assert water_observation.stock_percentage == 50.0

    assert len(notification_provider.sent_alerts) == 1

    alert = notification_provider.sent_alerts[0]

    assert alert.stock_observation_id == water_observation.id
    assert alert.stock_percentage == 50.0
    assert alert.threshold_percentage == 60.0


def test_cycle_rejects_inconsistent_yolo_configurations_before_inference(
    db_session: Session,
    tmp_path: Path,
) -> None:
    current = tmp_path / "inconsistent_yolo.png"

    create_test_image(
        current,
        occupied=True,
    )

    camera = create_camera(
        db_session,
    )

    coca_cola = create_product(
        db_session,
        name="Coca-Cola",
    )

    water = create_product(
        db_session,
        name="Water",
    )

    create_yolo_configuration(
        db_session,
        camera=camera,
        product=coca_cola,
        shelf_capacity=4,
        confidence_threshold=0.25,
    )

    create_yolo_configuration(
        db_session,
        camera=camera,
        product=water,
        shelf_capacity=4,
        confidence_threshold=0.50,
    )

    detector = FakeMulticlassDetector(())

    detector_factory = FakeDetectorFactory(
        detector,
    )

    service, _ = create_monitoring_service(
        db_session,
        detector_factory=detector_factory,
    )

    with pytest.raises(
        InconsistentYOLOConfigurationError,
    ):
        service.run(
            image_paths={
                camera.id: str(current),
            }
        )

    assert detector_factory.call_count == 0
    assert detector.call_count == 0
