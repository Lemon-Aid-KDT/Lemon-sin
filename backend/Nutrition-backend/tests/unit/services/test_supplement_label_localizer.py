"""Tests for Korean localization of supplement-label display sections (KR market)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest
from src.services.supplement_label_localizer import (
    build_translation_payload,
    is_english_dominant,
    localize_snapshot_to_korean,
    parse_translations,
)


def _chat_returning(translations: list[str]):
    """Fake chat callable returning the given translations as JSON."""

    async def _chat(_payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"message": {"content": json.dumps({"translations": translations})}}

    return _chat


def test_is_english_dominant() -> None:
    assert is_english_dominant("Consult your physician before using")
    assert not is_english_dominant("1일 1정 섭취하십시오")
    assert not is_english_dominant("mg")  # too few letters to bother translating


def test_build_payload_is_json_mode_and_carries_texts() -> None:
    payload = build_translation_payload(["Store in a cool dry place"], "gemma4:e4b")
    assert payload["format"] == "json"
    assert payload["options"]["temperature"] == 0
    assert "Store in a cool dry place" in payload["messages"][0]["content"]


def test_parse_translations_guards() -> None:
    assert parse_translations(json.dumps({"translations": ["가", "나"]}), 2) == ["가", "나"]
    assert parse_translations(json.dumps({"translations": ["가"]}), 2) is None  # count mismatch
    assert parse_translations("not json", 1) is None
    assert parse_translations(json.dumps({"translations": [""]}), 1) is None  # blank entry


@pytest.mark.asyncio
async def test_localizes_only_english_sections_without_mutating_input() -> None:
    snapshot = {
        "intake_method": {"text": "Take one tablet daily."},
        "precautions": [{"text": "Consult your physician before using."}],
        "functional_claims": [{"text": "장 건강에 도움을 줄 수 있음"}],  # Korean → skipped
    }
    # _collect_targets order: intake_method first, then list sections.
    out = await localize_snapshot_to_korean(
        snapshot,
        chat=_chat_returning(["1일 1정 섭취", "사용 전 의사와 상담하십시오"]),
        model="m",
    )
    assert out["intake_method"]["text"] == "1일 1정 섭취"
    assert out["precautions"][0]["text"] == "사용 전 의사와 상담하십시오"
    assert out["functional_claims"][0]["text"] == "장 건강에 도움을 줄 수 있음"  # unchanged
    # original snapshot is not mutated (a copy is returned)
    assert snapshot["precautions"][0]["text"] == "Consult your physician before using."


@pytest.mark.asyncio
async def test_korean_snapshot_makes_no_model_call() -> None:
    snapshot = {"precautions": [{"text": "임신 중에는 섭취 전 전문가와 상담하십시오."}]}
    called = False

    async def _chat(_payload: Mapping[str, Any]) -> Mapping[str, Any]:
        nonlocal called
        called = True
        return {"message": {"content": "{}"}}

    out = await localize_snapshot_to_korean(snapshot, chat=_chat, model="m")
    assert out is snapshot
    assert called is False


@pytest.mark.asyncio
async def test_best_effort_keeps_original_on_chat_failure() -> None:
    snapshot = {"precautions": [{"text": "Store in a cool dry place."}]}

    async def _boom(_payload: Mapping[str, Any]) -> Mapping[str, Any]:
        raise RuntimeError("ollama unreachable")

    out = await localize_snapshot_to_korean(snapshot, chat=_boom, model="m")
    assert out["precautions"][0]["text"] == "Store in a cool dry place."


@pytest.mark.asyncio
async def test_best_effort_keeps_original_on_count_mismatch() -> None:
    snapshot = {
        "precautions": [
            {"text": "Consult your physician."},
            {"text": "Keep out of reach of children."},
        ],
    }
    out = await localize_snapshot_to_korean(
        snapshot, chat=_chat_returning(["하나만 번역"]), model="m"
    )
    assert out["precautions"][0]["text"] == "Consult your physician."
    assert out["precautions"][1]["text"] == "Keep out of reach of children."
