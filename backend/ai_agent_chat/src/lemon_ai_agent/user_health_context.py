"""Privacy-safe app health context contracts for chatbot planning."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

ContextResolutionStatus = Literal[
    "sufficient",
    "needs_structured_lookup",
    "needs_more_info",
    "unknown_no_reviewed_source",
]

_SNAPSHOT_FIELDS = (
    "user_profile_summary",
    "today_analysis_snapshot",
    "health_analysis_snapshot",
    "active_supplement_snapshot",
    "recent_food_and_checklist_snapshot",
    "chat_derived_health_signals",
    "visible_analysis_context",
)

_FORBIDDEN_CONTEXT_KEYS = {
    "authorization",
    "conversation",
    "image_base64",
    "image_bytes",
    "messages",
    "prompt",
    "llm_output",
    "model_output",
    "provider_payload",
    "raw_chat_transcript",
    "raw_image",
    "raw_image_bytes",
    "raw_llm_output",
    "raw_model_output",
    "raw_ocr",
    "raw_ocr_text",
    "raw_prompt",
    "raw_provider_payload",
}

_FOOD_LOOKUP_TERMS = (
    "먹었",
    "먹은",
    "식사",
    "끼니",
    "아침",
    "점심",
    "저녁",
    "간식",
    "meal",
    "food",
)

_SPECIFIC_TIME_TERMS = (
    "오늘",
    "어제",
    "그제",
    "방금",
    "아까",
    "최근",
    "이번",
    "today",
    "yesterday",
    "recent",
)

_FOOD_RECORD_QUERY_TERMS = (
    "내가",
    "먹었",
    "먹은",
    "뭐 먹",
    "무엇을 먹",
    "기록",
    "조회",
    "확인해",
    "확인해줘",
)

_MEAL_PLANNING_TERMS = (
    "식단",
    "짜줘",
    "추천",
    "어떻게 먹",
    "뭘 먹",
    "뭐 먹으면",
    "먹으면 좋",
    "메뉴",
    "계획",
    "meal plan",
    "recommend",
)


@dataclass(frozen=True)
class UserHealthContextSnapshot:
    """Sanitized app-owned context available before each chatbot answer.

    The snapshot is a structured summary contract, not a dump of app data. Raw
    prompt text, OCR text, full chat transcripts, and raw LLM output are
    intentionally removed at construction time.
    """

    user_profile_summary: dict[str, Any] = field(default_factory=dict)
    today_analysis_snapshot: dict[str, Any] = field(default_factory=dict)
    health_analysis_snapshot: dict[str, Any] = field(default_factory=dict)
    active_supplement_snapshot: dict[str, Any] = field(default_factory=dict)
    recent_food_and_checklist_snapshot: dict[str, Any] = field(default_factory=dict)
    chat_derived_health_signals: dict[str, Any] = field(default_factory=dict)
    visible_analysis_context: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> UserHealthContextSnapshot:
        return cls()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> UserHealthContextSnapshot:
        sanitized = _sanitize_context_value(value)
        if not isinstance(sanitized, dict):
            return cls.empty()
        return cls(
            **{
                field_name: _as_dict(sanitized.get(field_name))
                for field_name in _SNAPSHOT_FIELDS
            }
        )

    def to_safe_context(self) -> dict[str, Any]:
        """Return non-empty, raw-free snapshot sections for planning prompts."""
        return {
            field_name: section
            for field_name in _SNAPSHOT_FIELDS
            if (section := getattr(self, field_name))
        }

    def has_context(self) -> bool:
        return bool(self.to_safe_context())

    def has_recent_food_records(self) -> bool:
        records = self.recent_food_and_checklist_snapshot.get("recent_food_records")
        return isinstance(records, list) and bool(records)


@dataclass(frozen=True)
class ContextResolution:
    status: ContextResolutionStatus
    safe_context: dict[str, Any] = field(default_factory=dict)
    required_records: tuple[str, ...] = ()
    lookup_filters: dict[str, str] = field(default_factory=dict)
    reason: str = ""


class ContextResolver:
    """Decides whether a question can use the snapshot or needs targeted DB reads."""

    def resolve(
        self,
        question: str,
        snapshot: UserHealthContextSnapshot,
    ) -> ContextResolution:
        normalized_question = question.casefold()
        if not snapshot.has_context():
            return ContextResolution(
                status="needs_more_info",
                reason="empty_user_health_context_snapshot",
            )

        if _asks_for_specific_food_record(normalized_question) and not snapshot.has_recent_food_records():
            return ContextResolution(
                status="needs_structured_lookup",
                safe_context=_profile_only_context(snapshot),
                required_records=("food_records",),
                lookup_filters={
                    "date_scope": "specific_or_recent",
                    "record_type": "food",
                },
                reason="specific_food_record_not_in_snapshot",
            )

        return ContextResolution(
            status="sufficient",
            safe_context=snapshot.to_safe_context(),
            reason="snapshot_sufficient",
        )


def _profile_only_context(snapshot: UserHealthContextSnapshot) -> dict[str, Any]:
    if not snapshot.user_profile_summary:
        return {}
    return {"user_profile_summary": snapshot.user_profile_summary}


def _asks_for_specific_food_record(normalized_question: str) -> bool:
    if any(term in normalized_question for term in _MEAL_PLANNING_TERMS):
        return False
    return (
        any(term in normalized_question for term in _FOOD_RECORD_QUERY_TERMS)
        and any(term in normalized_question for term in _FOOD_LOOKUP_TERMS)
        and any(term in normalized_question for term in _SPECIFIC_TIME_TERMS)
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _sanitize_context_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, nested_value in value.items():
            if not isinstance(key, str):
                continue
            if key.strip().casefold() in _FORBIDDEN_CONTEXT_KEYS:
                continue
            sanitized[key] = _sanitize_context_value(nested_value)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_context_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_context_value(item) for item in value)
    return value
