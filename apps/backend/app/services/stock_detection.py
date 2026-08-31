# Fake detector
import uuid

from sqlalchemy.orm import Session

from app.db.models.stock_observation import StockObservation
from app.schemas.stock_observation import StockObservationCreate
from app.services.stock_observation import StockObservationService
from app.vision.detector import ImageArray, StockDetector


class StockDetectionService:
    def __init__(
        self,
        db: Session,
        detector: StockDetector,
    ) -> None:
        self._detector = detector
        self._observation_service = StockObservationService(db)

    def process(
        self,
        *,
        image: ImageArray,
        camera_id: uuid.UUID,
        product_id: uuid.UUID,
    ) -> StockObservation:
        detection = self._detector.detect(image)

        observation_data = StockObservationCreate(
            camera_id=camera_id,
            product_id=product_id,
            detected_units=detection.detected_units,
            shelf_capacity=detection.shelf_capacity,
            detector_name=detection.detector_name,
        )

        return self._observation_service.create(observation_data)
