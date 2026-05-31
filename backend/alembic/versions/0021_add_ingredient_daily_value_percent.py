"""Add daily-value percent (%DV / 영양성분기준치) to ingredient tables.

Revision ID: 0021_add_ingredient_daily_value_percent
Revises: 0020_harden_supplement_user_tables_rls
Create Date: 2026-05-30 00:00:00.000000

Supplement labels frequently express each ingredient's amount alongside a
percentage of the daily reference intake (영양성분기준치 / %DV). The schema
previously captured only the absolute ``amount`` + ``unit`` and had no typed
column for the percentage, so that signal was lost. This migration adds an
optional, non-negative ``daily_value_percent`` Numeric column to both the
reference catalog ingredient table and the user-confirmed ingredient table.
The column is additive and nullable; existing rows are unaffected and no data
is modified.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_add_ingredient_daily_value_percent"
down_revision: str | Sequence[str] | None = "0020_harden_supplement_user_tables_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable, non-negative daily_value_percent to ingredient tables."""
    op.add_column(
        "supplement_product_ingredients",
        sa.Column("daily_value_percent", sa.Numeric(7, 3), nullable=True),
    )
    op.create_check_constraint(
        "ck_supplement_product_ingredients_daily_value_percent_nonnegative",
        "supplement_product_ingredients",
        "daily_value_percent IS NULL OR daily_value_percent >= 0",
    )

    op.add_column(
        "user_supplement_ingredients",
        sa.Column("daily_value_percent", sa.Numeric(7, 3), nullable=True),
    )
    op.create_check_constraint(
        "ck_user_supplement_ingredients_daily_value_percent_nonnegative",
        "user_supplement_ingredients",
        "daily_value_percent IS NULL OR daily_value_percent >= 0",
    )


def downgrade() -> None:
    """Remove the daily_value_percent columns from ingredient tables."""
    op.drop_constraint(
        "ck_user_supplement_ingredients_daily_value_percent_nonnegative",
        "user_supplement_ingredients",
        type_="check",
    )
    op.drop_column("user_supplement_ingredients", "daily_value_percent")

    op.drop_constraint(
        "ck_supplement_product_ingredients_daily_value_percent_nonnegative",
        "supplement_product_ingredients",
        type_="check",
    )
    op.drop_column("supplement_product_ingredients", "daily_value_percent")
