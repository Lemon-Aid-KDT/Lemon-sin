from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Protocol

ALLOWED_TRACE_SPANS = {
    "chat_turn_plan",
    "retrieval",
    "normalization",
    "route_decision",
    "render",
    "llm_polish",
    "safety_guard",
}

FORBIDDEN_TRACE_MARKERS = (
    "raw user question",
    "raw_user_question",
    "raw question",
    "raw prompt",
    "raw_prompt",
    "raw ocr",
    "raw_ocr",
    "raw_ocr_text",
    "raw llm response",
    "raw_llm_response",
    "raw_model_output",
    "provider payload",
    "provider_payload",
    "debug trace",
    "debug_trace",
    "user health snapshot",
    "user_health_snapshot",
    "user_health_context_snapshot",
    "full_prompt",
    "messages",
    "raw_provider_payload",
    "raw_transcript",
)


@dataclass(frozen=True)
class AgentTraceSpan:
    request_id: str
    span_name: str
    answerability: str = ""
    retrieval_status: str = ""
    renderer_route: str = ""
    claim_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    boundary_code: str = ""
    provider: str = ""
    latency_ms: float | None = None
    warning_codes: tuple[str, ...] = ()
    passed: bool = True
    raw_fields_stored: bool = False

    def __post_init__(self) -> None:
        if self.span_name not in ALLOWED_TRACE_SPANS:
            raise ValueError(f"forbidden trace marker: {self.span_name}")
        if self.raw_fields_stored:
            raise ValueError("raw_fields_stored must remain false")
        for value in _iter_string_values(self):
            normalized = value.casefold()
            if any(marker in normalized for marker in FORBIDDEN_TRACE_MARKERS):
                raise ValueError(f"forbidden trace marker: {value}")

    def to_public_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "span_name": self.span_name,
            "answerability": self.answerability,
            "retrieval_status": self.retrieval_status,
            "renderer_route": self.renderer_route,
            "claim_ids": list(self.claim_ids),
            "source_ids": list(self.source_ids),
            "boundary_code": self.boundary_code,
            "provider": self.provider,
            "latency_ms": self.latency_ms,
            "warning_codes": list(self.warning_codes),
            "passed": self.passed,
            "raw_fields_stored": False,
        }


class AgentTraceRecorder(Protocol):
    def record(self, span: AgentTraceSpan) -> None:
        ...


@dataclass
class NoopAgentTraceRecorder:
    @property
    def spans(self) -> tuple[AgentTraceSpan, ...]:
        return ()

    def record(self, _span: AgentTraceSpan) -> None:
        return None


@dataclass
class InMemoryAgentTraceRecorder:
    _spans: list[AgentTraceSpan] = field(default_factory=list)

    @property
    def spans(self) -> tuple[AgentTraceSpan, ...]:
        return tuple(self._spans)

    def record(self, span: AgentTraceSpan) -> None:
        self._spans.append(span)


@dataclass
class StructuredLogAgentTraceRecorder:
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("lemon_ai_agent.trace")
    )

    def record(self, span: AgentTraceSpan) -> None:
        self.logger.info(
            "agent_trace_span %s",
            json.dumps(span.to_public_dict(), ensure_ascii=False, sort_keys=True),
        )


def _iter_string_values(span: AgentTraceSpan) -> tuple[str, ...]:
    values: list[str] = [
        span.request_id,
        span.span_name,
        span.answerability,
        span.retrieval_status,
        span.renderer_route,
        span.boundary_code,
        span.provider,
    ]
    values.extend(span.claim_ids)
    values.extend(span.source_ids)
    values.extend(span.warning_codes)
    return tuple(values)
