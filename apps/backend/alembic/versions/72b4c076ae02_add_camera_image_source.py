"""add camera image source

Revision ID: 72b4c076ae02
Revises: 3de16a7b86e3
Create Date: 2026-09-21 16:04:11.272265
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "72b4c076ae02"
down_revision: str | Sequence[str] | None = "3de16a7b86e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "cameras",
        sa.Column(
            "source_type",
            sa.String(length=50),
            nullable=False,
            server_default="file",
        ),
    )

    op.add_column(
        "cameras",
        sa.Column(
            "source_uri",
            sa.String(length=1000),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_cameras_source_type",
        "cameras",
        "source_type IN ('file')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_cameras_source_type",
        "cameras",
        type_="check",
    )

    op.drop_column(
        "cameras",
        "source_uri",
    )

    op.drop_column(
        "cameras",
        "source_type",
    )
