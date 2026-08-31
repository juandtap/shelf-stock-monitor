import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.camera import Camera
    from app.db.models.product import Product


class ShelfConfiguration(TimestampMixin, Base):
    __tablename__ = "shelf_configurations"
    __table_args__ = (
        UniqueConstraint(
            "camera_id",
            "product_id",
            name="uq_shelf_configurations_camera_product",
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

    detector_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    reference_image_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    detector_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    camera: Mapped["Camera"] = relationship()
    product: Mapped["Product"] = relationship()
