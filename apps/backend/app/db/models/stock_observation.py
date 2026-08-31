import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.camera import Camera
    from app.db.models.product import Product


class StockObservation(TimestampMixin, Base):
    __tablename__ = "stock_observations"
    __table_args__ = (
        CheckConstraint(
            "detected_units >= 0",
            name="ck_stock_observations_detected_units_non_negative",
        ),
        CheckConstraint(
            "shelf_capacity > 0",
            name="ck_stock_observations_shelf_capacity_positive",
        ),
        CheckConstraint(
            "stock_percentage >= 0 AND stock_percentage <= 100",
            name="ck_stock_observations_percentage_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    detected_units: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    shelf_capacity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    stock_percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    detector_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    camera: Mapped["Camera"] = relationship(
        back_populates="stock_observations",
    )

    product: Mapped["Product"] = relationship(
        back_populates="stock_observations",
    )
