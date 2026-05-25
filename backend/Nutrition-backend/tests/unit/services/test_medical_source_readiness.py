"""Medical source registry readiness tests."""

from __future__ import annotations

from datetime import date

from src.config import Settings
from src.services.medical_source_readiness import build_medical_source_readiness


def test_medical_source_readiness_requires_key_for_reviewed_keyed_sources() -> None:
    """Verify keyed reviewed sources are explicit before live retrieval work."""
    readiness = build_medical_source_readiness(
        Settings(_env_file=None),
        today=date(2026, 5, 24),
    )
    by_id = {source.source_id: source for source in readiness.sources}

    assert by_id["kdca-healthinfo"].ready is False
    assert by_id["kdca-healthinfo"].error_code == "missing_api_key"
    assert by_id["kdca-healthinfo"].env_key == "KDCA_HEALTHINFO_API_KEY"

    assert by_id["kdris-2025"].ready is True
    assert by_id["kdris-2025"].error_code is None


def test_medical_source_readiness_keeps_draft_sources_out_of_user_facing_use() -> None:
    """Verify research backlog sources do not become user-facing when a key exists."""
    settings = Settings(
        _env_file=None,
        kdca_healthinfo_api_key="kdca-key",
        mfds_data_api_key="mfds-key",
        semantic_scholar_api_key="semantic-key",
    )

    readiness = build_medical_source_readiness(settings, today=date(2026, 5, 24))
    by_id = {source.source_id: source for source in readiness.sources}

    assert by_id["kdca-healthinfo"].ready is True
    assert by_id["kdca-healthinfo"].configured is True
    assert by_id["kdca-healthinfo"].topics[:3] == (
        "hypertension",
        "diabetes",
        "kidney_disease",
    )
    assert by_id["mfds-drug-safety"].ready is True
    assert by_id["mfds-drug-safety"].configured is True

    semantic_scholar = by_id["semantic-scholar"]
    assert semantic_scholar.configured is True
    assert semantic_scholar.ready is False
    assert semantic_scholar.user_facing_allowed is False
    assert semantic_scholar.error_code == "not_reviewed"
    assert readiness.ready is True


def test_medical_source_readiness_marks_expired_review_as_stale() -> None:
    """Verify stale-source behavior is deterministic before RAG/live retrieval."""
    readiness = build_medical_source_readiness(
        Settings(_env_file=None, kdca_healthinfo_api_key="kdca-key"),
        today=date(2027, 1, 1),
    )
    by_id = {source.source_id: source for source in readiness.sources}

    assert by_id["kdca-healthinfo"].ready is False
    assert by_id["kdca-healthinfo"].error_code == "source_stale"
    assert by_id["kdca-healthinfo"].review_expires_at == "2026-11-22"
    assert readiness.ready is False
