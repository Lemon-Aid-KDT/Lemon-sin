"""Output-stage sanitization for free-text fields parsed by the LLM.

These helpers run *after* Pydantic validation against
``SupplementStructuredParseResult`` so the parser schema continues to be the
authority on field types, lengths, and required-ness. Sanitization focuses on
*content* threats — prompt-injection markers, HTML, SQL injection patterns,
and URLs — without applying aggressive character-class allowlists that risk
mutilating legitimate Korean / multilingual supplement label text.

Each helper returns a :class:`SanitizerResult` carrying the (possibly
modified) value and a tuple of warning codes. When a value is fully blocked
the helper returns an empty string; the caller decides whether to drop the
field, raise, or keep an empty string visible in the preview.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_URL_PATTERN = re.compile(r"https?://|www\.", re.IGNORECASE)
_HTML_TAG = re.compile(r"<[^>]+>")
_SQL_INJECTION = re.compile(
    r"\b(drop\s+table|truncate\s+table|union\s+select|--\s|/\*)", re.IGNORECASE
)
_INJECTION_KEYWORDS: tuple[str, ...] = (
    "IGNORE PREVIOUS",
    "IGNORE PRIOR",
    "IGNORE ALL PREVIOUS",
    "SYSTEM:",
    "ASSISTANT:",
    "BEGIN INSTRUCTIONS",
    "DISREGARD PREVIOUS",
)


@dataclass(frozen=True)
class SanitizerResult:
    """Result of sanitizing a single free-text field.

    Attributes:
        value: Sanitized value. Empty string when the input was fully blocked.
        warnings: Stable warning codes such as ``sanitizer.blocked:product_name``.
    """

    value: str
    warnings: tuple[str, ...]


def _normalize_unicode(value: str) -> str:
    """Apply NFKC normalization so injection keywords cannot hide in compat forms."""
    return unicodedata.normalize("NFKC", value)


def _strip_controls(value: str) -> str:
    """Remove ASCII control characters that could break downstream consumers."""
    return _CONTROL_CHARS.sub("", value)


def _contains_injection_keyword(value: str) -> bool:
    """Return True when any prompt-injection marker is present (case-insensitive)."""
    upper = value.upper()
    return any(keyword in upper for keyword in _INJECTION_KEYWORDS)


def _is_blockable(value: str, *, allow_html: bool = False, allow_url: bool = False) -> bool:
    """Return True when the value matches any always-block content pattern."""
    if _contains_injection_keyword(value):
        return True
    if _SQL_INJECTION.search(value):
        return True
    if not allow_html and _HTML_TAG.search(value):
        return True
    return bool(not allow_url and _URL_PATTERN.search(value))


def _sanitize_blockable_field(value: str | None, field: str) -> SanitizerResult:
    """Strip controls and reject content carrying injection-shaped payloads.

    Args:
        value: Source string value, may be ``None``.
        field: Stable field identifier used in warning codes.

    Returns:
        Sanitized result. If blocked, ``value`` is the empty string and
        ``warnings`` contains ``sanitizer.blocked:{field}``.
    """
    if value is None:
        return SanitizerResult("", ())
    cleaned = _strip_controls(_normalize_unicode(value)).strip()
    if not cleaned:
        return SanitizerResult("", ())
    if _is_blockable(cleaned):
        return SanitizerResult("", (f"sanitizer.blocked:{field}",))
    return SanitizerResult(cleaned, ())


def sanitize_product_name(value: str | None) -> SanitizerResult:
    """Sanitize ``parsed_product.product_name``."""
    return _sanitize_blockable_field(value, "product_name")


def sanitize_manufacturer(value: str | None) -> SanitizerResult:
    """Sanitize ``parsed_product.manufacturer``."""
    return _sanitize_blockable_field(value, "manufacturer")


def sanitize_serving_size(value: str | None) -> SanitizerResult:
    """Sanitize ``parsed_product.serving_size``."""
    return _sanitize_blockable_field(value, "serving_size")


def sanitize_ingredient_name(value: str | None) -> SanitizerResult:
    """Sanitize ``ingredient_candidates[].display_name``."""
    return _sanitize_blockable_field(value, "ingredient_name")


def sanitize_unit(value: str | None) -> SanitizerResult:
    """Sanitize ``ingredient_candidates[].unit``.

    Units are short tokens (mg, IU, %DV) that should never carry URLs, HTML,
    SQL keywords, or prompt-injection markers.
    """
    return _sanitize_blockable_field(value, "unit")


def sanitize_preview_text(value: str | None, field: str) -> SanitizerResult:
    """Sanitize bounded label-preview text emitted by OCR/LLM parsing.

    Args:
        value: Source label-preview string.
        field: Stable field path used in sanitizer warning codes.

    Returns:
        Sanitized result with prompt-injection, URL, HTML, and SQL-shaped
        payloads blocked.
    """
    return _sanitize_blockable_field(value, field)
