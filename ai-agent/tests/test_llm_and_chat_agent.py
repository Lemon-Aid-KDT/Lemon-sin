import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lemon_ai_agent.agents.chat import ChatAgent
from lemon_ai_agent.llm import (
    FakeLLMClient,
    LLMMessage,
    LLMRequest,
    OllamaClient,
    OpenAICompatibleClient,
    SGLangClient,
)
from lemon_ai_agent.schemas import (
    CoachingRecommendation,
    DailyCoachingResult,
    FindingLevel,
    NutrientFinding,
)


class _FailingLLMClient:
    def generate(self, request: LLMRequest):
        raise RuntimeError("local server unavailable")


class _CapturingLLMClient:
    def __init__(self) -> None:
        self.request: LLMRequest | None = None

    def generate(self, request: LLMRequest):
        self.request = request
        return FakeLLMClient(
            response_text="현재 입력된 정보 기준으로 설명합니다."
        ).generate(request)


class _FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def _sample_result() -> DailyCoachingResult:
    return DailyCoachingResult(
        user_id="user-llm",
        date="2026-05-18",
        findings=[
            NutrientFinding(
                nutrient="sodium",
                total_amount=2600,
                unit="mg",
                ratio_to_target=1.3,
                level=FindingLevel.RISKY,
                message="Sodium is above the upper limit.",
            )
        ],
        recommendations=[
            CoachingRecommendation(
                category="reduce",
                title="Reduce sodium",
                rationale="주의가 필요할 수 있습니다. 현재 입력된 정보 기준입니다.",
                priority=10,
                requires_professional_consult=True,
            )
        ],
        actions=[],
        safety_warnings=[],
        trace=[
            "intake normalized: foods=1, supplements=0, confirmed source records: 1",
            "nutrition findings: sodium=risky",
            "policy guard warnings: 0",
        ],
    )


class LLMAndChatAgentTest(unittest.TestCase):
    def test_fake_llm_client_returns_fixed_response(self) -> None:
        client = FakeLLMClient(response_text="현재 입력된 정보 기준으로 설명합니다.")

        response = client.generate(
            LLMRequest(
                messages=[
                    LLMMessage(role="user", content="Explain the trace."),
                ]
            )
        )

        self.assertEqual(response.text, "현재 입력된 정보 기준으로 설명합니다.")
        self.assertEqual(response.provider, "fake")
        self.assertEqual(response.model, "fake-local-llm")

    def test_chat_agent_without_llm_uses_deterministic_fallback(self) -> None:
        answer = ChatAgent().answer("Why this?", _sample_result())

        self.assertIn("현재 입력 기준", answer)
        self.assertIn("전문가와 상담", answer)
        self.assertNotIn("For your question", answer)
        self.assertNotIn("Trace:", answer)
        self.assertNotIn("Source families:", answer)
        self.assertNotIn("diagnosis", answer.lower())
        self.assertNotIn("diabetes", answer.lower())
        self.assertNotIn("prescribe", answer.lower())

    def test_chat_agent_returns_safe_fake_llm_response(self) -> None:
        client = FakeLLMClient(
            response_text=(
                "현재 입력된 정보 기준으로 나트륨 섭취에 주의가 필요할 수 있습니다. "
                "전문가 상담을 권장합니다."
            )
        )

        answer = ChatAgent(llm_client=client).answer("Why this?", _sample_result())

        self.assertEqual(answer, client.response_text)

    def test_chat_agent_blocks_unsafe_llm_response(self) -> None:
        client = FakeLLMClient(response_text="당뇨입니다. 이 제품을 구매하세요.")
        agent = ChatAgent(llm_client=client)

        answer = agent.answer("Why this?", _sample_result())

        self.assertNotEqual(answer, client.response_text)
        self.assertIn("현재 입력 기준", answer)
        self.assertTrue(agent.last_llm_warnings)

    def test_chat_agent_falls_back_when_llm_fails(self) -> None:
        agent = ChatAgent(llm_client=_FailingLLMClient())

        answer = agent.answer("Why this?", _sample_result())

        self.assertIn("현재 입력 기준", answer)
        self.assertEqual(agent.last_llm_error, "local server unavailable")

    def test_chat_agent_sanitizes_trace_before_fallback_and_llm_prompt(self) -> None:
        result = DailyCoachingResult(
            user_id="user-unsafe-trace",
            date="2026-05-18",
            findings=[],
            recommendations=[],
            actions=[],
            safety_warnings=[],
            trace=["당뇨입니다. 이 제품을 구매하세요."],
        )
        client = _CapturingLLMClient()
        agent = ChatAgent(llm_client=client)

        answer = agent.answer("Why this?", result)
        prompt_text = "\n".join(message.content for message in client.request.messages)

        self.assertIn("trace item withheld by policy guard", prompt_text)
        self.assertNotIn("당뇨입니다", prompt_text)
        self.assertNotIn("제품을 구매", prompt_text)
        self.assertNotIn("당뇨입니다", answer)
        self.assertNotIn("제품을 구매", answer)
        self.assertTrue(agent.last_llm_warnings)

    def test_chat_agent_uses_low_temperature_for_health_explanation(self) -> None:
        client = _CapturingLLMClient()
        agent = ChatAgent(llm_client=client)

        agent.answer("Why this?", _sample_result())

        self.assertIsNotNone(client.request)
        self.assertEqual(client.request.temperature, 0.1)

    def test_chat_agent_withholds_raw_ocr_image_and_prompt_trace(self) -> None:
        result = DailyCoachingResult(
            user_id="user-sensitive-trace",
            date="2026-05-18",
            findings=[],
            recommendations=[],
            actions=[],
            safety_warnings=[],
            trace=[
                "raw_ocr_text: instant noodles sodium 2600mg",
                "image_id: meal-image-1",
                "raw_llm_response: internal chain output",
                "full_prompt: hidden prompt content",
            ],
        )
        client = _CapturingLLMClient()
        agent = ChatAgent(llm_client=client)

        answer = agent.answer("Why this?", result)
        prompt_text = "\n".join(message.content for message in client.request.messages)

        self.assertIn("trace item withheld by policy guard", prompt_text)
        self.assertNotIn("instant noodles sodium 2600mg", prompt_text)
        self.assertNotIn("meal-image-1", prompt_text)
        self.assertNotIn("internal chain output", prompt_text)
        self.assertNotIn("hidden prompt content", prompt_text)
        self.assertNotIn("instant noodles sodium 2600mg", answer)
        self.assertTrue(agent.last_llm_warnings)

    def test_ollama_client_sends_chat_payload(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return _FakeHTTPResponse({"message": {"content": "ok"}})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = OllamaClient(
                endpoint="http://127.0.0.1:11434",
                model="qwen2.5:7b-instruct",
                timeout=7,
            ).generate(
                LLMRequest(
                    messages=[LLMMessage(role="user", content="hello")],
                    temperature=0.1,
                    max_tokens=128,
                )
            )

        self.assertEqual(captured["url"], "http://127.0.0.1:11434/api/chat")
        self.assertEqual(captured["timeout"], 7)
        self.assertEqual(captured["body"]["model"], "qwen2.5:7b-instruct")
        self.assertEqual(captured["body"]["messages"][0]["content"], "hello")
        self.assertEqual(captured["body"]["options"]["temperature"], 0.1)
        self.assertEqual(captured["body"]["options"]["num_predict"], 128)
        self.assertFalse(captured["body"]["stream"])
        self.assertEqual(response.text, "ok")

    def test_openai_compatible_client_sends_chat_payload_and_auth(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["authorization"] = request.get_header("Authorization")
            return _FakeHTTPResponse({"choices": [{"message": {"content": "ok"}}]})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = OpenAICompatibleClient(
                endpoint="http://127.0.0.1:8000/v1",
                model="llama-local",
                api_key=None,
                timeout=9,
            ).generate(
                LLMRequest(
                    messages=[LLMMessage(role="user", content="hello")],
                    temperature=0.3,
                    max_tokens=256,
                )
            )

        self.assertEqual(
            captured["url"], "http://127.0.0.1:8000/v1/chat/completions"
        )
        self.assertEqual(captured["timeout"], 9)
        self.assertEqual(captured["authorization"], "Bearer EMPTY")
        self.assertEqual(captured["body"]["model"], "llama-local")
        self.assertEqual(captured["body"]["messages"][0]["role"], "user")
        self.assertEqual(captured["body"]["temperature"], 0.3)
        self.assertEqual(captured["body"]["max_tokens"], 256)
        self.assertEqual(response.text, "ok")

    def test_sglang_client_sends_json_schema_response_format(self) -> None:
        captured = {}
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "coaching_summary",
                "schema": {
                    "type": "object",
                    "properties": {"summary": {"type": "string"}},
                    "required": ["summary"],
                    "additionalProperties": False,
                },
            },
        }

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["authorization"] = request.get_header("Authorization")
            return _FakeHTTPResponse({"choices": [{"message": {"content": "ok"}}]})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = SGLangClient(
                endpoint="http://127.0.0.1:30000/v1",
                model="qwen-local",
                api_key=None,
                timeout=11,
            ).generate(
                LLMRequest(
                    messages=[LLMMessage(role="user", content="hello")],
                    temperature=0.0,
                    max_tokens=128,
                    response_format=response_format,
                )
            )

        self.assertEqual(
            captured["url"], "http://127.0.0.1:30000/v1/chat/completions"
        )
        self.assertEqual(captured["timeout"], 11)
        self.assertEqual(captured["authorization"], "Bearer EMPTY")
        self.assertEqual(captured["body"]["model"], "qwen-local")
        self.assertEqual(captured["body"]["response_format"], response_format)
        self.assertEqual(response.text, "ok")
        self.assertEqual(response.provider, "sglang")


if __name__ == "__main__":
    unittest.main()
