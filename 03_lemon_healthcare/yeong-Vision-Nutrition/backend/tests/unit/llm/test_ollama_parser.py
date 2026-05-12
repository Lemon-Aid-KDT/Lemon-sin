"""Ollama supplement parser adapter tests."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest

from src.config import Settings
from src.llm.ollama import (
    OllamaConfigurationError,
    OllamaStructuredOutputError,
    OllamaSupplementParser,
)


class _FakeResponse:
    """Fake HTTP response for Ollama adapter tests."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        """Return successfully for fake responses.

        Returns:
            None.
        """

    def json(self) -> Mapping[str, Any]:
        """Return the configured response payload.

        Returns:
            Fake JSON payload.
        """
        return self.payload


class _FakeHTTPClient:
    """Fake async HTTP client that captures the submitted request."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = payload
        self.url: str | None = None
        self.request_json: Mapping[str, Any] | None = None
        self.timeout: float | None = None

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
        self.url = url
        self.request_json = json
        self.timeout = timeout
        return _FakeResponse(self.payload)


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

    assert fake_client.url == "http://127.0.0.1:11434/api/chat"
    assert fake_client.timeout == 60
    assert fake_client.request_json is not None
    assert fake_client.request_json["model"] == "qwen3.5:9b"
    assert fake_client.request_json["stream"] is False
    assert fake_client.request_json["think"] is False
    assert fake_client.request_json["format"]["type"] == "object"
    assert fake_client.request_json["options"] == {"temperature": 0.0}
    assert result.parsed_product.product_name == "비타민 D 1000"
    assert result.ingredient_candidates[0].source == "ollama_structured"


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
async def test_ollama_parser_blocks_remote_base_url_when_external_llm_disabled() -> None:
    """Verify sensitive OCR text is not sent to non-local Ollama endpoints by default."""
    fake_client = _FakeHTTPClient({"message": {"content": "{}"}})

    with pytest.raises(OllamaConfigurationError):
        await OllamaSupplementParser(
            _settings(ollama_base_url="https://ollama.example.com"),
            http_client=fake_client,
        ).parse_supplement_ocr_text("비타민 D")

    assert fake_client.request_json is None
