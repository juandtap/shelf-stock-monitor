import uuid

import numpy as np
from sqlalchemy.orm import Session

from app.db.models.camera import Camera
from app.db.models.product import Product
from app.services.stock_detection import StockDetectionService
from app.vision.detector import ImageArray
from app.vision.models import StockDetectionResult


class FakeDetector:
    @property
    def name(self) -> str:
        return "fake_detector"

    def detect(self, image: ImageArray) -> StockDetectionResult:
        return StockDetectionResult(
            detected_units=3,
            shelf_capacity=6,
            detector_name=self.name,
        )


def create_camera(db_session: Session) -> Camera:
    camera = Camera(
        name=f"Detection Camera {uuid.uuid4()}",
        location="Test Shelf",
    )

    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)

    return camera


def create_product(db_session: Session) -> Product:
    product = Product(
        name="Detection Test Product",
        sku=f"DETECTION-{uuid.uuid4()}",
    )

    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    return product


def test_process_detection_creates_stock_observation(
    db_session: Session,
) -> None:
    camera = create_camera(db_session)
    product = create_product(db_session)

    detector = FakeDetector()

    service = StockDetectionService(
        db=db_session,
        detector=detector,
    )

    image = np.zeros(
        (100, 100, 3),
        dtype=np.uint8,
    )

    observation = service.process(
        image=image,
        camera_id=camera.id,
        product_id=product.id,
    )

    assert observation.camera_id == camera.id
    assert observation.product_id == product.id

    assert observation.detected_units == 3
    assert observation.shelf_capacity == 6
    assert observation.stock_percentage == 50.0
    assert observation.detector_name == "fake_detector"


def test_service_accepts_stock_detector_protocol(
    db_session: Session,
) -> None:
    camera = create_camera(db_session)
    product = create_product(db_session)

    service = StockDetectionService(
        db=db_session,
        detector=FakeDetector(),
    )

    image = np.zeros(
        (50, 50, 3),
        dtype=np.uint8,
    )

    observation = service.process(
        image=image,
        camera_id=camera.id,
        product_id=product.id,
    )

    assert observation.detector_name == "fake_detector"
