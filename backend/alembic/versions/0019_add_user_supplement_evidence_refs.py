"""Add confirmed supplement evidence references.

Revision ID: 0019_add_user_supplement_evidence_refs
Revises: 0018_create_learning_dataset_model_registry_tables
Create Date: 2026-05-28 00:00:00.000000

Confirmed supplement rows need bounded trace ids back to sanitized preview
evidence. The column stores only evidence span identifiers and intentionally
does not store raw OCR text, provider payloads, image bytes, URLs, or secrets.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_add_user_supplement_evidence_refs"
down_revision: str | Sequence[str] | None = "0018_create_learning_dataset_model_registry_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add sanitized evidence reference ids to user supplements."""
    op.add_column(
        "user_supplements",
        sa.Column(
            "evidence_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_user_supplements_evidence_refs_array",
        "user_supplements",
        "jsonb_typeof(evidence_refs) = 'array'",
    )


def downgrade() -> None:
    """Remove user supplement evidence reference ids."""
    op.drop_constraint(
        "ck_user_supplements_evidence_refs_array",
        "user_supplements",
        type_="check",
    )
    op.drop_column("user_supplements", "evidence_refs")
