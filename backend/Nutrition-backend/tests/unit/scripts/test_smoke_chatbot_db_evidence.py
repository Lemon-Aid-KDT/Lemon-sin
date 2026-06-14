"""Tests for the DB-backed chatbot evidence smoke script."""

from __future__ import annotations

from scripts import smoke_chatbot_db_evidence as smoke


def test_parse_args_defaults_to_production_db_only_mode() -> None:
    """Verify the smoke proves DB-only retrieval by default."""
    args = smoke._parse_args(
        [
            "--database-url",
            "postgresql://postgres:secret@db.example.test:5432/postgres?sslmode=require",
        ]
    )

    assert args.preset == "hypertension-sodium"
    assert args.environment == "production"
    assert args.database_url.startswith("postgresql://")


def test_normalize_database_url_accepts_supabase_postgres_uri() -> None:
    """Verify Dashboard-style URLs become async SQLAlchemy URLs."""
    normalized = smoke._normalize_database_url(
        "postgresql://postgres:secret@db.example.test:5432/postgres?sslmode=require"
    )

    assert normalized == (
        "postgresql+asyncpg://postgres:secret@db.example.test:5432/postgres?ssl=require"
    )


def test_summary_payload_omits_database_url_and_keeps_source_metadata() -> None:
    """Verify output is useful for QA but does not include secrets."""
    summary = smoke._summary_payload(
        environment="production",
        preset="hypertension-sodium",
        record_count=14,
        answerability="answerable",
        source_count=1,
        sources=[
            {
                "source_id": "kdris-2025",
                "source_family": "nutrition_reference",
                "version_label": "KDRIs 2025",
                "expires_at": "2027-05-19",
                "source_url": "https://example.test/kdris",
            }
        ],
        safety_warnings=[],
    )

    assert summary == {
        "status": "ok",
        "environment": "production",
        "preset": "hypertension-sodium",
        "db_evidence_record_count": 14,
        "answerability": "answerable",
        "source_count": 1,
        "sources": [
            {
                "source_id": "kdris-2025",
                "source_family": "nutrition_reference",
                "version_label": "KDRIs 2025",
                "expires_at": "2027-05-19",
            }
        ],
        "safety_warnings": [],
    }
