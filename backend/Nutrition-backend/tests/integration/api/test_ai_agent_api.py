"""AI Agent daily coaching API tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from lemon_ai_agent.llm import LLMRequest, LLMResponse
from src.api.v1 import ai_agent
from src.config import Settings, get_settings
from src.db.dependencies import get_async_session
from src.main import create_app
from src.services.privacy import ConsentRequiredError


class _UnavailableOllamaClient:
    """Network-free Ollama stand-in for route fallback tests."""

    provider = "ollama"
    model = "offline-test-ollama"

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        """Accept the production client constructor shape without opening a socket."""

    def generate(self, _request: LLMRequest) -> LLMResponse:
        """Force the app adapter through its deterministic fallback path."""
        raise RuntimeError("offline test llm")


@pytest.fixture(autouse=True)
def _disable_live_ollama_for_route_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep route tests isolated from whichever Ollama server is running locally."""
    monkeypatch.setattr(ai_agent, "OllamaClient", _UnavailableOllamaClient)


async def _fake_session_dependency() -> AsyncIterator[object]:
    """Yield a fake session for route tests.

    Yields:
        Fake session object.
    """
    yield object()


async def _allow_consent(*_args: object, **_kwargs: object) -> None:
    """No-op consent service for route tests.

    Args:
        *_args: Positional call arguments.
        **_kwargs: Keyword call arguments.

    Returns:
        None.
    """


async def _deny_consent(*_args: object, **_kwargs: object) -> None:
    """Raise a missing-consent service error.

    Args:
        *_args: Positional call arguments.
        **_kwargs: Keyword call arguments.

    Returns:
        None.

    Raises:
        ConsentRequiredError: Always raised for this test.
    """
    raise ConsentRequiredError("Consent is required.")


async def _record_noop_audit(*_args: object, **_kwargs: object) -> None:
    """No-op audit service for route tests.

    Args:
        *_args: Positional call arguments.
        **_kwargs: Keyword call arguments.

    Returns:
        None.
    """


async def _memory_context(*_args: object, **_kwargs: object) -> dict[str, object]:
    """Return route-level memory context for injection tests.

    Args:
        *_args: Positional call arguments.
        **_kwargs: Keyword call arguments.

    Returns:
        Sanitized Agent memory context.
    """
    return {
        "schema_version": "agent-memory-summary-v1",
        "summaries": [
            {
                "memory_type": "daily_coaching",
                "summary_json": {
                    "repeated_nutrient_patterns": {
                        "sodium": 3,
                        "protein": 2,
                    }
                },
                "source_counters": {"daily_coaching": 3},
                "algorithm_version": "agent-memory-summary-v1.0.0",
            }
        ],
    }


def _client(settings: Settings | None = None) -> TestClient:
    """Return a TestClient with the DB session dependency replaced.

    Args:
        settings: Optional settings override for route dependency injection.

    Returns:
        FastAPI test client.
    """
    app = create_app()
    app.dependency_overrides[get_async_session] = _fake_session_dependency
    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _payload(*, user_confirmed: bool = True, unsafe_trend: bool = False) -> dict[str, object]:
    """Return a daily coaching request payload.

    Args:
        user_confirmed: Whether the OCR source has user confirmation.
        unsafe_trend: Whether to include unsafe trend text for sanitization.

    Returns:
        JSON request payload.
    """
    trend_summary = (
        "diabetes. purchase this supplement."
        if unsafe_trend
        else "Meal score has dropped for 7 days."
    )
    return {
        "request_id": "daily-coaching-route-test",
        "user_id": "client-supplied-user",
        "context": {
            "profile": {
                "age": 52,
                "gender": "male",
                "goals": ["meal_management"],
                "chronic_conditions": ["hypertension"],
                "medications": ["blood_pressure_medication"],
            }
        },
        "payload": {
            "date": "2026-05-18",
            "sources": [
                {
                    "source_type": "food_ocr",
                    "image_id": "meal-image-1",
                    "raw_ocr_text": "instant noodles sodium 2600mg",
                    "user_confirmed": user_confirmed,
                }
            ],
            "foods": [
                {
                    "name": "instant noodles",
                    "meal_type": "lunch",
                    "serving_label": "1 bowl",
                    "nutrients": [
                        {"name": "sodium", "amount": 2600, "unit": "mg"},
                        {"name": "protein", "amount": 25, "unit": "g"},
                    ],
                }
            ],
            "supplements": [],
            "health_trends": [
                {
                    "metric": "meal_score",
                    "direction": "down",
                    "severity": "watch",
                    "summary": trend_summary,
                }
            ],
        },
    }


def _chat_payload(
    *,
    message: str = "오늘 기록을 보고 먼저 확인할 점을 알려줘.",
    preview_context: bool = False,
) -> dict[str, object]:
    """Return a chatbot request payload.

    Args:
        preview_context: Whether the request contains preview-only client context.

    Returns:
        JSON request payload.
    """
    return {
        "request_id": "chat-route-test",
        "user_id": "client-supplied-user",
        "message": message,
        "conversation": [
            {
                "role": "user",
                "content": "점심과 영양제를 입력했어.",
                "created_at": "2026-05-21T09:00:00+09:00",
            }
        ],
        "context": {
            "daily_coaching_summary": "나트륨 섭취가 반복적으로 높게 기록되었습니다.",
            "preview_only": preview_context,
            "internal_trace": "supplement totals: vitamin d=25mcg",
        },
    }


def test_daily_coaching_returns_completed_result_for_confirmed_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the route runs deterministic coaching for confirmed input."""
    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)

    response = _client().post("/api/v1/ai-agent/daily-coaching", json=_payload())

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["user_id"] == "local-dev-user"
    assert body["status"] == "completed"
    assert body["approval_status"] == "confirmed"
    assert body["provider"] == "deterministic"
    assert body["debug_trace"] == []
    assert {
        "message",
        "findings",
        "recommendations",
        "safety_warnings",
        "provider",
        "used_tools",
    }.issubset(body)
    assert "오늘의 요약" in body["message"]
    assert "권장 행동" in body["message"]
    assert "참고 및 주의" in body["message"]
    assert "supplement totals" not in body["message"]
    assert "nutrition findings" not in body["message"]
    assert "Trace" not in body["message"]
    levels = {finding["nutrient"]: finding["level"] for finding in body["findings"]}
    assert levels["sodium"] == "risky"
    assert levels["protein"] == "low"
    assert "raw_ocr_text" not in str(body)


def test_daily_coaching_injects_memory_and_records_confirmed_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify route-level memory injection and confirmed persistence handoff."""
    persisted: dict[str, object] = {}

    async def _capture_memory_update(*args: object, **_kwargs: object) -> None:
        persisted["memory_request"] = args[3]
        persisted["memory_output"] = args[4]

    async def _capture_agent_run(*args: object, **_kwargs: object) -> None:
        persisted["run_output"] = args[3]

    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)
    monkeypatch.setattr(ai_agent, "load_agent_memory_context", _memory_context)
    monkeypatch.setattr(ai_agent, "upsert_daily_coaching_memory", _capture_memory_update)
    monkeypatch.setattr(ai_agent, "record_agent_run", _capture_agent_run)

    response = _client().post("/api/v1/ai-agent/daily-coaching", json=_payload())

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "agent_memory" in body["used_tools"]
    assert any(
        "appeared 3 times" in recommendation["rationale"]
        for recommendation in body["recommendations"]
    )
    memory_request = persisted["memory_request"]
    memory_output = persisted["memory_output"]
    run_output = persisted["run_output"]
    assert memory_request.context["agent_memory"]["summaries"][0]["memory_type"] == "daily_coaching"
    assert memory_output.status == "completed"
    assert memory_output.approval_status == "confirmed"
    assert run_output.status == "completed"


def test_daily_coaching_uses_sglang_provider_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify backend route selects the SGLang client under SGLang settings."""
    captured: dict[str, object] = {}

    class _FakeSGLangClient:
        """Network-free SGLang stand-in for route dependency tests."""

        def __init__(
            self,
            *,
            model: str,
            endpoint: str,
            api_key: str | None,
            timeout: float,
        ) -> None:
            self.model = model
            captured["sglang_client"] = {
                "model": model,
                "endpoint": endpoint,
                "api_key": api_key,
                "timeout": timeout,
            }

        def generate(self, request: LLMRequest) -> LLMResponse:
            captured["llm_request"] = request
            return LLMResponse(
                text=(
                    "오늘의 요약: 현재 입력 기준으로 한 가지 영양 항목은 "
                    "주의가 필요할 수 있습니다. 권장 행동: 확인된 권장 사항을 "
                    "먼저 살펴보세요. 참고 및 주의: 의학적 판단이 필요한 경우 "
                    "전문가와 상담해 주세요."
                ),
                provider="sglang",
                model=self.model,
            )

    async def _capture_agent_run(*args: object, **kwargs: object) -> None:
        captured["run_output"] = args[3]
        captured["run_model"] = kwargs.get("model")

    settings = Settings(
        _env_file=None,
        llm_provider="sglang",
        sglang_base_url="http://127.0.0.1:30000/v1",
        sglang_model="Qwen/Qwen2.5-0.5B-Instruct",
    )
    monkeypatch.setattr(ai_agent, "SGLangClient", _FakeSGLangClient)
    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)
    monkeypatch.setattr(ai_agent, "record_agent_run", _capture_agent_run)

    response = _client(settings=settings).post(
        "/api/v1/ai-agent/daily-coaching",
        json=_payload(),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["provider"] == "sglang"
    assert "오늘의 요약" in body["message"]
    assert "supplement totals" not in body["message"]
    assert "nutrition findings" not in body["message"]
    assert captured["sglang_client"] == {
        "model": "Qwen/Qwen2.5-0.5B-Instruct",
        "endpoint": "http://127.0.0.1:30000/v1",
        "api_key": None,
        "timeout": settings.ollama_timeout_sec,
    }
    assert captured["llm_request"].messages[0].role == "system"
    assert "Answer only in Korean" in captured["llm_request"].messages[0].content
    assert "Do not mention or quote internal calculation logs" in captured[
        "llm_request"
    ].messages[0].content
    assert "Trace summary" not in captured["llm_request"].messages[1].content
    assert captured["run_output"].provider == "sglang"
    assert captured["run_model"] == "Qwen/Qwen2.5-0.5B-Instruct"


def test_daily_coaching_returns_preview_for_unconfirmed_ocr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify unconfirmed OCR source records stop at preview state."""
    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)

    response = _client().post(
        "/api/v1/ai-agent/daily-coaching",
        json=_payload(user_confirmed=False),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "preview"
    assert body["approval_status"] == "requires_confirmation"
    assert body["requires_user_approval"] is True
    assert body["findings"] == []
    assert body["recommendations"] == []
    assert body["actions"] == []


def test_daily_coaching_preview_does_not_persist_memory_or_run_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify unconfirmed preview responses skip memory and run persistence."""
    persisted: dict[str, int] = {"memory": 0, "run": 0}

    async def _capture_memory_update(*_args: object, **_kwargs: object) -> None:
        persisted["memory"] += 1

    async def _capture_agent_run(*_args: object, **_kwargs: object) -> None:
        persisted["run"] += 1

    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)
    monkeypatch.setattr(ai_agent, "upsert_daily_coaching_memory", _capture_memory_update)
    monkeypatch.setattr(ai_agent, "record_agent_run", _capture_agent_run)

    response = _client().post(
        "/api/v1/ai-agent/daily-coaching",
        json=_payload(user_confirmed=False),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "preview"
    assert persisted == {"memory": 0, "run": 0}


def test_daily_coaching_requires_sensitive_health_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the route fails closed without sensitive-health consent."""
    monkeypatch.setattr(ai_agent, "require_user_consent", _deny_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)

    response = _client().post("/api/v1/ai-agent/daily-coaching", json=_payload())

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["code"] == "consent_required"


def test_daily_coaching_sanitizes_unsafe_trend_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify unsafe trace text is not returned from the API response."""
    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)

    response = _client().post(
        "/api/v1/ai-agent/daily-coaching",
        json=_payload(unsafe_trend=True),
    )

    assert response.status_code == status.HTTP_200_OK
    body_text = str(response.json())
    assert "Trace text blocked" in body_text
    assert "diabetes" not in body_text
    assert "purchase this supplement" not in body_text


def test_daily_coaching_activity_context_omits_raw_sensitive_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify activity context does not expose raw device-sensitive extras."""
    payload = _payload()
    payload["payload"]["health_trends"] = [
        {
            "metric": "activity_context",
            "direction": "up",
            "severity": "info",
            "summary": "Confirmed activity entry: 7200 steps and 34 active minutes.",
            "steps": 7200,
            "active_minutes": 34,
            "activity_energy_kcal": 220,
            "workout_type": "walk",
            "source": "manual",
            "user_confirmed": True,
            "route_location": "home to clinic",
            "blood_pressure": "120/80",
            "sleep": "7h",
        }
    ]
    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)

    response = _client().post("/api/v1/ai-agent/daily-coaching", json=payload)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    body_text = str(body)
    assert body["debug_trace"] == []
    assert "route_location" not in body_text
    assert "home to clinic" not in body_text
    assert "blood_pressure" not in body_text
    assert "120/80" not in body_text
    assert "sleep" not in body_text


def test_chat_route_uses_sglang_provider_and_agent_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify chatbot route reuses the local LLM and memory context safely."""
    captured: dict[str, object] = {}

    class _FakeSGLangClient:
        """Network-free SGLang stand-in for chatbot route tests."""

        def __init__(
            self,
            *,
            model: str,
            endpoint: str,
            api_key: str | None,
            timeout: float,
        ) -> None:
            self.model = model
            captured["sglang_client"] = {
                "model": model,
                "endpoint": endpoint,
                "api_key": api_key,
                "timeout": timeout,
            }

        def generate(self, request: LLMRequest) -> LLMResponse:
            captured["llm_request"] = request
            return LLMResponse(
                text=(
                    "요약\n"
                    "- 현재 입력 기준으로 확인된 기록을 함께 살펴봤습니다.\n"
                    "주의 조건\n"
                    "- 의학적 판단이 필요한 경우 전문가와 상담해 주세요.\n"
                    "오늘 할 일\n"
                    "- 오늘 확정한 식사와 영양제 기록부터 점검해 주세요.\n"
                    "관리 포인트\n"
                    "- 반복 패턴을 확인하세요.\n"
                    "출처 기준\n"
                    "- 질병관리청 건강정보, KDRIs 영양 기준"
                ),
                provider="sglang",
                model=self.model,
            )

    settings = Settings(
        _env_file=None,
        llm_provider="sglang",
        sglang_base_url="http://127.0.0.1:30000/v1",
        sglang_model="Qwen/Qwen2.5-0.5B-Instruct",
    )
    monkeypatch.setattr(ai_agent, "SGLangClient", _FakeSGLangClient)
    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)
    monkeypatch.setattr(ai_agent, "load_agent_memory_context", _memory_context)

    response = _client(settings=settings).post(
        "/api/v1/ai-agent/chat",
        json=_chat_payload(),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["request_id"] == "chat-route-test"
    assert body["provider"] == "sglang"
    assert "요약" in body["message"]
    assert "주의 조건" in body["message"]
    assert "오늘 할 일" in body["message"]
    assert "관리 포인트" in body["message"]
    assert "출처 기준" in body["message"]
    assert "agent_memory" in body["used_tools"]
    assert "knowledge_policy" in body["used_tools"]
    assert body["source_families"] == ["general_medical"]
    assert "supplement totals" not in body["message"]
    assert "internal_trace" not in body["message"]
    assert captured["sglang_client"]["model"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert "Answer only in Korean" in captured["llm_request"].messages[0].content
    assert "Question category:" in captured["llm_request"].messages[1].content
    assert "Allowed source families:" in captured["llm_request"].messages[1].content
    assert "Response contract:" in captured["llm_request"].messages[1].content
    assert "Internal context for grounding only" in captured[
        "llm_request"
    ].messages[1].content
    assert "internal_trace" not in captured["llm_request"].messages[1].content
    assert "supplement totals" not in captured["llm_request"].messages[1].content
    assert "summary_json" not in captured["llm_request"].messages[1].content


def test_chat_route_preview_context_does_not_persist_daily_coaching_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify chat preview context is not recorded as a completed coaching run."""
    persisted: dict[str, int] = {"memory": 0, "run": 0}

    async def _capture_memory_update(*_args: object, **_kwargs: object) -> None:
        persisted["memory"] += 1

    async def _capture_agent_run(*_args: object, **_kwargs: object) -> None:
        persisted["run"] += 1

    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)
    monkeypatch.setattr(ai_agent, "load_agent_memory_context", _memory_context)
    monkeypatch.setattr(ai_agent, "upsert_daily_coaching_memory", _capture_memory_update)
    monkeypatch.setattr(ai_agent, "record_agent_run", _capture_agent_run)
    monkeypatch.setattr(ai_agent, "_build_llm_client", lambda _settings: None)

    response = _client().post(
        "/api/v1/ai-agent/chat",
        json=_chat_payload(preview_context=True),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["provider"] == "deterministic"
    assert body["requires_user_approval"] is False
    assert persisted == {"memory": 0, "run": 0}


def test_chat_route_magnesium_blood_pressure_med_uses_caution_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify lower-risk medication/supplement co-use can use the bounded LLM."""
    captured: dict[str, object] = {"generate_called": False}

    class _FakeSGLangClient:
        """SGLang stand-in for medication/supplement caution questions."""

        def __init__(
            self,
            *,
            model: str,
            endpoint: str,
            api_key: str | None,
            timeout: float,
        ) -> None:
            _ = (endpoint, api_key, timeout)
            self.model = model
            captured["model"] = model

        def generate(self, request: LLMRequest) -> LLMResponse:
            captured["generate_called"] = True
            captured["llm_request"] = request
            return LLMResponse(
                text=(
                    "요약\n"
                    "- 마그네슘은 근육·신경 기능과 관련된 영양소입니다.\n"
                    "주의 조건\n"
                    "- 혈압약을 복용 중이면 혈압약 종류와 신장 기능, 다른 영양제 중복 여부를 함께 봐야 합니다.\n"
                    "오늘 할 일\n"
                    "- 제품 라벨의 마그네슘 함량과 최근 어지러움, 설사, 복통 같은 이상 증상을 확인하세요.\n"
                    "관리 포인트\n"
                    "- 새 보충제 시작이나 복용량 결정은 약 이름과 제품 라벨을 가지고 약사 또는 의사에게 확인하세요.\n"
                    "출처 기준\n"
                    "- KDRIs 영양 기준, MFDS 의약품 안전 정보"
                ),
                provider="sglang",
                model=self.model,
            )

    settings = Settings(
        _env_file=None,
        llm_provider="sglang",
        sglang_base_url="http://127.0.0.1:30000/v1",
        sglang_model="Qwen/Qwen2.5-0.5B-Instruct",
    )
    monkeypatch.setattr(ai_agent, "SGLangClient", _FakeSGLangClient)
    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)
    monkeypatch.setattr(ai_agent, "load_agent_memory_context", _memory_context)

    response = _client(settings=settings).post(
        "/api/v1/ai-agent/chat",
        json=_chat_payload(message="혈압약 먹는데 마그네슘 영양제 같이 먹어도 돼?"),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["provider"] == "sglang"
    assert body["requires_user_approval"] is False
    assert "knowledge_policy" in body["used_tools"]
    assert body["source_families"] == [
        "supplement_reference",
        "drug_safety_boundary",
        "chronic_condition",
    ]
    assert "마그네슘" in body["message"]
    assert "제품 라벨" in body["message"]
    assert "함량" in body["message"]
    assert "혈압약 종류" in body["message"]
    assert "신장 기능" in body["message"]
    assert "어지러움" in body["message"]
    assert "설사" in body["message"]
    assert "복통" in body["message"]
    assert "약사" in body["message"]
    assert "의사" in body["message"]
    assert "먹어도 됩니다" not in body["message"]
    assert "Drug interaction boundary applied" not in body["safety_warnings"]
    assert body["answerability"] == "answerable_with_caution"
    assert any(source["source_id"] == "kdris-2025" for source in body["sources"])
    assert captured["generate_called"] is True


def test_chat_route_unknown_question_fails_closed_without_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify uncovered medical knowledge does not fall through to generic LLM answers."""
    captured: dict[str, int] = {"generate_calls": 0}

    class _FakeSGLangClient:
        """SGLang stand-in that must not generate for unknown-source questions."""

        def __init__(
            self,
            *,
            model: str,
            endpoint: str,
            api_key: str | None,
            timeout: float,
        ) -> None:
            pass

        def generate(self, _request: LLMRequest) -> LLMResponse:
            captured["generate_calls"] += 1
            return LLMResponse(
                text="셀레늄은 리튬과 함께 먹어도 됩니다.",
                provider="sglang",
                model="fake",
            )

    settings = Settings(
        _env_file=None,
        llm_provider="sglang",
        sglang_base_url="http://127.0.0.1:30000/v1",
        sglang_model="Qwen/Qwen2.5-0.5B-Instruct",
    )
    monkeypatch.setattr(ai_agent, "SGLangClient", _FakeSGLangClient)
    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)
    monkeypatch.setattr(ai_agent, "load_agent_memory_context", _memory_context)

    response = _client(settings=settings).post(
        "/api/v1/ai-agent/chat",
        json=_chat_payload(message="리튬 약을 먹는데 셀레늄 영양제 같이 먹어도 돼?"),
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["provider"] == "deterministic"
    assert body["answerability"] == "unknown_no_reviewed_source"
    assert body["sources"] == []
    assert "현재 검수된 지식 안에서 답할 수 없습니다" in body["message"]
    assert "셀레늄은 리튬과 함께 먹어도 됩니다" not in body["message"]
    assert captured["generate_calls"] == 0


def test_chat_route_production_source_gate_fails_closed_before_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify production source governance failures stop chatbot generation."""
    captured: dict[str, int] = {"build_client_calls": 0}

    async def _deny_sources(*_args: object, **_kwargs: object) -> tuple[bool, list[str]]:
        return False, ["no_reviewed_sources"]

    def _capture_llm_client(_settings: Settings) -> object:
        captured["build_client_calls"] += 1
        raise AssertionError("source readiness failure should not build LLM client")

    monkeypatch.setattr(ai_agent, "_production_medical_source_gate", _deny_sources)
    monkeypatch.setattr(ai_agent, "_build_llm_client", _capture_llm_client)
    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)

    response = _client().post("/api/v1/ai-agent/chat", json=_chat_payload())

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["provider"] == "deterministic"
    assert body["answerability"] == "unknown_no_reviewed_source"
    assert body["sources"] == []
    assert body["source_families"] == []
    assert body["used_tools"] == ["medical_source_readiness"]
    assert "no_reviewed_sources" in body["safety_warnings"]
    assert "검수된 의료 지식 출처가 준비되지 않아 답변할 수 없습니다" in body["message"]
    assert captured["build_client_calls"] == 0


def test_chat_route_escalation_boundaries_do_not_call_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify emergency and mental-health risk route to deterministic resources."""
    captured: dict[str, int] = {"generate_calls": 0}

    class _FakeSGLangClient:
        """SGLang stand-in that must not generate for escalation questions."""

        def __init__(
            self,
            *,
            model: str,
            endpoint: str,
            api_key: str | None,
            timeout: float,
        ) -> None:
            pass

        def generate(self, _request: LLMRequest) -> LLMResponse:
            captured["generate_calls"] += 1
            raise AssertionError("escalation response should not call LLM")

    settings = Settings(
        _env_file=None,
        llm_provider="sglang",
        sglang_base_url="http://127.0.0.1:30000/v1",
        sglang_model="Qwen/Qwen2.5-0.5B-Instruct",
    )
    monkeypatch.setattr(ai_agent, "SGLangClient", _FakeSGLangClient)
    monkeypatch.setattr(ai_agent, "require_user_consent", _allow_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)
    monkeypatch.setattr(ai_agent, "load_agent_memory_context", _memory_context)

    emergency = _client(settings=settings).post(
        "/api/v1/ai-agent/chat",
        json=_chat_payload(message="가슴이 아프고 숨이 차"),
    )
    mental = _client(settings=settings).post(
        "/api/v1/ai-agent/chat",
        json=_chat_payload(message="살 빼려고 계속 굶을래"),
    )

    assert emergency.status_code == status.HTTP_200_OK
    assert mental.status_code == status.HTTP_200_OK
    emergency_body = emergency.json()
    mental_body = mental.json()
    assert "심장" in emergency_body["message"] or "폐" in emergency_body["message"]
    assert "단순 피로" in emergency_body["message"] or "소화불량" in emergency_body["message"]
    assert "119" in emergency_body["message"]
    assert "E-Gen" in emergency_body["message"]
    assert "109" in mental_body["message"]
    assert "체중 관리 조언보다 현재 안전 확인" in mental_body["message"]
    assert "Emergency escalation boundary applied" in emergency_body["safety_warnings"]
    assert "Mental health escalation boundary applied" in mental_body["safety_warnings"]
    assert captured["generate_calls"] == 0


def test_chat_route_requires_sensitive_health_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify chatbot route fails closed without sensitive-health consent."""
    monkeypatch.setattr(ai_agent, "require_user_consent", _deny_consent)
    monkeypatch.setattr(ai_agent, "record_sensitive_audit_event", _record_noop_audit)

    response = _client().post("/api/v1/ai-agent/chat", json=_chat_payload())

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["code"] == "consent_required"
