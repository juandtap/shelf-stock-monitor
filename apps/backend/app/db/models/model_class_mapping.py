import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.product import Product


class ModelClassMapping(TimestampMixin, Base):
    __tablename__ = "model_class_mappings"

    __table_args__ = (
        UniqueConstraint(
            "model_key",
            "class_id",
            name="uq_model_class_mappings_model_class",
        ),
        UniqueConstraint(
            "model_key",
            "product_id",
            name="uq_model_class_mappings_model_product",
        ),
        CheckConstraint(
            "class_id >= 0",
            name="ck_model_class_mappings_class_id_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    model_key: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    class_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    product: Mapped["Product"] = relationship()
