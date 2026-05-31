"""Supplement OCR structured parsing service."""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.llm.ollama import SUPPLEMENT_PARSER_SOURCE, OllamaSupplementParser
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.label_layout import LabelLayout, LabelSection
from src.models.schemas.supplement import (
    SupplementAnalysisStatus,
    SupplementMissingRequiredSection,
    SupplementPreviewEvidenceSpan,
    SupplementPreviewLabelSection,
)
from src.models.schemas.supplement_parser import SupplementStructuredParseResult
from src.ocr.text_normalizer import normalize_ocr_text as normalize_provider_ocr_text
from src.security.auth import AuthenticatedUser
from src.security.subjects import build_owner_subject
from src.services.supplement_text_sanitizer import (
    sanitize_ingredient_name,
    sanitize_manufacturer,
    sanitize_preview_text,
    sanitize_product_name,
    sanitize_serving_size,
    sanitize_unit,
)

SUPPLEMENT_PARSER_CONFIRMATION_WARNING = (
    "Structured OCR parsing is a preview. Review and confirm every field before saving."
)
OCR_PATTERN_FALLBACK_WARNING = "ocr_pattern_fallback_requires_review"
OCR_PATTERN_FALLBACK_SOURCE = "ocr_pattern_fallback"
EXCIPIENT_FILTERED_WARNING = "ingredient.excipient_filtered"
INGREDIENT_AMOUNT_MISSING_WARNING = "ingredient.amount_missing"
SUPPLEMENT_IMAGE_ASSIST_WARNING = (
    "Image-assisted text extraction is a fallback preview. Review every field before saving."
)
SUPPLEMENT_PARSER_PROVIDER = "ollama"
OLLAMA_VISION_ASSIST_PROVIDER = "ollama_vision_assist"
OCR_PROVIDER_MAX_LENGTH = 64
OCR_LOW_CONFIDENCE_THRESHOLD = Decimal("0.80")
LAYOUT_TEXT_BUNDLE_MAX_CHARS = 2_000
LAYOUT_EVIDENCE_EXCERPT_MAX_CHARS = 240
LAYOUT_SECTION_TYPE_MAP = {
    "daily_intake": "intake_method",
    "nutrition_function_info": "supplement_facts",
    "intake_method": "intake_method",
    "precautions": "precautions",
    "ingredients": "ingredients",
    "functionality": "functional_info",
    "storage_method": "storage_method",
}
INGREDIENT_AMOUNT_PATTERN = re.compile(
    r"(?P<name>[A-Za-z가-힣][A-Za-z가-힣0-9\s()/+\-.,]{1,80}?)"
    r"\s*(?P<amount>\d+(?:[,.]\d+)?)\s*"
    r"(?P<unit>mg|g|mcg|μg|ug|㎍|iu|IU|%)\b"
    # Optional trailing %DV (영양성분기준치) after a real unit, e.g. "1000 mg 100%".
    r"(?:\s*(?P<dv>\d+(?:[,.]\d+)?)\s*%)?"
)
TRAILING_INGREDIENT_PUNCTUATION = " -_/.,:\uff1a|·•"
MAX_PATTERN_FALLBACK_INGREDIENTS = 20
INGREDIENT_MIN_NAME_CHARS = 2
INGREDIENT_MAX_NAME_CHARS = 80
PACKAGING_QUANTITY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^(?:g|mg|kg|ml|l)\s*(?:x\s*)?\d*\s*(?:포|정|캡슐|개입)?\s*\(?$",
        re.IGNORECASE,
    ),
    re.compile(r"^정\s*(?:x\s*)?\d*\s*(?:개입)?\s*\(?$", re.IGNORECASE),
    re.compile(r"^\d+\s*(?:정|포|캡슐|개입)\s*\(?$", re.IGNORECASE),
)
# Inactive excipients / capsule-coating materials that the LLM sometimes lists as
# ingredients. Matched by exact normalized name only (never substring) so genuine
# active nutrients are never dropped.
# Maintenance: extend when a new LLM model surfaces more excipient false-positives
# (e.g., additional Korean coating agents); keep entries exact-match, lowercase-normalized.
_EXCIPIENT_NAME_KEYS: frozenset[str] = frozenset(
    {
        "gelatin",
        "젤라틴",
        "glycerin",
        "glycerine",
        "글리세린",
        "purified water",
        "정제수",
        "softgel",
        "sunflower oil",
        "해바라기씨유",
        "soybean oil",
        "대두유",
        "silicon dioxide",
        "이산화규소",
        "magnesium stearate",
        "스테아린산마그네슘",
        "microcrystalline cellulose",
        "결정셀룰로스",
        "titanium dioxide",
        "이산화티타늄",
        "hydroxypropyl methylcellulose",
        "hpmc",
    }
)


class SupplementOCRTextParser(Protocol):
    """Protocol for parser adapters that convert OCR text into structured facts."""

    async def parse_supplement_ocr_text(
        self,
        ocr_text: str,
    ) -> SupplementStructuredParseResult:
        """Parse OCR text into a validated supplement structure.

        Args:
            ocr_text: Normalized OCR text.

        Returns:
            Structured supplement parse result.
        """


@dataclass(frozen=True)
class SupplementParserStoreResult:
    """Stored supplement parser result.

    Attributes:
        record: Updated supplement analysis row.
        parse_result: Validated structured parse output.
    """

    record: SupplementAnalysisRun
    parse_result: SupplementStructuredParseResult


class SupplementParserInputError(ValueError):
    """Raised when OCR text or OCR metadata fails parser input validation."""


class SupplementAnalysisNotFoundError(ValueError):
    """Raised when the current user cannot access the requested analysis row."""


class SupplementAnalysisExpiredError(ValueError):
    """Raised when the analysis preview has expired before parsing."""


class SupplementAnalysisStateError(ValueError):
    """Raised when the analysis preview is not in a parseable lifecycle state."""


class SupplementParserConflictError(ValueError):
    """Raised when a preview already has a different OCR text hash."""


async def parse_supplement_analysis_ocr_text(
    session: AsyncSession,
    user: AuthenticatedUser,
    analysis_id: UUID,
    ocr_text: str,
    ocr_provider: str,
    ocr_confidence: float | None,
    settings: Settings,
    ocr_layout: LabelLayout | None = None,
    parser: SupplementOCRTextParser | None = None,
) -> SupplementParserStoreResult:
    """Parse OCR text and store the structured preview on an owned analysis row.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        analysis_id: Supplement analysis preview identifier.
        ocr_text: Raw OCR text. It is normalized, hashed, sent only to local Ollama,
            and never stored as raw text.
        ocr_provider: OCR provider label.
        ocr_confidence: Optional OCR confidence from 0.0 to 1.0.
        settings: Runtime settings.
        ocr_layout: Optional deterministic layout parsed from provider OCR coordinates.
        parser: Optional parser adapter, primarily for tests.

    Returns:
        Updated analysis row and validated parse result.

    Raises:
        SupplementParserInputError: If OCR text, provider, or confidence is invalid.
        SupplementAnalysisNotFoundError: If the row is absent or belongs to another owner.
        SupplementAnalysisExpiredError: If the preview has expired.
        SupplementAnalysisStateError: If the row is already confirmed, failed, or expired.
        SupplementParserConflictError: If a different OCR text was already attached.
    """
    normalized_text = normalize_ocr_text(ocr_text, settings.supplement_ocr_text_max_chars)
    normalized_provider = _normalize_ocr_provider(ocr_provider)
    normalized_confidence = _normalize_confidence(ocr_confidence)
    text_hash = hash_ocr_text(normalized_text, settings.privacy_hash_secret)
    owner_subject = build_owner_subject(user)

    record = await session.scalar(
        select(SupplementAnalysisRun).where(
            SupplementAnalysisRun.id == analysis_id,
            SupplementAnalysisRun.owner_subject == owner_subject,
        )
    )
    if record is None:
        raise SupplementAnalysisNotFoundError("Supplement analysis preview was not found.")
    _validate_parseable_record(record, text_hash)

    active_parser = parser or OllamaSupplementParser(settings)
    parse_result = await active_parser.parse_supplement_ocr_text(normalized_text)
    _validate_parser_result(parse_result, settings.supplement_parser_max_ingredients)
    parse_result = _sanitize_parser_result(parse_result)
    parse_result = _merge_ocr_pattern_fallbacks(parse_result, normalized_text)
    _validate_parser_result(parse_result, settings.supplement_parser_max_ingredients)

    record.ocr_provider = normalized_provider
    record.ocr_confidence = normalized_confidence
    record.ocr_text_hash = text_hash
    record.parsed_snapshot = _build_parsed_snapshot(
        parse_result=parse_result,
        previous_snapshot=record.parsed_snapshot,
        ocr_confidence=normalized_confidence,
        ocr_provider=normalized_provider,
        ocr_layout=ocr_layout,
        settings=settings,
    )
    record.warnings = _build_warning_list(parse_result.warnings, normalized_provider)
    record.algorithm_version = settings.supplement_parser_algorithm_version
    record.status = SupplementAnalysisStatus.REQUIRES_CONFIRMATION.value

    await session.commit()
    await session.refresh(record)
    return SupplementParserStoreResult(record=record, parse_result=parse_result)


def normalize_ocr_text(ocr_text: str, max_chars: int) -> str:
    """Normalize OCR text before hashing and structured parsing.

    Args:
        ocr_text: Raw OCR text.
        max_chars: Maximum accepted character count.

    Returns:
        Normalized OCR text.

    Raises:
        SupplementParserInputError: If the OCR text is blank or too long.
    """
    normalized = "\n".join(
        line.rstrip() for line in ocr_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ).strip()
    normalized = normalize_provider_ocr_text(normalized)
    if not normalized:
        raise SupplementParserInputError("OCR text is empty.")
    if len(normalized) > max_chars:
        raise SupplementParserInputError("OCR text exceeds the configured parser limit.")
    return normalized


def hash_ocr_text(ocr_text: str, privacy_hash_secret: SecretStr) -> str:
    """Build a privacy-preserving HMAC-SHA256 fingerprint for OCR text.

    Args:
        ocr_text: Normalized OCR text.
        privacy_hash_secret: Application HMAC secret.

    Returns:
        Hex-encoded HMAC-SHA256 OCR text fingerprint.
    """
    secret = privacy_hash_secret.get_secret_value().encode("utf-8")
    return hmac.new(secret, ocr_text.encode("utf-8"), hashlib.sha256).hexdigest()


def _validate_parseable_record(record: SupplementAnalysisRun, ocr_text_hash: str) -> None:
    """Validate a preview row before parsing updates are applied.

    Args:
        record: Existing supplement analysis row.
        ocr_text_hash: HMAC fingerprint of the incoming OCR text.

    Raises:
        SupplementAnalysisExpiredError: If the preview TTL has elapsed.
        SupplementAnalysisStateError: If the row cannot be parsed in its current state.
        SupplementParserConflictError: If a different OCR text hash is already present.
    """
    if record.expires_at <= datetime.now(UTC):
        raise SupplementAnalysisExpiredError("Supplement analysis preview has expired.")
    if record.status != SupplementAnalysisStatus.REQUIRES_CONFIRMATION.value:
        raise SupplementAnalysisStateError("Supplement analysis preview is not parseable.")
    if record.ocr_text_hash is not None and record.ocr_text_hash != ocr_text_hash:
        raise SupplementParserConflictError("Supplement analysis preview already has OCR text.")


def _validate_parser_result(
    parse_result: SupplementStructuredParseResult,
    max_ingredients: int,
) -> None:
    """Validate runtime parser bounds not expressed by static JSON schema settings.

    Args:
        parse_result: Validated structured parser result.
        max_ingredients: Runtime maximum ingredient candidates.

    Raises:
        SupplementParserInputError: If the parser result exceeds runtime bounds.
    """
    if len(parse_result.ingredient_candidates) > max_ingredients:
        raise SupplementParserInputError("Parser returned too many ingredient candidates.")


def _sanitize_parser_result(
    parse_result: SupplementStructuredParseResult,
) -> SupplementStructuredParseResult:
    """Strip injection / SQL / HTML / URL payloads from free-text parser fields.

    Blocked product/manufacturer/serving fields collapse to ``None`` so the
    Pydantic schema remains satisfied. Ingredient candidates whose
    ``display_name`` would be blocked are dropped entirely because the schema
    requires a non-empty name. Sanitizer warning codes are merged into the
    returned ``warnings`` list so downstream callers and audit logs see them.

    Args:
        parse_result: Result returned by the LLM parser after schema validation.

    Returns:
        A new ``SupplementStructuredParseResult`` with sanitized free-text fields
        and any ``sanitizer.blocked:*`` warning codes appended.
    """
    snapshot = parse_result.model_dump()
    warnings: list[str] = list(snapshot.get("warnings", []))

    product = snapshot.get("parsed_product") or {}
    name_result = sanitize_product_name(product.get("product_name"))
    product["product_name"] = name_result.value or None
    warnings.extend(name_result.warnings)

    manufacturer_result = sanitize_manufacturer(product.get("manufacturer"))
    product["manufacturer"] = manufacturer_result.value or None
    warnings.extend(manufacturer_result.warnings)

    serving_result = sanitize_serving_size(product.get("serving_size"))
    product["serving_size"] = serving_result.value or None
    warnings.extend(serving_result.warnings)
    snapshot["parsed_product"] = product

    surviving_ingredients: list[dict[str, Any]] = []
    amount_missing = False
    for candidate in snapshot.get("ingredient_candidates", []):
        name_res = sanitize_ingredient_name(candidate.get("display_name"))
        if not name_res.value:
            warnings.extend(name_res.warnings)
            continue
        # Drop inactive excipients (gelatin, glycerin, purified water, ...) the
        # LLM sometimes emits as ingredients; they are not nutrient content.
        if _is_excipient_name(name_res.value):
            warnings.append(EXCIPIENT_FILTERED_WARNING)
            continue
        unit_res = sanitize_unit(candidate.get("unit"))
        candidate["display_name"] = name_res.value
        candidate["unit"] = unit_res.value or None
        warnings.extend(unit_res.warnings)
        if candidate.get("amount") is None:
            amount_missing = True
        surviving_ingredients.append(candidate)
    # Flag (do not drop) name-only candidates so reviewers see missing 함량/단위.
    if amount_missing:
        warnings.append(INGREDIENT_AMOUNT_MISSING_WARNING)
    snapshot["ingredient_candidates"] = surviving_ingredients
    snapshot = _sanitize_preview_fields(snapshot, warnings)

    deduped: list[str] = []
    seen: set[str] = set()
    for warning in warnings:
        if warning and warning not in seen:
            deduped.append(warning)
            seen.add(warning)
    snapshot["warnings"] = deduped

    return SupplementStructuredParseResult.model_validate(snapshot)


def _sanitize_preview_fields(snapshot: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    """Sanitize V3 review fields without exposing raw OCR or model payloads.

    Args:
        snapshot: Parser result dump being prepared for storage.
        warnings: Mutable warning list to receive sanitizer codes.

    Returns:
        Snapshot with unsafe review fields removed or normalized.
    """
    for section in snapshot.get("label_sections", []):
        if not isinstance(section, dict):
            continue
        _sanitize_optional_text_field(
            section, "heading_text", "label_section.heading_text", warnings
        )
        _sanitize_optional_text_field(section, "text_bundle", "label_section.text_bundle", warnings)

    intake_method = snapshot.get("intake_method")
    if isinstance(intake_method, dict):
        _sanitize_optional_text_field(intake_method, "text", "intake_method.text", warnings)

    _sanitize_required_text_items(
        snapshot.get("precautions"),
        field_key="text",
        warning_field="precaution.text",
        warnings=warnings,
    )
    _sanitize_required_text_items(
        snapshot.get("functional_claims"),
        field_key="text",
        warning_field="functional_claim.text",
        warnings=warnings,
    )
    _sanitize_required_text_items(
        snapshot.get("evidence_spans"),
        field_key="text_excerpt",
        warning_field="evidence_span.text_excerpt",
        warnings=warnings,
    )
    return snapshot


def _sanitize_optional_text_field(
    target: dict[str, Any],
    key: str,
    warning_field: str,
    warnings: list[str],
) -> None:
    """Sanitize an optional text field in place.

    Args:
        target: Mutable parser output object.
        key: Field name to sanitize.
        warning_field: Stable warning field name.
        warnings: Mutable warning list.
    """
    result = sanitize_preview_text(target.get(key), warning_field)
    warnings.extend(result.warnings)
    target[key] = result.value or None


def _sanitize_required_text_items(
    items: Any,
    *,
    field_key: str,
    warning_field: str,
    warnings: list[str],
) -> None:
    """Sanitize required text fields and drop unsafe items in place.

    Args:
        items: Candidate parser-output list.
        field_key: Required text field inside each list item.
        warning_field: Stable warning field name.
        warnings: Mutable warning list.
    """
    if not isinstance(items, list):
        return
    surviving: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result = sanitize_preview_text(item.get(field_key), warning_field)
        warnings.extend(result.warnings)
        if not result.value:
            continue
        item[field_key] = result.value
        surviving.append(item)
    items[:] = surviving


def _merge_ocr_pattern_fallbacks(
    parse_result: SupplementStructuredParseResult,
    ocr_text: str,
) -> SupplementStructuredParseResult:
    """Enrich missing amounts and add explicit OCR amount-pattern candidates.

    The fallback is intentionally narrow: it only converts visible
    ``name + amount + unit`` text into review-required ingredient candidates.
    It does not infer ingredients from product names, package counts, or section
    headings, and it still stores no raw OCR text.

    Args:
        parse_result: Sanitized LLM parser output.
        ocr_text: Normalized OCR text held only in request memory.

    Returns:
        Parser result with bounded fallback candidates merged in.
    """
    fallback_candidates = _extract_ocr_pattern_ingredient_candidates(ocr_text)
    if not fallback_candidates:
        return parse_result

    snapshot = parse_result.model_dump()
    existing_candidates = _list_of_mappings(snapshot.get("ingredient_candidates"))

    # 1) Enrich existing name-only candidates (amount is None) with an amount/unit
    #    from a name-matched OCR amount pattern, instead of adding a duplicate row.
    fallback_by_name: dict[str, dict[str, Any]] = {}
    for candidate in fallback_candidates:
        name_key = _ingredient_name_key(str(candidate.get("display_name") or ""))
        if name_key and name_key not in fallback_by_name:
            fallback_by_name[name_key] = candidate
    enriched = False
    for candidate in existing_candidates:
        if candidate.get("amount") is not None:
            continue
        match = fallback_by_name.get(
            _ingredient_name_key(str(candidate.get("display_name") or ""))
        )
        if match is None:
            continue
        candidate["amount"] = match.get("amount")
        if not candidate.get("unit"):
            candidate["unit"] = match.get("unit")
        if (
            candidate.get("daily_value_percent") is None
            and match.get("daily_value_percent") is not None
        ):
            candidate["daily_value_percent"] = match.get("daily_value_percent")
        enriched = True

    # 2) Add genuinely-new OCR amount-pattern candidates the LLM missed.
    existing_keys = {_ingredient_candidate_key(candidate) for candidate in existing_candidates}
    added = False
    for candidate in fallback_candidates:
        key = _ingredient_candidate_key(candidate)
        if key in existing_keys:
            continue
        existing_candidates.append(candidate)
        existing_keys.add(key)
        added = True
        if len(existing_candidates) >= MAX_PATTERN_FALLBACK_INGREDIENTS:
            break

    if not enriched and not added:
        return parse_result

    snapshot["ingredient_candidates"] = existing_candidates
    snapshot["warnings"] = _append_unique_string(
        snapshot.get("warnings"),
        OCR_PATTERN_FALLBACK_WARNING,
    )
    snapshot["low_confidence_fields"] = _append_unique_string(
        snapshot.get("low_confidence_fields"),
        "ingredient_candidates",
    )
    return SupplementStructuredParseResult.model_validate(snapshot)


def _extract_ocr_pattern_ingredient_candidates(ocr_text: str) -> list[dict[str, Any]]:
    """Extract review-required ingredients from explicit OCR amount patterns.

    Args:
        ocr_text: Normalized OCR text held only in request memory.

    Returns:
        Bounded schema-shaped ingredient candidates.
    """
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, float, str]] = set()
    for line in _ocr_lines(ocr_text):
        for match in INGREDIENT_AMOUNT_PATTERN.finditer(line):
            name = _clean_ingredient_name(match.group("name"))
            if not name:
                continue
            # Excipients can also appear as "name + amount + unit" in OCR text;
            # keep the fallback path consistent with the LLM-path excipient filter.
            if _is_excipient_name(name):
                continue
            amount = _parse_ingredient_amount(match.group("amount"))
            unit = _normalize_ingredient_unit(match.group("unit"))
            dv_raw = match.group("dv")
            daily_value_percent = _parse_ingredient_amount(dv_raw) if dv_raw else None
            key = (_ingredient_name_key(name), amount, unit)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "display_name": name,
                    "nutrient_code": None,
                    "amount": amount,
                    "unit": unit,
                    "daily_value_percent": daily_value_percent,
                    "confidence": 0.55,
                    "source": OCR_PATTERN_FALLBACK_SOURCE,
                }
            )
            if len(candidates) >= MAX_PATTERN_FALLBACK_INGREDIENTS:
                return candidates
    return candidates


def _ocr_lines(ocr_text: str) -> list[str]:
    """Return bounded non-empty OCR lines.

    Args:
        ocr_text: OCR text held only in request memory.

    Returns:
        Non-empty lines capped for deterministic fallback work.
    """
    return [line.strip() for line in ocr_text.splitlines() if line.strip()][:300]


def _clean_ingredient_name(value: str) -> str:
    """Normalize a regex-captured ingredient name.

    Args:
        value: Ingredient prefix captured before an amount and unit.

    Returns:
        Cleaned ingredient name, or an empty string when the prefix is unsafe.
    """
    cleaned = re.sub(r"^[^A-Za-z가-힣]+", "", value)
    cleaned = _strip_ingredient_heading_prefix(cleaned)
    cleaned = re.sub(r"[:\uff1a|·•]+$", "", cleaned).strip(TRAILING_INGREDIENT_PUNCTUATION)
    cleaned = " ".join(cleaned.split())
    if not (INGREDIENT_MIN_NAME_CHARS <= len(cleaned) <= INGREDIENT_MAX_NAME_CHARS):
        return ""
    if _looks_like_non_ingredient_heading(cleaned):
        return ""
    if _looks_like_packaging_quantity_token(cleaned):
        return ""
    if not re.search(r"[A-Za-z가-힣]", cleaned):
        return ""
    return cleaned


def _strip_ingredient_heading_prefix(value: str) -> str:
    """Remove common Korean/English section prefixes from a candidate.

    Args:
        value: Candidate ingredient prefix.

    Returns:
        Candidate with non-ingredient section wording removed.
    """
    cleaned = value.strip()
    patterns = (
        r"^(?:nutrition facts|supplement facts)\s*[:\uff1a|·•-]*\s*",
        r"^(?:영양\s*정보|영양\s*기능\s*정보|기능\s*정보)\s*[:\uff1a|·•-]*\s*",
        r"^(?:원재료명|원료명)\s*(?:및\s*함량)?\s*[:\uff1a|·•-]*\s*",
        r"^(?:1일\s*)?(?:섭취량|섭취\s*방법)\s*[:\uff1a|·•-]*\s*",
    )
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def _looks_like_non_ingredient_heading(value: str) -> bool:
    """Return whether text is a generic label heading, not an ingredient.

    Args:
        value: Cleaned ingredient candidate.

    Returns:
        True when the candidate is likely a section or package descriptor.
    """
    normalized = _ingredient_name_key(value)
    heading_tokens = (
        "nutrition facts",
        "supplement facts",
        "영양 정보",
        "영양정보",
        "영양 기능 정보",
        "영양기능정보",
        "섭취 방법",
        "섭취방법",
        "주의 사항",
        "주의사항",
        "원재료명",
        "원료명",
        "기능 정보",
        "기능정보",
        "건강기능식품",
        "총 내용량",
        "내용량",
        "제조원",
        "보관",
        "유통기한",
    )
    return any(token in normalized for token in heading_tokens)


def _looks_like_packaging_quantity_token(value: str) -> bool:
    """Return whether a candidate is a package quantity fragment.

    Args:
        value: Cleaned ingredient candidate.

    Returns:
        True when the value is a bounded package/serving-count fragment.
    """
    normalized = _ingredient_name_key(value)
    if not normalized:
        return False
    return any(pattern.fullmatch(normalized) for pattern in PACKAGING_QUANTITY_PATTERNS)


def _parse_ingredient_amount(value: str) -> int | float:
    """Parse a visible numeric ingredient amount.

    Args:
        value: OCR amount text.

    Returns:
        Integer when exact, otherwise float.
    """
    numeric_value = float(value.replace(",", ""))
    return int(numeric_value) if numeric_value.is_integer() else numeric_value


def _normalize_ingredient_unit(value: str) -> str:
    """Normalize common OCR unit variants.

    Args:
        value: OCR unit text.

    Returns:
        Normalized unit string.
    """
    stripped = value.strip()
    if stripped in {"μg", "㎍"} or stripped.casefold() in {"mcg", "ug"}:
        return "ug"
    if stripped.casefold() == "iu":
        return "IU"
    return stripped.casefold() if stripped != "%" else "%"


def _ingredient_candidate_key(candidate: dict[str, Any]) -> tuple[str, float | None, str | None]:
    """Return a stable dedupe key for ingredient candidates."""
    amount = candidate.get("amount")
    normalized_amount = float(amount) if isinstance(amount, int | float) else None
    unit = candidate.get("unit")
    return (
        _ingredient_name_key(str(candidate.get("display_name") or "")),
        normalized_amount,
        str(unit).casefold() if unit is not None else None,
    )


def _ingredient_name_key(value: str) -> str:
    """Return a normalized ingredient name key for comparison."""
    return " ".join(value.casefold().split())


def _is_excipient_name(value: str) -> bool:
    """Return whether a sanitized ingredient name is a known inactive excipient.

    Args:
        value: Sanitized ingredient display name.

    Returns:
        True only on an exact normalized match against the excipient allowlist,
        so genuine active nutrients are never dropped.
    """
    return _ingredient_name_key(value) in _EXCIPIENT_NAME_KEYS


def _list_of_mappings(value: Any) -> list[dict[str, Any]]:
    """Return dict items from a parser snapshot value."""
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _append_unique_string(value: Any, item: str) -> list[str]:
    """Append a bounded string to a list-shaped parser field once.

    Args:
        value: Existing parser field.
        item: String to append.

    Returns:
        Deduplicated list.
    """
    items = [entry for entry in value if isinstance(entry, str)] if isinstance(value, list) else []
    if item not in items:
        items.append(item)
    return items


def _normalize_ocr_provider(ocr_provider: str) -> str:
    """Normalize and validate OCR provider metadata.

    Args:
        ocr_provider: Raw OCR provider label.

    Returns:
        Trimmed provider label.

    Raises:
        SupplementParserInputError: If the provider label is invalid.
    """
    normalized = ocr_provider.strip()
    if not normalized:
        raise SupplementParserInputError("OCR provider is required.")
    if len(normalized) > OCR_PROVIDER_MAX_LENGTH:
        raise SupplementParserInputError("OCR provider exceeds the storage limit.")
    return normalized


def _normalize_confidence(ocr_confidence: float | None) -> Decimal | None:
    """Validate OCR confidence and convert it for database storage.

    Args:
        ocr_confidence: Optional OCR confidence value.

    Returns:
        Decimal confidence or None.

    Raises:
        SupplementParserInputError: If confidence is outside 0.0 to 1.0.
    """
    if ocr_confidence is None:
        return None
    if ocr_confidence < 0 or ocr_confidence > 1:
        raise SupplementParserInputError("OCR confidence must be between 0 and 1.")
    return Decimal(str(ocr_confidence))


def _build_parsed_snapshot(
    *,
    parse_result: SupplementStructuredParseResult,
    previous_snapshot: dict[str, Any],
    ocr_confidence: Decimal | None,
    ocr_provider: str,
    ocr_layout: LabelLayout | None,
    settings: Settings,
) -> dict[str, Any]:
    """Build the sanitized JSON snapshot persisted for user confirmation.

    Args:
        parse_result: Validated structured parser result.
        previous_snapshot: Existing preview snapshot, used only to preserve intake metadata.
        ocr_confidence: Provider-level OCR confidence.
        ocr_provider: OCR-like provider that produced the parser input.
        ocr_layout: Optional deterministic layout parsed from OCR coordinates.
        settings: Runtime settings used for model and algorithm metadata.

    Returns:
        Sanitized parsed snapshot with no raw OCR text or model response.
    """
    low_confidence_fields = _build_low_confidence_fields(
        parse_result.low_confidence_fields,
        ocr_confidence,
    )
    layout_sections, layout_evidence_spans, layout_fallback_reason = _layout_context_to_preview(
        ocr_layout
    )
    label_sections = _merge_label_sections(parse_result.label_sections, layout_sections)
    evidence_spans = _merge_evidence_spans(parse_result.evidence_spans, layout_evidence_spans)
    missing_required_sections = _merge_missing_required_sections(
        parse_result.missing_required_sections,
        label_sections,
        intake_text=parse_result.intake_method.text,
    )
    snapshot: dict[str, Any] = {
        "parsed_product": parse_result.parsed_product.model_dump(exclude_none=True),
        "ingredient_candidates": [
            candidate.model_dump(exclude_none=True)
            for candidate in parse_result.ingredient_candidates
        ],
        "layout_available": bool(label_sections),
        "label_sections": [section.model_dump(exclude_none=True) for section in label_sections],
        "intake_method": parse_result.intake_method.model_dump(exclude_none=True),
        "precautions": [
            precaution.model_dump(exclude_none=True) for precaution in parse_result.precautions
        ],
        "functional_claims": [
            claim.model_dump(exclude_none=True) for claim in parse_result.functional_claims
        ],
        "evidence_spans": [span.model_dump(exclude_none=True) for span in evidence_spans],
        "missing_required_sections": missing_required_sections,
        "low_confidence_fields": low_confidence_fields,
        "parser_metadata": {
            "provider": SUPPLEMENT_PARSER_PROVIDER,
            "source": SUPPLEMENT_PARSER_SOURCE,
            "input_provider": ocr_provider,
            "model": settings.ollama_model,
            "algorithm_version": settings.supplement_parser_algorithm_version,
            "raw_ocr_text_stored": False,
            "raw_model_response_stored": False,
        },
    }
    if ocr_layout is not None:
        snapshot["parser_metadata"]["layout_provider"] = ocr_layout.provider
        snapshot["parser_metadata"]["layout_page_count"] = ocr_layout.page_count
        snapshot["parser_metadata"]["layout_warning_count"] = len(ocr_layout.warnings)
    if layout_fallback_reason is not None:
        snapshot["layout_fallback_reason"] = layout_fallback_reason
    intake = previous_snapshot.get("intake")
    if isinstance(intake, dict):
        snapshot["intake"] = intake
    return snapshot


def _layout_context_to_preview(
    ocr_layout: LabelLayout | None,
) -> tuple[list[SupplementPreviewLabelSection], list[SupplementPreviewEvidenceSpan], str | None]:
    """Convert deterministic OCR layout sections into bounded preview objects.

    Args:
        ocr_layout: Parsed provider-neutral label layout.

    Returns:
        Preview sections, evidence spans, and an optional fallback reason.
    """
    if ocr_layout is None:
        return [], [], None

    sections: list[SupplementPreviewLabelSection] = []
    evidence_spans: list[SupplementPreviewEvidenceSpan] = []
    for raw_index, section in enumerate(ocr_layout.sections, start=1):
        preview_type = LAYOUT_SECTION_TYPE_MAP.get(section.section_type)
        if preview_type is None:
            continue
        text_bundle = _section_text_bundle(section)
        sanitized_bundle = sanitize_preview_text(text_bundle, "layout_section.text_bundle").value
        if not sanitized_bundle:
            continue

        section_id = f"layout-section-{raw_index}"
        span_id = f"layout-span-{raw_index}"
        heading_text = sanitize_preview_text(
            section.anchor_text,
            "layout_section.heading_text",
        ).value
        confidence = _section_confidence(section)
        sections.append(
            SupplementPreviewLabelSection.model_validate(
                {
                    "section_id": section_id,
                    "section_type": preview_type,
                    "heading_text": heading_text,
                    "text_bundle": sanitized_bundle,
                    "confidence": confidence,
                    "requires_review": False,
                    "evidence_refs": [span_id],
                }
            )
        )
        evidence_excerpt = sanitize_preview_text(
            sanitized_bundle[:LAYOUT_EVIDENCE_EXCERPT_MAX_CHARS],
            "layout_section.evidence_excerpt",
        ).value
        if evidence_excerpt:
            evidence_spans.append(
                SupplementPreviewEvidenceSpan.model_validate(
                    {
                        "span_id": span_id,
                        "source_type": "ocr_layout",
                        "section_type": preview_type,
                        "text_excerpt": evidence_excerpt,
                        "page_index": _section_page_index(section),
                        "cell_ref": section_id,
                        "confidence": confidence,
                    }
                )
            )

    if sections:
        return sections, evidence_spans, None
    if ocr_layout.warnings:
        return [], [], ocr_layout.warnings[0]
    return [], [], None


def _section_text_bundle(section: LabelSection) -> str:
    """Build a bounded section text bundle from deterministic layout rows.

    Args:
        section: Parsed label section.

    Returns:
        Bounded section text assembled in visual row order.
    """
    rows: list[str] = []
    for row in section.rows:
        row_text = " | ".join(cell.text for cell in sorted(row, key=lambda item: item.column_index))
        if row_text.strip():
            rows.append(row_text.strip())
    return "\n".join(rows)[:LAYOUT_TEXT_BUNDLE_MAX_CHARS].strip()


def _section_page_index(section: LabelSection) -> int | None:
    """Return the first page index represented by a layout section."""
    if section.anchor_box is not None:
        return section.anchor_box.page_index
    for row in section.rows:
        if row:
            return row[0].bounding_box.page_index
    return None


def _section_confidence(section: LabelSection) -> float | None:
    """Return the average confidence across a deterministic layout section."""
    values = [
        cell.confidence for row in section.rows for cell in row if cell.confidence is not None
    ]
    if not values:
        return None
    return sum(values) / len(values)


def _merge_label_sections(
    parser_sections: list[SupplementPreviewLabelSection],
    layout_sections: list[SupplementPreviewLabelSection],
) -> list[SupplementPreviewLabelSection]:
    """Prefer deterministic layout sections and append non-duplicate parser sections."""
    if not layout_sections:
        return list(parser_sections)
    merged = list(layout_sections)
    seen_types = {section.section_type for section in merged}
    for section in parser_sections:
        if section.section_type in seen_types:
            continue
        merged.append(section)
        seen_types.add(section.section_type)
    return merged


def _merge_evidence_spans(
    parser_spans: list[SupplementPreviewEvidenceSpan],
    layout_spans: list[SupplementPreviewEvidenceSpan],
) -> list[SupplementPreviewEvidenceSpan]:
    """Merge parser and layout evidence by stable span id."""
    merged: list[SupplementPreviewEvidenceSpan] = []
    seen_ids: set[str] = set()
    for span in [*parser_spans, *layout_spans]:
        if span.span_id in seen_ids:
            continue
        merged.append(span)
        seen_ids.add(span.span_id)
    return merged


def _merge_missing_required_sections(
    parser_missing: list[SupplementMissingRequiredSection],
    label_sections: list[SupplementPreviewLabelSection],
    *,
    intake_text: str | None,
) -> list[SupplementMissingRequiredSection]:
    """Remove missing-section markers proven present by parser or layout evidence."""
    present_types = {section.section_type for section in label_sections}
    if intake_text and intake_text.strip():
        present_types.add("intake_method")

    normalized: list[SupplementMissingRequiredSection] = []
    seen: set[str] = set()
    for section in parser_missing:
        if _is_required_section_present(section, present_types):
            continue
        if section not in seen:
            normalized.append(section)
            seen.add(section)
    return normalized


def _is_required_section_present(
    section: SupplementMissingRequiredSection,
    present_types: set[str],
) -> bool:
    """Return whether a required section has supporting preview evidence."""
    if section == "supplement_facts":
        return bool({"supplement_facts", "nutrition_info", "ingredients"} & present_types)
    if section == "functional_info":
        return "functional_info" in present_types
    return section in present_types


def _build_low_confidence_fields(
    parser_fields: list[str],
    ocr_confidence: Decimal | None,
) -> list[str]:
    """Merge parser field warnings with OCR-level confidence review signals.

    Args:
        parser_fields: Field paths reported by the structured parser.
        ocr_confidence: Provider-level OCR confidence.

    Returns:
        Deduplicated field paths that require user review.
    """
    fields = list(parser_fields)
    if ocr_confidence is not None and ocr_confidence < OCR_LOW_CONFIDENCE_THRESHOLD:
        fields.append("ocr_text")

    normalized: list[str] = []
    seen: set[str] = set()
    for field in fields:
        stripped = field.strip()
        if not stripped or stripped in seen:
            continue
        normalized.append(stripped)
        seen.add(stripped)
    return normalized


def _build_warning_list(parser_warnings: list[str], ocr_provider: str) -> list[str]:
    """Merge parser warnings with the required user-confirmation warning.

    Args:
        parser_warnings: Safe parser-produced warning strings.
        ocr_provider: OCR-like provider that produced parser input.

    Returns:
        Deduplicated warning list.
    """
    warnings = [SUPPLEMENT_PARSER_CONFIRMATION_WARNING, *parser_warnings]
    if ocr_provider == OLLAMA_VISION_ASSIST_PROVIDER:
        warnings.append(SUPPLEMENT_IMAGE_ASSIST_WARNING)
    normalized: list[str] = []
    seen: set[str] = set()
    for warning in warnings:
        stripped = warning.strip()
        if not stripped or stripped in seen:
            continue
        normalized.append(stripped)
        seen.add(stripped)
    return normalized
