import uuid
from typing import Literal

from sqlalchemy import CheckConstraint, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin
from app.db.models.stock_observation import StockObservation

StockAlertReason = Literal[
    "legacy_low_stock",
    "initial_low_stock",
    "entered_low_stock",
    "significant_stock_drop",
    "low_stock_reminder",
]


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
        CheckConstraint(
            "reason IN ("
            "'legacy_low_stock', "
            "'initial_low_stock', "
            "'entered_low_stock', "
            "'significant_stock_drop', "
            "'low_stock_reminder'"
            ")",
            name="ck_stock_alerts_reason",
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

    reason: Mapped[StockAlertReason] = mapped_column(
        String(length=50),
        nullable=False,
    )

    stock_observation: Mapped[StockObservation] = relationship()
