import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.stock_alert import StockAlert, StockAlertReason
from app.db.models.stock_observation import StockObservation


class StockAlertRepository:
    def __init__(
        self,
        db: Session,
    ) -> None:
        self._db = db

    def create(
        self,
        *,
        stock_observation_id: uuid.UUID,
        stock_percentage: float,
        threshold_percentage: float,
        reason: StockAlertReason,
    ) -> StockAlert:
        alert = StockAlert(
            stock_observation_id=stock_observation_id,
            stock_percentage=stock_percentage,
            threshold_percentage=threshold_percentage,
            reason=reason,
        )

        self._db.add(alert)
        self._db.commit()
        self._db.refresh(alert)

        return alert

    def get_by_id(
        self,
        alert_id: uuid.UUID,
    ) -> StockAlert | None:
        statement = select(StockAlert).where(
            StockAlert.id == alert_id,
        )

        return self._db.scalar(statement)

    def get_by_observation_id(
        self,
        stock_observation_id: uuid.UUID,
    ) -> StockAlert | None:
        statement = select(StockAlert).where(
            StockAlert.stock_observation_id == stock_observation_id,
        )

        return self._db.scalar(statement)

    def get_latest_for_camera_and_product(
        self,
        *,
        camera_id: uuid.UUID,
        product_id: uuid.UUID,
    ) -> StockAlert | None:
        statement = (
            select(StockAlert)
            .join(
                StockObservation,
                StockObservation.id == StockAlert.stock_observation_id,
            )
            .where(
                StockObservation.camera_id == camera_id,
                StockObservation.product_id == product_id,
            )
            .order_by(
                StockAlert.created_at.desc(),
            )
            .limit(1)
        )

        return self._db.scalar(statement)

    def get_all(
        self,
    ) -> list[StockAlert]:
        statement = select(StockAlert).order_by(
            StockAlert.created_at.desc(),
        )

        return list(self._db.scalars(statement).all())
