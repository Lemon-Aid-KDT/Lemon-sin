"""Readiness checks for reviewed medical source metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from lemon_ai_agent.knowledge import REVIEWED_MEDICAL_SOURCE_REGISTRY, ReviewedMedicalSource

from src.config import BACKEND_ROOT, PROJECT_ROOT, Settings


@dataclass(frozen=True)
class MedicalSourceStatus:
    source_id: str
    title: str
    status: str
    configured: bool
    ready: bool
    error_code: str | None
    env_key: str | None
    missing_topic_ids: tuple[str, ...]
    source_families: tuple[str, ...]
    topics: tuple[str, ...]
    user_facing_allowed: bool
    last_reviewed_at: str
    review_expires_at: str


@dataclass(frozen=True)
class MedicalSourceReadiness:
    ready: bool
    sources: tuple[MedicalSourceStatus, ...]


def build_medical_source_readiness(
    settings: Settings,
    *,
    today: date | None = None,
) -> MedicalSourceReadiness:
    """Return sanitized readiness for source-governance checks.

    The check does not call external APIs and never exposes secret values. It only
    verifies that reviewed source metadata is current and that keyed sources have
    a configured key before future live retrieval or RAG work can rely on them.
    """
    current_date = today or datetime.now(UTC).date()
    statuses = tuple(
        _source_status(settings, source, current_date)
        for source in REVIEWED_MEDICAL_SOURCE_REGISTRY
    )
    return MedicalSourceReadiness(
        ready=all(source.ready for source in statuses if source.user_facing_allowed),
        sources=statuses,
    )


def _source_status(
    settings: Settings,
    source: ReviewedMedicalSource,
    today: date,
) -> MedicalSourceStatus:
    env_key = source.env_key
    configured = True if env_key is None else _has_secret_setting(settings, env_key)
    missing_topic_ids = _missing_required_topic_ids(settings, source)
    configured = configured and not missing_topic_ids
    expires_at = date.fromisoformat(source.review_expires_at)
    status = source.status
    user_facing_allowed = source.user_facing_allowed

    error_code: str | None = None
    if status != "reviewed":
        error_code = "not_reviewed"
    elif today > expires_at:
        error_code = "source_stale"
    elif not configured:
        error_code = "missing_topic_ids" if missing_topic_ids else "missing_api_key"

    return MedicalSourceStatus(
        source_id=source.source_id,
        title=source.title,
        status=status,
        configured=configured,
        ready=error_code is None and user_facing_allowed,
        error_code=error_code,
        env_key=env_key,
        missing_topic_ids=missing_topic_ids,
        source_families=source.source_families,
        topics=source.topics,
        user_facing_allowed=user_facing_allowed,
        last_reviewed_at=source.last_reviewed_at,
        review_expires_at=source.review_expires_at,
    )


def _has_secret_setting(settings: Settings, env_key: str) -> bool:
    attr_name = env_key.lower()
    value = getattr(settings, attr_name, None)
    if value is None:
        return False
    if hasattr(value, "get_secret_value"):
        return bool(value.get_secret_value())
    return bool(value)


def _missing_required_topic_ids(
    settings: Settings,
    source: ReviewedMedicalSource,
) -> tuple[str, ...]:
    if not source.topic_id_requirements:
        return ()

    configured_topic_ids = _configured_kdca_healthinfo_topic_ids(settings)
    return tuple(
        topic_id
        for topic_id, _label in source.topic_id_requirements
        if not configured_topic_ids.get(topic_id)
    )


def _configured_kdca_healthinfo_topic_ids(settings: Settings) -> dict[str, str]:
    topic_ids = _load_topic_ids_from_file(settings.kdca_healthinfo_topic_ids_file)
    topic_ids.update(
        {
            key: value
            for key, value in settings.kdca_healthinfo_topic_ids.items()
            if isinstance(value, str) and value.strip()
        }
    )
    return topic_ids


def _load_topic_ids_from_file(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    resolved_path = _resolve_topic_ids_path(path)
    if resolved_path is None:
        return {}
    try:
        raw_value = json.loads(resolved_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return _parse_topic_ids(raw_value)


def _resolve_topic_ids_path(path: Path) -> Path | None:
    candidates = [path]
    if not path.is_absolute():
        candidates.extend((PROJECT_ROOT / path, BACKEND_ROOT / path))
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _parse_topic_ids(raw_value: Any) -> dict[str, str]:
    if not isinstance(raw_value, dict):
        return {}

    raw_topics = raw_value.get("topics", raw_value)
    if not isinstance(raw_topics, dict):
        return {}

    topic_ids: dict[str, str] = {}
    for key, value in raw_topics.items():
        if not isinstance(key, str):
            continue
        parsed_value = _parse_topic_id_value(value)
        if parsed_value:
            topic_ids[key] = parsed_value
    return topic_ids


def _parse_topic_id_value(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        raw_topic_id = value.get("topic_id")
        if isinstance(raw_topic_id, str):
            return raw_topic_id.strip() or None
    return None
