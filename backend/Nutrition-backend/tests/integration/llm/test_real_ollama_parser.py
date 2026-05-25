"""Opt-in live smoke tests for the local Ollama supplement parser."""

from __future__ import annotations

import os

import pytest
from src.config import Settings
from src.llm.ollama import OllamaChatClient, OllamaSupplementParser, check_ollama_readiness

RUN_OLLAMA_TESTS = os.getenv("RUN_OLLAMA_TESTS", "").lower() == "true"


pytestmark = pytest.mark.skipif(
    not RUN_OLLAMA_TESTS,
    reason="Set RUN_OLLAMA_TESTS=true to run local Ollama live smoke tests.",
)


def _live_settings() -> Settings:
    """Return settings for a local Ollama live smoke run."""
    return Settings(ollama_timeout_sec=180)


@pytest.mark.asyncio
async def test_real_ollama_parser_returns_schema_valid_result() -> None:
    """Verify local Ollama can parse a small OCR sample into validated JSON."""
    settings = _live_settings()
    readiness = await check_ollama_readiness(settings, OllamaChatClient(settings))

    assert readiness.ready is True
    assert readiness.error_code is None
    assert settings.ollama_model in readiness.model_names

    result = await OllamaSupplementParser(settings).parse_supplement_ocr_text(
        "Product: Lemon Vitamin D. "
        "Ingredient: Vitamin D 25 mcg. "
        "Serving: 1 tablet once daily."
    )

    assert result.ingredient_candidates
    first_ingredient = result.ingredient_candidates[0]
    assert "vitamin" in first_ingredient.display_name.lower()
    assert first_ingredient.amount == 25
    assert first_ingredient.unit in {"mcg", "ug", "µg"}
    assert first_ingredient.source == "ollama_structured"
