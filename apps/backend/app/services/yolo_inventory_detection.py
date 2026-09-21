import uuid

from sqlalchemy.orm import Session

from app.db.models.stock_observation import StockObservation
from app.repositories.model_class_mapping import ModelClassMappingRepository
from app.repositories.shelf_configuration import ShelfConfigurationRepository
from app.services.stock_detection import StockDetectionService
from app.vision.detector import ImageArray, StockDetector


class ModelClassMappingNotFoundError(Exception):
    pass


class YOLOInventoryDetectionService:
    def __init__(
        self,
        db: Session,
        detector: StockDetector,
    ) -> None:
        self._detection_service = StockDetectionService(
            db=db,
            detector=detector,
        )
        self._mapping_repository = ModelClassMappingRepository(db)
        self._configuration_repository = ShelfConfigurationRepository(db)

    def process(
        self,
        *,
        image: ImageArray,
        camera_id: uuid.UUID,
        model_key: str,
    ) -> list[StockObservation]:
        configurations = self._configuration_repository.get_active_by_camera(
            camera_id,
        )

        yolo_configurations = [
            configuration
            for configuration in configurations
            if configuration.detector_type == "yolo"
        ]

        if not yolo_configurations:
            return []

        mappings = self._mapping_repository.get_by_model(
            model_key,
        )

        mappings_by_product = {mapping.product_id: mapping for mapping in mappings}

        for configuration in yolo_configurations:
            if configuration.product_id not in mappings_by_product:
                raise ModelClassMappingNotFoundError(
                    "No model class mapping found for "
                    f"product {configuration.product_id} "
                    f"using model {model_key}.",
                )

        detection = self._detection_service.detect(
            image=image,
        )

        counts_by_class = {
            class_detection.class_id: class_detection.detected_units
            for class_detection in detection.class_detections
        }

        observations: list[StockObservation] = []

        for configuration in yolo_configurations:
            mapping = mappings_by_product[configuration.product_id]

            detected_units = counts_by_class.get(
                mapping.class_id,
                0,
            )

            observation = self._detection_service.create_observation(
                detection=detection,
                camera_id=camera_id,
                product_id=configuration.product_id,
                shelf_capacity=configuration.shelf_capacity,
                detected_units=detected_units,
            )

            observations.append(observation)

        return observations
