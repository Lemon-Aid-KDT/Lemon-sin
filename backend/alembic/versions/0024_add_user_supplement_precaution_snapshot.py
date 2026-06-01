"""Add confirmed supplement precaution snapshot.

Revision ID: 0024_add_user_supplement_precaution_snapshot
Revises: 0023c_force_row_level_security
Create Date: 2026-06-01 00:00:00.000000

The snapshot stores only user-confirmed precaution sentences from the reviewed
label result. It intentionally does not store raw OCR text, provider payloads,
image bytes, URLs, or secrets.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024_add_user_supplement_precaution_snapshot"
down_revision: str | Sequence[str] | None = "0023c_force_row_level_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add sanitized user-confirmed precaution sentences to supplements."""
    op.add_column(
        "user_supplements",
        sa.Column(
            "precaution_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_user_supplements_precaution_snapshot_array",
        "user_supplements",
        "jsonb_typeof(precaution_snapshot) = 'array'",
    )


def downgrade() -> None:
    """Remove user-confirmed precaution sentence snapshots."""
    op.drop_constraint(
        "ck_user_supplements_precaution_snapshot_array",
        "user_supplements",
        type_="check",
    )
    op.drop_column("user_supplements", "precaution_snapshot")
