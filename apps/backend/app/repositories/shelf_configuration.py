import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.shelf_configuration import ShelfConfiguration
from app.schemas.shelf_configuration import ShelfConfigurationCreate


class ShelfConfigurationRepository:
    def __init__(
        self,
        db: Session,
    ) -> None:
        self.db = db

    def create(
        self,
        configuration_data: ShelfConfigurationCreate,
    ) -> ShelfConfiguration:
        configuration = ShelfConfiguration(
            camera_id=configuration_data.camera_id,
            product_id=configuration_data.product_id,
            detector_type=configuration_data.detector_type,
            reference_image_path=configuration_data.reference_image_path,
            detector_config=configuration_data.detector_config.model_dump(),
            shelf_capacity=configuration_data.shelf_capacity,
            low_stock_threshold=configuration_data.low_stock_threshold,
        )

        self.db.add(configuration)
        self.db.commit()
        self.db.refresh(configuration)

        return configuration

    def get_by_id(
        self,
        configuration_id: uuid.UUID,
    ) -> ShelfConfiguration | None:
        statement = select(ShelfConfiguration).where(
            ShelfConfiguration.id == configuration_id,
        )

        return self.db.scalar(statement)

    def get_by_camera_and_product(
        self,
        *,
        camera_id: uuid.UUID,
        product_id: uuid.UUID,
    ) -> ShelfConfiguration | None:
        statement = select(ShelfConfiguration).where(
            ShelfConfiguration.camera_id == camera_id,
            ShelfConfiguration.product_id == product_id,
        )

        return self.db.scalar(statement)

    def get_all(
        self,
    ) -> list[ShelfConfiguration]:
        statement = select(ShelfConfiguration).order_by(
            ShelfConfiguration.created_at.desc(),
        )

        return list(self.db.scalars(statement).all())

    def get_active(
        self,
    ) -> list[ShelfConfiguration]:
        statement = (
            select(ShelfConfiguration)
            .where(
                ShelfConfiguration.is_active.is_(True),
            )
            .order_by(
                ShelfConfiguration.created_at.desc(),
            )
        )

        return list(self.db.scalars(statement).all())

    def get_active_by_camera(
        self,
        camera_id: uuid.UUID,
    ) -> list[ShelfConfiguration]:
        statement = (
            select(ShelfConfiguration)
            .where(
                ShelfConfiguration.camera_id == camera_id,
                ShelfConfiguration.is_active.is_(True),
            )
            .order_by(
                ShelfConfiguration.created_at.asc(),
            )
        )

        return list(self.db.scalars(statement).all())
