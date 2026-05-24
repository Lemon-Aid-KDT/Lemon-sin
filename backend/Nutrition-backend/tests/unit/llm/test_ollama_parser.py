"""Ollama supplement parser adapter tests."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import httpx
import pytest
from src.config import Settings
from src.llm.ollama import (
    MAX_OLLAMA_OCR_PROMPT_CHARS,
    TRUNCATED_OCR_TEXT_MARKER,
    OllamaChatClient,
    OllamaClientError,
    OllamaConfigurationError,
    OllamaStructuredOutputError,
    OllamaSupplementParser,
    check_ollama_readiness,
)


class _FakeResponse:
    """Fake HTTP response for Ollama adapter tests."""

    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise an HTTP status error when configured to do so.

        Returns:
            None.
        """
        if self.status_code < 400:
            return
        request = httpx.Request("GET", "http://127.0.0.1:11434/api/test")
        response = httpx.Response(self.status_code, request=request)
        raise httpx.HTTPStatusError("Fake Ollama status error.", request=request, response=response)

    def json(self) -> Any:
        """Return the configured response payload.

        Returns:
            Fake JSON payload.
        """
        return self.payload


class _FakeHTTPClient:
    """Fake async HTTP client that captures the submitted request."""

    def __init__(
        self,
        post_payload: Any = None,
        *,
        get_payload: Any = None,
        post_status_code: int = 200,
        get_status_code: int = 200,
    ) -> None:
        self.post_payload = post_payload
        self.get_payload = get_payload if get_payload is not None else {"models": []}
        self.post_status_code = post_status_code
        self.get_status_code = get_status_code
        self.post_url: str | None = None
        self.get_url: str | None = None
        self.request_json: Mapping[str, Any] | None = None
        self.post_timeout: float | None = None
        self.get_timeout: float | None = None

    async def post(
        self,
        url: str,
        *,
        json: Mapping[str, Any],
        timeout: float,
    ) -> _FakeResponse:
        """Capture the request and return the fake response.

        Args:
            url: Request URL.
            json: Request JSON payload.
            timeout: Request timeout.

        Returns:
            Fake HTTP response.
        """
        self.post_url = url
        self.request_json = json
        self.post_timeout = timeout
        return _FakeResponse(self.post_payload, self.post_status_code)

    async def get(
        self,
        url: str,
        *,
        timeout: float,
    ) -> _FakeResponse:
        """Capture the request and return the fake response.

        Args:
            url: Request URL.
            timeout: Request timeout.

        Returns:
            Fake HTTP response.
        """
        self.get_url = url
        self.get_timeout = timeout
        return _FakeResponse(self.get_payload, self.get_status_code)


def _settings(
    *,
    ollama_base_url: str = "http://127.0.0.1:11434",
    ollama_temperature: float = 0.0,
) -> Settings:
    """Return settings for Ollama parser tests.

    Args:
        ollama_base_url: Ollama endpoint used by the parser.
        ollama_temperature: Sampling temperature sent to Ollama.

    Returns:
        Settings object.
    """
    return Settings(
        ollama_base_url=ollama_base_url,
        ollama_temperature=ollama_temperature,
    )


@pytest.mark.asyncio
async def test_ollama_parser_posts_json_schema_and_validates_content() -> None:
    """Verify the adapter sends JSON Schema and validates the structured response."""
    response_content = json.dumps(
        {
            "parsed_product": {
                "product_name": "비타민 D 1000",
                "serving_size": "1 tablet",
                "daily_servings": 1,
            },
            "ingredient_candidates": [
                {
                    "display_name": "비타민 D",
                    "amount": 25,
                    "unit": "ug",
                    "confidence": 0.91,
                }
            ],
            "low_confidence_fields": ["manufacturer"],
            "warnings": [],
        },
        ensure_ascii=False,
    )
    fake_client = _FakeHTTPClient({"message": {"content": response_content}})

    result = await OllamaSupplementParser(
        _settings(ollama_temperature=0),
        http_client=fake_client,
    ).parse_supplement_ocr_text("비타민 D 1000\n1정당 비타민 D 25 ug")

    assert fake_client.post_url == "http://127.0.0.1:11434/api/chat"
    assert fake_client.post_timeout == 60
    assert fake_client.request_json is not None
    assert fake_client.request_json["model"] == "qwen3.5:9b"
    assert fake_client.request_json["stream"] is False
    assert fake_client.request_json["think"] is False
    assert fake_client.request_json["format"]["type"] == "object"
    assert fake_client.request_json["options"] == {"temperature": 0.0}
    assert result.parsed_product.product_name == "비타민 D 1000"
    assert result.ingredient_candidates[0].source == "ollama_structured"


@pytest.mark.asyncio
async def test_ollama_parser_bounds_long_ocr_text_in_prompt() -> None:
    """Verify long OCR text is compacted before local structured-output calls."""
    response_content = json.dumps({"ingredient_candidates": []}, ensure_ascii=False)
    fake_client = _FakeHTTPClient({"message": {"content": response_content}})
    long_ocr_text = "비타민 D 25 ug\n" + ("middle-noise-line\n" * 1200) + "마그네슘 100 mg\n"

    await OllamaSupplementParser(
        _settings(),
        http_client=fake_client,
    ).parse_supplement_ocr_text(long_ocr_text)

    assert fake_client.request_json is not None
    assert fake_client.request_json["format"]["type"] == "object"
    user_prompt = fake_client.request_json["messages"][1]["content"]
    assert len(user_prompt) < len(long_ocr_text)
    assert TRUNCATED_OCR_TEXT_MARKER in user_prompt
    assert "비타민 D 25 ug" in user_prompt
    assert "마그네슘 100 mg" in user_prompt
    assert len(user_prompt) < MAX_OLLAMA_OCR_PROMPT_CHARS + 1_000


@pytest.mark.asyncio
async def test_ollama_parser_rejects_schema_invalid_content() -> None:
    """Verify invalid model output is rejected after the Ollama call."""
    fake_client = _FakeHTTPClient({"message": {"content": '{"unexpected": true}'}})

    with pytest.raises(OllamaStructuredOutputError):
        await OllamaSupplementParser(
            _settings(),
            http_client=fake_client,
        ).parse_supplement_ocr_text("비타민 D")


@pytest.mark.asyncio
async def test_ollama_parser_rejects_malformed_json_content() -> None:
    """Verify malformed structured content is rejected."""
    fake_client = _FakeHTTPClient({"message": {"content": "{not-json"}})

    with pytest.raises(OllamaStructuredOutputError):
        await OllamaSupplementParser(
            _settings(),
            http_client=fake_client,
        ).parse_supplement_ocr_text("비타민 D")


@pytest.mark.asyncio
async def test_ollama_parser_discards_non_null_nutrient_code() -> None:
    """Verify the LLM cannot persist invented internal nutrient codes."""
    response_content = json.dumps(
        {
            "ingredient_candidates": [
                {
                    "display_name": "비타민 D",
                    "nutrient_code": "VITAMIN_D",
                    "confidence": 0.8,
                }
            ]
        },
        ensure_ascii=False,
    )
    fake_client = _FakeHTTPClient({"message": {"content": response_content}})

    result = await OllamaSupplementParser(
        _settings(),
        http_client=fake_client,
    ).parse_supplement_ocr_text("비타민 D")

    assert result.ingredient_candidates[0].nutrient_code is None


@pytest.mark.asyncio
async def test_ollama_parser_normalizes_common_model_shape_aliases() -> None:
    """Verify common model output aliases are normalized before validation."""
    response_content = json.dumps(
        {
            "product": {
                "product_name": "오메가3",
                "serving_size": "1 capsule",
                "raw_ocr_text": "must not persist",
            },
            "ingredients": [
                {
                    "name": "EPA",
                    "quantity": "180",
                    "units": "mg",
                    "nutrient_code": "EPA",
                    "source": "model_generated",
                    "extra": "ignored",
                }
            ],
            "low_confidence_fields": "ingredient_candidates[0].confidence",
            "warnings": ["needs_review"],
            "raw_model_response": "must not persist",
        },
        ensure_ascii=False,
    )
    fake_client = _FakeHTTPClient({"message": {"content": response_content}})

    result = await OllamaSupplementParser(
        _settings(),
        http_client=fake_client,
    ).parse_supplement_ocr_text("EPA 180 mg")

    ingredient = result.ingredient_candidates[0]
    assert result.parsed_product.product_name == "오메가3"
    assert result.parsed_product.serving_size == "1 capsule"
    assert ingredient.display_name == "EPA"
    assert ingredient.amount == 180
    assert ingredient.unit == "mg"
    assert ingredient.nutrient_code is None
    assert ingredient.confidence == 0.0
    assert ingredient.source == "ollama_structured"
    assert result.low_confidence_fields == ["ingredient_candidates[0].confidence"]
    assert result.warnings == ["needs_review"]
    serialized = result.model_dump_json()
    assert "raw_ocr_text" not in serialized
    assert "raw_model_response" not in serialized


@pytest.mark.asyncio
async def test_ollama_parser_downgrades_invalid_confidence() -> None:
    """Verify malformed confidence does not invalidate visible ingredients."""
    response_content = json.dumps(
        {
            "ingredient_candidates": [
                {
                    "display_name": "비타민 D",
                    "confidence": 1.2,
                }
            ]
        },
        ensure_ascii=False,
    )
    fake_client = _FakeHTTPClient({"message": {"content": response_content}})

    result = await OllamaSupplementParser(
        _settings(),
        http_client=fake_client,
    ).parse_supplement_ocr_text("비타민 D")

    assert result.ingredient_candidates[0].confidence == 0.0


@pytest.mark.asyncio
async def test_ollama_parser_decodes_fenced_json_content() -> None:
    """Verify common fenced JSON responses are decoded without storing raw text."""
    response_content = (
        "```json\n"
        + json.dumps(
            {
                "ingredient_candidates": [
                    {
                        "display_name": "마그네슘",
                        "amount": "100",
                        "unit": "mg",
                        "confidence": "0.7",
                    }
                ]
            },
            ensure_ascii=False,
        )
        + "\n```"
    )
    fake_client = _FakeHTTPClient({"message": {"content": response_content}})

    result = await OllamaSupplementParser(
        _settings(),
        http_client=fake_client,
    ).parse_supplement_ocr_text("마그네슘 100 mg")

    ingredient = result.ingredient_candidates[0]
    assert ingredient.display_name == "마그네슘"
    assert ingredient.amount == 100
    assert ingredient.confidence == 0.7


@pytest.mark.asyncio
async def test_ollama_parser_rejects_missing_message_content() -> None:
    """Verify malformed Ollama chat responses are rejected before validation."""
    fake_client = _FakeHTTPClient({"message": {}})

    with pytest.raises(OllamaClientError):
        await OllamaSupplementParser(
            _settings(),
            http_client=fake_client,
        ).parse_supplement_ocr_text("비타민 D")


@pytest.mark.asyncio
async def test_ollama_parser_rejects_non_object_response_body() -> None:
    """Verify non-object Ollama responses are rejected."""
    fake_client = _FakeHTTPClient(["not", "an", "object"])

    with pytest.raises(OllamaClientError):
        await OllamaSupplementParser(
            _settings(),
            http_client=fake_client,
        ).parse_supplement_ocr_text("비타민 D")


@pytest.mark.asyncio
async def test_ollama_parser_blocks_remote_base_url_when_external_llm_disabled() -> None:
    """Verify sensitive OCR text is not sent to non-local Ollama endpoints by default."""
    fake_client = _FakeHTTPClient({"message": {"content": "{}"}})

    with pytest.raises(OllamaConfigurationError):
        await OllamaSupplementParser(
            _settings(ollama_base_url="https://ollama.example.com"),
            http_client=fake_client,
        ).parse_supplement_ocr_text("비타민 D")

    assert fake_client.request_json is None


@pytest.mark.asyncio
async def test_check_ollama_readiness_reports_ready_for_installed_model() -> None:
    """Verify readiness succeeds when the configured model is present."""
    settings = _settings()
    fake_client = _FakeHTTPClient(
        get_payload={
            "models": [
                {"name": "qwen3.5:9b", "model": "qwen3.5:9b"},
                {"name": "gemma4:e4b"},
            ]
        }
    )
    chat_client = OllamaChatClient(settings, http_client=fake_client)

    readiness = await check_ollama_readiness(settings, chat_client)

    assert readiness.ready is True
    assert readiness.model_present is True
    assert readiness.error_code is None
    assert readiness.model_names == ("qwen3.5:9b", "gemma4:e4b")
    assert fake_client.get_url == "http://127.0.0.1:11434/api/tags"
    assert fake_client.get_timeout == 60


@pytest.mark.asyncio
async def test_check_ollama_readiness_reports_missing_model() -> None:
    """Verify readiness reports a missing configured model without raising."""
    settings = _settings()
    fake_client = _FakeHTTPClient(get_payload={"models": [{"name": "gemma4:e4b"}]})
    chat_client = OllamaChatClient(settings, http_client=fake_client)

    readiness = await check_ollama_readiness(settings, chat_client)

    assert readiness.ready is False
    assert readiness.model_present is False
    assert readiness.error_code == "model_missing"
    assert readiness.model_names == ("gemma4:e4b",)


@pytest.mark.asyncio
async def test_check_ollama_readiness_blocks_remote_base_url() -> None:
    """Verify readiness does not call a remote URL when external LLM is disabled."""
    settings = _settings(ollama_base_url="https://ollama.example.com")
    fake_client = _FakeHTTPClient(get_payload={"models": [{"name": "qwen3.5:9b"}]})
    chat_client = OllamaChatClient(settings, http_client=fake_client)

    readiness = await check_ollama_readiness(settings, chat_client)

    assert readiness.ready is False
    assert readiness.error_code == "configuration_invalid"
    assert fake_client.get_url is None


@pytest.mark.asyncio
async def test_check_ollama_readiness_handles_unavailable_api() -> None:
    """Verify readiness returns a stable status when Ollama is unavailable."""
    settings = _settings()
    fake_client = _FakeHTTPClient(get_payload={"error": "unavailable"}, get_status_code=500)
    chat_client = OllamaChatClient(settings, http_client=fake_client)

    readiness = await check_ollama_readiness(settings, chat_client)

    assert readiness.ready is False
    assert readiness.model_present is False
    assert readiness.error_code == "ollama_unavailable"
