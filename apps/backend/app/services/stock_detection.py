import uuid

from sqlalchemy.orm import Session

from app.db.models.stock_observation import StockObservation
from app.schemas.stock_observation import StockObservationCreate
from app.services.stock_observation import StockObservationService
from app.vision.detector import ImageArray, StockDetector
from app.vision.models import StockDetectionResult


class StockDetectionService:
    def __init__(
        self,
        db: Session,
        detector: StockDetector,
    ) -> None:
        self._detector = detector
        self._observation_service = StockObservationService(db)

    def detect(
        self,
        *,
        image: ImageArray,
    ) -> StockDetectionResult:
        return self._detector.detect(image)

    def create_observation(
        self,
        *,
        detection: StockDetectionResult,
        camera_id: uuid.UUID,
        product_id: uuid.UUID,
        shelf_capacity: int,
        detected_units: int | None = None,
    ) -> StockObservation:
        observation_data = StockObservationCreate(
            camera_id=camera_id,
            product_id=product_id,
            detected_units=(detection.detected_units if detected_units is None else detected_units),
            shelf_capacity=shelf_capacity,
            detector_name=detection.detector_name,
        )

        return self._observation_service.create(
            observation_data,
        )

    def process(
        self,
        *,
        image: ImageArray,
        camera_id: uuid.UUID,
        product_id: uuid.UUID,
        shelf_capacity: int,
    ) -> StockObservation:
        detection = self.detect(
            image=image,
        )

        return self.create_observation(
            detection=detection,
            camera_id=camera_id,
            product_id=product_id,
            shelf_capacity=shelf_capacity,
        )
