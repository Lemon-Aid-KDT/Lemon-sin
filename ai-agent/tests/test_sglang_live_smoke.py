import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lemon_ai_agent.llm import LLMMessage, LLMRequest, SGLangClient


class SGLangLiveSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        if os.environ.get("RUN_SGLANG_SMOKE") != "1":
            self.skipTest("set RUN_SGLANG_SMOKE=1 to call a live SGLang server")

    def test_sglang_client_calls_live_chat_completions(self) -> None:
        endpoint = os.environ.get("SGLANG_BASE_URL", "http://localhost:30000/v1")
        model = os.environ.get("SGLANG_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
        api_key = os.environ.get("SGLANG_API_KEY", "EMPTY")
        timeout = float(os.environ.get("SGLANG_TIMEOUT", "60"))

        client = SGLangClient(
            endpoint=endpoint,
            model=model,
            api_key=api_key,
            timeout=timeout,
        )

        try:
            response = client.generate(
                LLMRequest(
                    messages=[
                        LLMMessage(
                            role="system",
                            content=(
                                "You are validating a local SGLang server. "
                                "Reply with one short safe sentence. Do not diagnose, "
                                "treat, prescribe, or promote a product."
                            ),
                        ),
                        LLMMessage(
                            role="user",
                            content="Say that the local SGLang smoke test is working.",
                        ),
                    ],
                    temperature=0.0,
                    max_tokens=64,
                )
            )
        except RuntimeError as exc:
            self.skipTest(f"SGLang server is not reachable at {endpoint}: {exc}")

        self.assertEqual(response.provider, "sglang")
        self.assertEqual(response.model, model)
        self.assertTrue(response.text.strip())


if __name__ == "__main__":
    unittest.main()
