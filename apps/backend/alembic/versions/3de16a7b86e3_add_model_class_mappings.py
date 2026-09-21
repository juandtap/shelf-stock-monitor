"""add model class mappings

Revision ID: 3de16a7b86e3
Revises: 7c1d8f2e4a90
Create Date: 2026-09-21 14:22:56.640031
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3de16a7b86e3"
down_revision: str | Sequence[str] | None = "7c1d8f2e4a90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_class_mappings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "model_key",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "class_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "class_id >= 0",
            name="ck_model_class_mappings_class_id_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "model_key",
            "class_id",
            name="uq_model_class_mappings_model_class",
        ),
        sa.UniqueConstraint(
            "model_key",
            "product_id",
            name="uq_model_class_mappings_model_product",
        ),
    )

    op.create_index(
        op.f("ix_model_class_mappings_model_key"),
        "model_class_mappings",
        ["model_key"],
        unique=False,
    )

    op.create_index(
        op.f("ix_model_class_mappings_product_id"),
        "model_class_mappings",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_model_class_mappings_product_id"),
        table_name="model_class_mappings",
    )

    op.drop_index(
        op.f("ix_model_class_mappings_model_key"),
        table_name="model_class_mappings",
    )

    op.drop_table("model_class_mappings")
