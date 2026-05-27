"""Medical source registry readiness tests."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from lemon_ai_agent.knowledge import REVIEWED_MEDICAL_SOURCE_REGISTRY
from src.config import Settings
from src.services.medical_source_readiness import build_medical_source_readiness

NUTRITION_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _kdca_topic_ids() -> dict[str, str]:
    by_id = {source.source_id: source for source in REVIEWED_MEDICAL_SOURCE_REGISTRY}
    return {
        topic_id: f"{index:04d}"
        for index, (topic_id, _label) in enumerate(
            by_id["kdca-healthinfo"].topic_id_requirements,
            start=1,
        )
    }


def test_medical_source_readiness_requires_key_for_reviewed_keyed_sources() -> None:
    """Verify keyed reviewed sources are explicit before live retrieval work."""
    readiness = build_medical_source_readiness(
        Settings(_env_file=None),
        today=date(2026, 5, 24),
    )
    by_id = {source.source_id: source for source in readiness.sources}

    assert by_id["kdca-healthinfo"].ready is False
    assert by_id["kdca-healthinfo"].error_code == "missing_topic_ids"
    assert by_id["kdca-healthinfo"].env_key is None
    assert "hypertension" in by_id["kdca-healthinfo"].missing_topic_ids

    assert by_id["kdris-2025"].ready is True
    assert by_id["kdris-2025"].error_code is None


def test_medical_source_readiness_keeps_draft_sources_out_of_user_facing_use() -> None:
    """Verify research backlog sources do not become user-facing when a key exists."""
    settings = Settings(
        _env_file=None,
        kdca_healthinfo_topic_ids=_kdca_topic_ids(),
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
        Settings(_env_file=None, kdca_healthinfo_topic_ids=_kdca_topic_ids()),
        today=date(2027, 1, 1),
    )
    by_id = {source.source_id: source for source in readiness.sources}

    assert by_id["kdca-healthinfo"].ready is False
    assert by_id["kdca-healthinfo"].error_code == "source_stale"
    assert by_id["kdca-healthinfo"].review_expires_at == "2026-11-22"
    assert readiness.ready is False


def test_medical_source_readiness_loads_kdca_topic_ids_file(tmp_path) -> None:
    """Verify KDCA topic identifiers can be kept in an ignored local JSON file."""
    topic_ids = _kdca_topic_ids()
    topic_ids_file = tmp_path / "kdca_healthinfo_topics.local.json"
    topic_ids_file.write_text(
        '{"topics": {'
        + ", ".join(
            f'"{topic_id}": {{"title": "{topic_id}", "topic_id": "{value}"}}'
            for topic_id, value in topic_ids.items()
        )
        + "}}",
        encoding="utf-8",
    )

    readiness = build_medical_source_readiness(
        Settings(
            _env_file=None,
            kdca_healthinfo_topic_ids_file=topic_ids_file,
        ),
        today=date(2026, 5, 24),
    )
    by_id = {source.source_id: source for source in readiness.sources}

    assert by_id["kdca-healthinfo"].ready is True
    assert by_id["kdca-healthinfo"].missing_topic_ids == ()


def test_kdca_topic_ids_example_matches_required_topics() -> None:
    """Verify the tracked KDCA topic-id template stays aligned with readiness."""
    example_path = NUTRITION_BACKEND_ROOT / "config" / "kdca_healthinfo_topics.example.json"
    raw_value = json.loads(example_path.read_text(encoding="utf-8"))
    assert isinstance(raw_value, dict)
    topics = raw_value["topics"]
    assert isinstance(topics, dict)

    assert set(topics) == set(_kdca_topic_ids())
