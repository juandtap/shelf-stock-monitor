"""add shelf capacity to shelf configurations

Revision ID: 4f8c9d2a7b31
Revises: be08fbffcc91
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "4f8c9d2a7b31"
down_revision: str | Sequence[str] | None = "be08fbffcc91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "shelf_configurations",
        sa.Column(
            "shelf_capacity",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE shelf_configurations
        SET shelf_capacity = jsonb_array_length(
            detector_config->'regions'
        )
        WHERE detector_type = 'opencv_roi'
        """
    )

    op.alter_column(
        "shelf_configurations",
        "shelf_capacity",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.create_check_constraint(
        "ck_shelf_configurations_shelf_capacity_positive",
        "shelf_configurations",
        "shelf_capacity > 0",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_shelf_configurations_shelf_capacity_positive",
        "shelf_configurations",
        type_="check",
    )

    op.drop_column(
        "shelf_configurations",
        "shelf_capacity",
    )
