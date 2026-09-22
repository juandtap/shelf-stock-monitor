"""add reason to stock alerts

Revision ID: 260de4049e1e
Revises: 72b4c076ae02
Create Date: 2026-09-21 19:00:22.739143
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "260de4049e1e"
down_revision: str | Sequence[str] | None = "72b4c076ae02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "stock_alerts",
        sa.Column(
            "reason",
            sa.String(length=50),
            nullable=False,
            server_default="legacy_low_stock",
        ),
    )

    op.create_check_constraint(
        "ck_stock_alerts_reason",
        "stock_alerts",
        "reason IN ("
        "'legacy_low_stock', "
        "'initial_low_stock', "
        "'entered_low_stock', "
        "'significant_stock_drop', "
        "'low_stock_reminder'"
        ")",
    )

    op.alter_column(
        "stock_alerts",
        "reason",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_stock_alerts_reason",
        "stock_alerts",
        type_="check",
    )
    op.drop_column("stock_alerts", "reason")
