import uuid

from sqlalchemy import CheckConstraint, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin
from app.db.models.stock_observation import StockObservation


class StockAlert(TimestampMixin, Base):
    __tablename__ = "stock_alerts"

    __table_args__ = (
        CheckConstraint(
            "stock_percentage >= 0 AND stock_percentage <= 100",
            name="ck_stock_alerts_stock_percentage",
        ),
        CheckConstraint(
            "threshold_percentage >= 0 AND threshold_percentage <= 100",
            name="ck_stock_alerts_threshold_percentage",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    stock_observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "stock_observations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    stock_percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    threshold_percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    stock_observation: Mapped[StockObservation] = relationship()
