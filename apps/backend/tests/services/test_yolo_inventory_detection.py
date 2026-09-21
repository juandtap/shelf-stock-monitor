import uuid

import numpy as np
import pytest
from sqlalchemy.orm import Session

from app.db.models.camera import Camera
from app.db.models.product import Product
from app.db.models.shelf_configuration import ShelfConfiguration
from app.repositories.model_class_mapping import ModelClassMappingRepository
from app.services.yolo_inventory_detection import (
    ModelClassMappingNotFoundError,
    YOLOInventoryDetectionService,
)
from app.vision.detector import ImageArray
from app.vision.models import (
    ClassDetection,
    StockDetectionResult,
)

TEST_MODEL_KEY = "test-model"


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
) -> ShelfConfiguration:
    configuration = ShelfConfiguration(
        camera_id=camera.id,
        product_id=product.id,
        detector_type="yolo",
        reference_image_path=None,
        detector_config={
            "model_key": TEST_MODEL_KEY,
            "model_path": "model.pt",
            "confidence_threshold": 0.25,
            "iou_threshold": 0.7,
            "image_size": 640,
            "class_ids": None,
            "device": None,
        },
        shelf_capacity=shelf_capacity,
        low_stock_threshold=50.0,
        is_active=True,
    )

    db_session.add(configuration)
    db_session.commit()
    db_session.refresh(configuration)

    return configuration


def test_process_creates_observation_for_each_configured_product(
    db_session: Session,
) -> None:
    camera = create_camera(db_session)

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
    )
    create_yolo_configuration(
        db_session,
        camera=camera,
        product=water,
        shelf_capacity=4,
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
        ),
    )

    service = YOLOInventoryDetectionService(
        db=db_session,
        detector=detector,
    )

    image = np.zeros(
        (100, 100, 3),
        dtype=np.uint8,
    )

    observations = service.process(
        image=image,
        camera_id=camera.id,
        model_key=TEST_MODEL_KEY,
    )

    observations_by_product = {observation.product_id: observation for observation in observations}

    assert len(observations) == 2
    assert detector.call_count == 1

    assert observations_by_product[coca_cola.id].detected_units == 3
    assert observations_by_product[coca_cola.id].stock_percentage == 75.0

    assert observations_by_product[water.id].detected_units == 2
    assert observations_by_product[water.id].stock_percentage == 50.0


def test_missing_detection_creates_zero_stock_observation(
    db_session: Session,
) -> None:
    camera = create_camera(db_session)

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
    )
    create_yolo_configuration(
        db_session,
        camera=camera,
        product=water,
        shelf_capacity=4,
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
                class_id=1,
                detected_units=2,
            ),
        ),
    )

    service = YOLOInventoryDetectionService(
        db=db_session,
        detector=detector,
    )

    image = np.zeros(
        (100, 100, 3),
        dtype=np.uint8,
    )

    observations = service.process(
        image=image,
        camera_id=camera.id,
        model_key=TEST_MODEL_KEY,
    )

    observations_by_product = {observation.product_id: observation for observation in observations}

    assert detector.call_count == 1
    assert observations_by_product[coca_cola.id].detected_units == 0
    assert observations_by_product[coca_cola.id].stock_percentage == 0.0

    assert observations_by_product[water.id].detected_units == 2


def test_missing_mapping_fails_before_inference(
    db_session: Session,
) -> None:
    camera = create_camera(db_session)

    product = create_product(
        db_session,
        name="Unmapped Product",
    )

    create_yolo_configuration(
        db_session,
        camera=camera,
        product=product,
        shelf_capacity=4,
    )

    detector = FakeMulticlassDetector(())

    service = YOLOInventoryDetectionService(
        db=db_session,
        detector=detector,
    )

    image = np.zeros(
        (100, 100, 3),
        dtype=np.uint8,
    )

    with pytest.raises(
        ModelClassMappingNotFoundError,
    ):
        service.process(
            image=image,
            camera_id=camera.id,
            model_key=TEST_MODEL_KEY,
        )

    assert detector.call_count == 0


def test_camera_without_yolo_configurations_skips_inference(
    db_session: Session,
) -> None:
    camera = create_camera(db_session)

    detector = FakeMulticlassDetector(())

    service = YOLOInventoryDetectionService(
        db=db_session,
        detector=detector,
    )

    image = np.zeros(
        (100, 100, 3),
        dtype=np.uint8,
    )

    observations = service.process(
        image=image,
        camera_id=camera.id,
        model_key=TEST_MODEL_KEY,
    )

    assert observations == []
    assert detector.call_count == 0
