"""Readiness checks for reviewed medical source metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from lemon_ai_agent.knowledge import REVIEWED_MEDICAL_SOURCE_REGISTRY, ReviewedMedicalSource

from src.config import Settings


@dataclass(frozen=True)
class MedicalSourceStatus:
    source_id: str
    title: str
    status: str
    configured: bool
    ready: bool
    error_code: str | None
    env_key: str | None
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
    expires_at = date.fromisoformat(source.review_expires_at)
    status = source.status
    user_facing_allowed = source.user_facing_allowed

    error_code: str | None = None
    if status != "reviewed":
        error_code = "not_reviewed"
    elif today > expires_at:
        error_code = "source_stale"
    elif not configured:
        error_code = "missing_api_key"

    return MedicalSourceStatus(
        source_id=source.source_id,
        title=source.title,
        status=status,
        configured=configured,
        ready=error_code is None and user_facing_allowed,
        error_code=error_code,
        env_key=env_key,
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
