"""use clock timestamp for observations

Revision ID: 7c1d8f2e4a90
Revises: 4f8c9d2a7b31
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7c1d8f2e4a90"
down_revision: str | Sequence[str] | None = "4f8c9d2a7b31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "stock_observations",
        "captured_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("clock_timestamp()"),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "stock_observations",
        "captured_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        existing_nullable=False,
    )
