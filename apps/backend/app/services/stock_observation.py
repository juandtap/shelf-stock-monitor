from sqlalchemy.orm import Session

from app.db.models.stock_observation import StockObservation
from app.repositories.camera import CameraRepository
from app.repositories.product import ProductRepository
from app.repositories.stock_observation import StockObservationRepository
from app.schemas.stock_observation import StockObservationCreate


class CameraNotFoundError(Exception):
    pass


class ProductNotFoundError(Exception):
    pass


class StockObservationService:
    def __init__(self, db: Session) -> None:
        self.camera_repository = CameraRepository(db)
        self.product_repository = ProductRepository(db)
        self.observation_repository = StockObservationRepository(db)

    def create(
        self,
        observation_data: StockObservationCreate,
    ) -> StockObservation:
        camera = self.camera_repository.get_by_id(
            observation_data.camera_id,
        )

        if camera is None:
            raise CameraNotFoundError

        product = self.product_repository.get_by_id(
            observation_data.product_id,
        )

        if product is None:
            raise ProductNotFoundError

        stock_percentage = self._calculate_stock_percentage(
            detected_units=observation_data.detected_units,
            shelf_capacity=observation_data.shelf_capacity,
        )

        return self.observation_repository.create(
            camera_id=observation_data.camera_id,
            product_id=observation_data.product_id,
            detected_units=observation_data.detected_units,
            shelf_capacity=observation_data.shelf_capacity,
            stock_percentage=stock_percentage,
            detector_name=observation_data.detector_name,
        )

    @staticmethod
    def _calculate_stock_percentage(
        *,
        detected_units: int,
        shelf_capacity: int,
    ) -> float:
        return round(
            (detected_units / shelf_capacity) * 100,
            2,
        )
