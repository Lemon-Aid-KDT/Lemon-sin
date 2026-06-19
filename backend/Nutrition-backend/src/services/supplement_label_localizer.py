"""Localize user-facing supplement-label text sections to Korean (KR-market display).

OCR'd foreign-language (e.g. English) labels surface English precaution / intake /
functional-claim text in the analysis result. For the Korean-market launch this
localizes those display sections to Korean with a focused local-LLM (Ollama)
translation pass — kept separate from structured parsing, since the section text is
verbatim OCR (not model-generated) and is recovered by deterministic fallbacks.

Design constraints:
- Best-effort: any failure (config, transport, schema, timeout) leaves the original
  text intact — localization never breaks analysis.
- Korean-dominant text is never sent to the model (no needless call / no cost).
- One model call translates all sections together (order-preserved), so latency is a
  single round-trip regardless of how many sections were extracted.
- The chat call is injected (``chat``) so this module is unit-testable without a model
  and decoupled from the live client.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
from typing import Any

# Async callable performing one Ollama /api/chat request (e.g. OllamaChatClient.post_chat).
ChatCallable = Callable[[Mapping[str, Any]], Awaitable[Mapping[str, Any]]]

_HANGUL_START = "가"
_HANGUL_END = "힣"

# Sections whose visible ``text`` is shown verbatim to the user and so must read Korean.
_LIST_SECTION_KEYS = ("precautions", "functional_claims")

# Minimum ASCII letters before a section is considered worth translating (skips units
# like "mg"/"IU" and mostly-Korean text with a stray Latin token).
_MIN_LATIN_LETTERS = 3

_PROMPT = (
    "다음은 영양제 라벨에서 추출한 사용자 표시용 문구들이다. 각 문구를 자연스럽고 정확한 "
    "한국어로 번역하라. 의미를 보존하고, 의료적 단정·과장 없이 라벨 문구 톤을 유지한다. "
    "이미 한국어인 문구는 그대로 둔다. 입력과 같은 개수·같은 순서로 번역만 담아 JSON으로 "
    ' 반환한다. 형식: {"translations": ["...", ...]}. 마크다운 없이 JSON만.\n\n입력:\n'
)


def is_english_dominant(text: str) -> bool:
    """Return whether the text is Latin-dominant enough to be worth translating.

    Args:
        text: Candidate display text.

    Returns:
        True when ASCII letters clearly outnumber Hangul syllables (a foreign-language
        section); False for Korean-dominant or non-textual values.
    """
    latin = sum(1 for char in text if char.isascii() and char.isalpha())
    hangul = sum(1 for char in text if _HANGUL_START <= char <= _HANGUL_END)
    return latin >= _MIN_LATIN_LETTERS and latin > hangul


def build_translation_payload(texts: list[str], model: str) -> dict[str, Any]:
    """Build the Ollama /api/chat payload that translates the texts to Korean."""
    numbered = "\n".join(f"{index + 1}. {text}" for index, text in enumerate(texts))
    return {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
        "messages": [{"role": "user", "content": _PROMPT + numbered}],
    }


def _message_content(data: Mapping[str, Any]) -> str:
    """Extract the assistant message content from an Ollama chat response."""
    message = data.get("message")
    if isinstance(message, Mapping):
        content = message.get("content")
        if isinstance(content, str):
            return content
    return ""


def parse_translations(content: str, expected: int) -> list[str] | None:
    """Parse the model's JSON content into exactly ``expected`` non-empty translations.

    Args:
        content: Raw assistant message content (expected JSON).
        expected: Number of input texts that must be translated.

    Returns:
        The translations in order, or None when the output is malformed, the count
        does not match, or any entry is blank (best-effort: caller keeps originals).
    """
    try:
        obj = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None
    rows = obj.get("translations") if isinstance(obj, Mapping) else obj
    if not isinstance(rows, list) or len(rows) != expected:
        return None
    out: list[str] = []
    for row in rows:
        if not isinstance(row, str) or not row.strip():
            return None
        out.append(row.strip())
    return out


def _collect_targets(snapshot: dict[str, Any]) -> list[tuple[str, int | None]]:
    """Return (section_key, list_index|None) locations of English-dominant section text."""
    targets: list[tuple[str, int | None]] = []
    intake = snapshot.get("intake_method")
    if (
        isinstance(intake, dict)
        and isinstance(intake.get("text"), str)
        and is_english_dominant(intake["text"])
    ):
        targets.append(("intake_method", None))
    for key in _LIST_SECTION_KEYS:
        value = snapshot.get(key)
        if not isinstance(value, list):
            continue
        for index, item in enumerate(value):
            if (
                isinstance(item, dict)
                and isinstance(item.get("text"), str)
                and is_english_dominant(item["text"])
            ):
                targets.append((key, index))
    return targets


def _text_at(snapshot: dict[str, Any], key: str, index: int | None) -> str:
    """Read the section text for a collected target location."""
    if index is None:
        return snapshot[key]["text"]
    return snapshot[key][index]["text"]


def _set_text_at(snapshot: dict[str, Any], key: str, index: int | None, text: str) -> None:
    """Write the translated text back into the snapshot at a target location."""
    if index is None:
        snapshot[key]["text"] = text
    else:
        snapshot[key][index]["text"] = text


async def localize_snapshot_to_korean(
    snapshot: dict[str, Any],
    *,
    chat: ChatCallable,
    model: str,
) -> dict[str, Any]:
    """Return a snapshot whose English display sections are translated to Korean.

    Translates ``precautions[].text``, ``intake_method.text`` and
    ``functional_claims[].text`` when they are English-dominant. Best-effort: when
    nothing needs translating the input snapshot is returned unchanged (no model
    call); on any failure the original snapshot is returned.

    Args:
        snapshot: Parsed snapshot dict (not mutated; a copy is returned on change).
        chat: Injected async Ollama chat callable.
        model: Translation model name.

    Returns:
        The snapshot with localized section text, or the original on no-op/failure.
    """
    targets = _collect_targets(snapshot)
    if not targets:
        return snapshot
    texts = [_text_at(snapshot, key, index) for key, index in targets]
    try:
        data = await chat(build_translation_payload(texts, model))
    except Exception:
        # Best-effort enrichment: a translation failure (config / transport / timeout)
        # must never break analysis — keep the original (foreign-language) text.
        return snapshot
    translations = parse_translations(_message_content(data), len(texts))
    if translations is None:
        return snapshot
    localized = deepcopy(snapshot)
    for (key, index), translated in zip(targets, translations, strict=True):
        _set_text_at(localized, key, index, translated)
    return localized
