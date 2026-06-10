from __future__ import annotations

import pytest
from lemon_ai_agent.agents.chatbot import ChatbotAgent
from lemon_ai_agent.chat_session import ChatbotRequest
from lemon_ai_agent.llm import FakeLLMClient
from lemon_ai_agent.tracing import (
    AgentTraceSpan,
    InMemoryAgentTraceRecorder,
    NoopAgentTraceRecorder,
)


def test_agent_trace_span_accepts_only_sanitized_fields() -> None:
    span = AgentTraceSpan(
        request_id="req-1",
        span_name="chat_turn_plan",
        answerability="answerable_with_caution",
        retrieval_status="found",
        renderer_route="card_answer",
        claim_ids=("claim-1",),
        source_ids=("source-1",),
        boundary_code="",
        provider="deterministic",
        latency_ms=12.5,
        warning_codes=("fallback_used",),
        passed=True,
    )

    assert span.to_public_dict() == {
        "request_id": "req-1",
        "span_name": "chat_turn_plan",
        "answerability": "answerable_with_caution",
        "retrieval_status": "found",
        "renderer_route": "card_answer",
        "claim_ids": ["claim-1"],
        "source_ids": ["source-1"],
        "boundary_code": "",
        "provider": "deterministic",
        "latency_ms": 12.5,
        "warning_codes": ["fallback_used"],
        "passed": True,
        "raw_fields_stored": False,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("span_name", "raw_prompt"),
        ("warning_codes", ("raw llm response leaked",)),
        ("warning_codes", ("raw_llm_response",)),
        ("warning_codes", ("raw_user_question",)),
        ("warning_codes", ("raw_ocr_text",)),
        ("warning_codes", ("debug_trace",)),
        ("warning_codes", ("user_health_snapshot",)),
        ("source_ids", ("provider payload",)),
    ],
)
def test_agent_trace_span_rejects_forbidden_markers(field: str, value: object) -> None:
    kwargs = {
        "request_id": "req-1",
        "span_name": "chat_turn_plan",
        "answerability": "answerable",
        "retrieval_status": "found",
        "renderer_route": "card_answer",
        "claim_ids": (),
        "source_ids": (),
        "boundary_code": "",
        "provider": "deterministic",
        "latency_ms": None,
        "warning_codes": (),
        "passed": True,
    }
    kwargs[field] = value

    with pytest.raises(ValueError, match="forbidden trace marker"):
        AgentTraceSpan(**kwargs)


def test_trace_recorder_is_disabled_by_default_noop() -> None:
    recorder = NoopAgentTraceRecorder()
    recorder.record(
        AgentTraceSpan(
            request_id="req-1",
            span_name="render",
            answerability="unknown_no_reviewed_source",
            retrieval_status="no_match",
            renderer_route="unknown",
            claim_ids=(),
            source_ids=(),
            boundary_code="",
            provider="deterministic",
            latency_ms=None,
            warning_codes=("no_reviewed_answer_card",),
            passed=True,
        )
    )

    assert recorder.spans == ()


def test_chatbot_records_sanitized_spans_when_recorder_is_injected() -> None:
    recorder = InMemoryAgentTraceRecorder()

    response = ChatbotAgent(trace_recorder=recorder).answer(
        ChatbotRequest(
            request_id="trace-test-1",
            user_id="trace-user",
            message="리튬 복용 중인데 타우린 영양제를 같이 먹어도 돼?",
        )
    )

    assert response.answerability == "unknown_no_reviewed_source"
    assert [span.span_name for span in recorder.spans] == [
        "chat_turn_plan",
        "retrieval",
        "route_decision",
        "render",
    ]
    assert all(span.raw_fields_stored is False for span in recorder.spans)
    assert all(not span.claim_ids for span in recorder.spans)
    assert all(not span.source_ids for span in recorder.spans)


def test_chatbot_records_llm_and_safety_spans_without_raw_content() -> None:
    recorder = InMemoryAgentTraceRecorder()
    response = ChatbotAgent(
        llm_client=FakeLLMClient(
            response_text=(
                "요약\n"
                "- 제품 라벨의 마그네슘 함량과 혈압약 종류를 확인해야 합니다.\n"
                "오늘 할 일\n"
                "- 제품 라벨, 함량, 혈압약 종류, 신장 기능을 확인하세요.\n"
                "출처 기준\n"
                "- NIH ODS Magnesium Fact Sheet"
            )
        ),
        trace_recorder=recorder,
    ).answer(
        ChatbotRequest(
            request_id="trace-test-llm",
            user_id="trace-user",
            message="혈압약 먹는데 마그네슘 영양제를 같이 먹어도 돼?",
        )
    )

    assert response.provider == "fake"
    assert response.answerability == "answerable_with_caution"
    assert [span.span_name for span in recorder.spans] == [
        "chat_turn_plan",
        "retrieval",
        "llm_polish",
        "safety_guard",
        "route_decision",
        "render",
    ]
    assert all(span.raw_fields_stored is False for span in recorder.spans)
    assert all("혈압약" not in str(span.to_public_dict()) for span in recorder.spans)
    assert recorder.spans[-1].provider == "fake"
    assert recorder.spans[-1].source_ids


def test_chatbot_records_normalization_span_on_entity_resolution_path() -> None:
    recorder = InMemoryAgentTraceRecorder()

    response = ChatbotAgent(trace_recorder=recorder).answer(
        ChatbotRequest(
            request_id="trace-test-normalization",
            user_id="trace-user",
            message="혈압약 먹는데 칼슘 영양제를 같이 먹어도 돼?",
            context={
                "user_health_snapshot": {"raw_prompt": "must not leak"},
                "raw_ocr_text": "제품 라벨 원문",
                "raw_provider_payload": {"messages": ["hidden"]},
            },
        )
    )

    assert response.answerability == "needs_more_info"
    assert [span.span_name for span in recorder.spans] == [
        "chat_turn_plan",
        "retrieval",
        "normalization",
        "route_decision",
        "render",
    ]
    trace_text = str([span.to_public_dict() for span in recorder.spans]).casefold()
    assert "혈압약" not in trace_text
    assert "칼슘" not in trace_text
    assert "raw_prompt" not in trace_text
    assert "raw_ocr_text" not in trace_text
    assert "raw_provider_payload" not in trace_text
    assert "user_health_snapshot" not in trace_text
