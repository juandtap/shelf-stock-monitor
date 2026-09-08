from sqlalchemy.orm import Session

from app.db.models.shelf_configuration import ShelfConfiguration
from app.db.models.stock_observation import StockObservation
from app.repositories.shelf_configuration import ShelfConfigurationRepository
from app.repositories.stock_observation import StockObservationRepository
from app.schemas.inventory_status import (
    InventoryState,
    InventoryStatusResponse,
)


class InventoryStatusService:
    def __init__(
        self,
        db: Session,
    ) -> None:
        self.configuration_repository = ShelfConfigurationRepository(db)
        self.observation_repository = StockObservationRepository(db)

    def get_statuses(
        self,
    ) -> list[InventoryStatusResponse]:
        configurations = self.configuration_repository.get_active()

        statuses = [self._build_status(configuration) for configuration in configurations]

        return sorted(
            statuses,
            key=lambda status: (
                status.product_name.lower(),
                status.camera_name.lower(),
            ),
        )

    def _build_status(
        self,
        configuration: ShelfConfiguration,
    ) -> InventoryStatusResponse:
        observation = self.observation_repository.get_latest_for_camera_and_product(
            camera_id=configuration.camera_id,
            product_id=configuration.product_id,
        )

        if observation is None:
            return self._build_unknown_status(
                configuration,
            )

        return self._build_observed_status(
            configuration,
            observation,
        )

    def _build_unknown_status(
        self,
        configuration: ShelfConfiguration,
    ) -> InventoryStatusResponse:
        return InventoryStatusResponse(
            configuration_id=configuration.id,
            camera_id=configuration.camera_id,
            camera_name=configuration.camera.name,
            product_id=configuration.product_id,
            product_name=configuration.product.name,
            product_sku=configuration.product.sku,
            detected_units=None,
            shelf_capacity=configuration.shelf_capacity,
            stock_percentage=None,
            low_stock_threshold=configuration.low_stock_threshold,
            status="unknown",
            detector_name=None,
            captured_at=None,
        )

    def _build_observed_status(
        self,
        configuration: ShelfConfiguration,
        observation: StockObservation,
    ) -> InventoryStatusResponse:
        state = self._resolve_state(
            stock_percentage=observation.stock_percentage,
            low_stock_threshold=configuration.low_stock_threshold,
        )

        return InventoryStatusResponse(
            configuration_id=configuration.id,
            camera_id=configuration.camera_id,
            camera_name=configuration.camera.name,
            product_id=configuration.product_id,
            product_name=configuration.product.name,
            product_sku=configuration.product.sku,
            detected_units=observation.detected_units,
            shelf_capacity=observation.shelf_capacity,
            stock_percentage=observation.stock_percentage,
            low_stock_threshold=configuration.low_stock_threshold,
            status=state,
            detector_name=observation.detector_name,
            captured_at=observation.captured_at,
        )

    @staticmethod
    def _resolve_state(
        *,
        stock_percentage: float,
        low_stock_threshold: float,
    ) -> InventoryState:
        if stock_percentage < low_stock_threshold:
            return "low_stock"

        return "ok"
