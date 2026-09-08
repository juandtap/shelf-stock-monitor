from pathlib import Path
from typing import cast

import cv2
from sqlalchemy.orm import Session

from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.models.stock_observation import StockObservation
from app.services.stock_detection import StockDetectionService
from app.vision.detector import ImageArray
from app.vision.factory import StockDetectorFactory


class CurrentImageNotFoundError(Exception):
    pass


class InvalidCurrentImageError(Exception):
    pass


class ShelfMonitoringService:
    def __init__(
        self,
        db: Session,
        detector_factory: StockDetectorFactory | None = None,
    ) -> None:
        self._db = db
        self._detector_factory = detector_factory or StockDetectorFactory()

    def process(
        self,
        *,
        configuration: ShelfConfiguration,
        image_path: str,
    ) -> StockObservation:
        image = self._load_image(image_path)

        detector = self._detector_factory.create(
            configuration,
        )

        detection_service = StockDetectionService(
            db=self._db,
            detector=detector,
        )

        return detection_service.process(
            image=image,
            camera_id=configuration.camera_id,
            product_id=configuration.product_id,
            shelf_capacity=configuration.shelf_capacity,
        )

    @staticmethod
    def _load_image(image_path: str) -> ImageArray:
        path = Path(image_path)

        if not path.is_file():
            raise CurrentImageNotFoundError(f"Current image not found: {path}")

        image_raw = cv2.imread(
            str(path),
            cv2.IMREAD_COLOR,
        )

        if image_raw is None:
            raise InvalidCurrentImageError(f"Unable to read current image: {path}")

        return cast(ImageArray, image_raw)
