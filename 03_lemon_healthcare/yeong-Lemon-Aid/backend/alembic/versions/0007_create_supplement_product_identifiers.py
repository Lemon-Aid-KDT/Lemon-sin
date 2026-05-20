"""Create supplement product identifier table.

Revision ID: 0007_create_supplement_product_identifiers
Revises: 0006_create_regulated_ocr_intake
Create Date: 2026-05-16 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_create_supplement_product_identifiers"
down_revision: str | Sequence[str] | None = "0006_create_regulated_ocr_intake"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply this migration."""
    op.create_table(
        "supplement_product_identifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identifier_type", sa.String(length=40), nullable=False),
        sa.Column("identifier_value_hash", sa.String(length=80), nullable=False),
        sa.Column("identifier_value_encrypted", sa.String(length=512), nullable=True),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column(
            "source_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
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
            "identifier_type IN "
            "('ean8', 'upca', 'ean13', 'gtin14', 'qr_url', 'foodqr_id', 'prdlst_report_no')",
            name=op.f("ck_supplement_product_identifiers_identifier_type_allowed"),
        ),
        sa.CheckConstraint(
            "verification_status IN ('candidate', 'verified', 'rejected')",
            name=op.f("ck_supplement_product_identifiers_verification_status_allowed"),
        ),
        sa.CheckConstraint(
            "identifier_value_hash <> ''",
            name=op.f("ck_supplement_product_identifiers_identifier_value_hash_nonempty"),
        ),
        sa.CheckConstraint(
            "source_provider <> ''",
            name=op.f("ck_supplement_product_identifiers_identifier_source_provider_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["supplement_products.id"],
            name=op.f("fk_supplement_product_identifiers_product_id_supplement_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supplement_product_identifiers")),
        sa.UniqueConstraint(
            "identifier_type",
            "identifier_value_hash",
            "source_provider",
            name="uq_supplement_product_identifiers_type_hash_provider",
        ),
    )
    op.create_index(
        "ix_supplement_product_identifiers_product_status",
        "supplement_product_identifiers",
        ["product_id", "verification_status"],
        unique=False,
    )
    op.create_index(
        "ix_supplement_product_identifiers_type_hash",
        "supplement_product_identifiers",
        ["identifier_type", "identifier_value_hash"],
        unique=False,
    )


def downgrade() -> None:
    """Rollback this migration."""
    op.drop_index(
        "ix_supplement_product_identifiers_type_hash",
        table_name="supplement_product_identifiers",
    )
    op.drop_index(
        "ix_supplement_product_identifiers_product_status",
        table_name="supplement_product_identifiers",
    )
    op.drop_table("supplement_product_identifiers")
