import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.stock_observation import StockObservation


class StockObservationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        camera_id: uuid.UUID,
        product_id: uuid.UUID,
        detected_units: int,
        shelf_capacity: int,
        stock_percentage: float,
        detector_name: str,
    ) -> StockObservation:
        observation = StockObservation(
            camera_id=camera_id,
            product_id=product_id,
            detected_units=detected_units,
            shelf_capacity=shelf_capacity,
            stock_percentage=stock_percentage,
            detector_name=detector_name,
        )

        self.db.add(observation)
        self.db.commit()
        self.db.refresh(observation)

        return observation

    def get_by_id(
        self,
        observation_id: uuid.UUID,
    ) -> StockObservation | None:
        statement = select(StockObservation).where(
            StockObservation.id == observation_id,
        )

        return self.db.scalar(statement)

    def get_all(self) -> list[StockObservation]:
        statement = select(StockObservation).order_by(
            StockObservation.captured_at.desc(),
        )

        return list(self.db.scalars(statement).all())
