import uuid

from sqlalchemy.orm import Session

from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.models.stock_observation import StockObservation
from app.repositories.camera import CameraRepository
from app.repositories.product import ProductRepository
from app.repositories.shelf_configuration import ShelfConfigurationRepository
from app.schemas.shelf_configuration import ShelfConfigurationCreate
from app.services.shelf_monitoring import ShelfMonitoringService


class ShelfConfigurationCameraNotFoundError(Exception):
    pass


class ShelfConfigurationProductNotFoundError(Exception):
    pass


class ShelfConfigurationAlreadyExistsError(Exception):
    pass


class ShelfConfigurationNotFoundError(Exception):
    pass


class ShelfConfigurationService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._camera_repository = CameraRepository(db)
        self._product_repository = ProductRepository(db)
        self._configuration_repository = ShelfConfigurationRepository(db)

    def create(
        self,
        configuration_data: ShelfConfigurationCreate,
    ) -> ShelfConfiguration:
        camera = self._camera_repository.get_by_id(
            configuration_data.camera_id,
        )

        if camera is None:
            raise ShelfConfigurationCameraNotFoundError

        product = self._product_repository.get_by_id(
            configuration_data.product_id,
        )

        if product is None:
            raise ShelfConfigurationProductNotFoundError

        existing_configuration = self._configuration_repository.get_by_camera_and_product(
            camera_id=configuration_data.camera_id,
            product_id=configuration_data.product_id,
        )

        if existing_configuration is not None:
            raise ShelfConfigurationAlreadyExistsError

        return self._configuration_repository.create(
            configuration_data,
        )

    def monitor(
        self,
        *,
        configuration_id: uuid.UUID,
        image_path: str,
    ) -> StockObservation:
        configuration = self._configuration_repository.get_by_id(
            configuration_id,
        )

        if configuration is None:
            raise ShelfConfigurationNotFoundError

        monitoring_service = ShelfMonitoringService(
            db=self._db,
        )

        return monitoring_service.process(
            configuration=configuration,
            image_path=image_path,
        )
