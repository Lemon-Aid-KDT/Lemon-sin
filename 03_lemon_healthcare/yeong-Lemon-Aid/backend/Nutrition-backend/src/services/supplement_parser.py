"""Supplement OCR structured parsing service."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.llm.ollama import OllamaSupplementParser
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.supplement import SupplementAnalysisStatus
from src.models.schemas.supplement_layout_context import SupplementLayoutContextV1
from src.models.schemas.supplement_parser import (
    StructuredParseResultLike,
    SupplementStructuredParseResultV2,
    coerce_supplement_structured_parse_result_v2,
)
from src.models.schemas.supplement_snapshot import (
    OCRSnapshotProvider,
    StructuredIntakeMethodV3,
    SupplementParsedSnapshotSourceV3,
    SupplementParsedSnapshotV3,
    SupplementSnapshotEvidenceSpan,
    SupplementSnapshotFunctionalClaimV3,
    SupplementSnapshotIngredientV3,
    SupplementSnapshotIntakeMethodV3,
    SupplementSnapshotLabelSectionV3,
    SupplementSnapshotPrecautionV3,
    SupplementSnapshotProductV3,
    SupplementSnapshotServingV3,
)
from src.security.auth import AuthenticatedUser
from src.security.subjects import build_owner_subject
from src.services.nutrient_code_matcher import (
    match_nutrient_code_candidates,
    normalize_nutrient_alias,
)
from src.services.parser_domain_correction import apply_parser_domain_corrections

SUPPLEMENT_PARSER_CONFIRMATION_WARNING = (
    "Structured OCR parsing is a preview. Review and confirm every field before saving."
)
SUPPLEMENT_IMAGE_ASSIST_WARNING = (
    "Image-assisted text extraction is a fallback preview. Review every field before saving."
)
OLLAMA_VISION_ASSIST_PROVIDER = "ollama_vision_assist"
OCR_PROVIDER_MAX_LENGTH = 64
SNAPSHOT_MAX_EVIDENCE_SPANS = 160
SNAPSHOT_MAX_LABEL_SECTIONS = 40


class SupplementOCRTextParser(Protocol):
    """Protocol for parser adapters that convert OCR text into structured facts."""

    async def parse_supplement_ocr_text(
        self,
        ocr_text: str,
    ) -> StructuredParseResultLike:
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
        parse_result: Validated expanded structured parse output.
    """

    record: SupplementAnalysisRun
    parse_result: SupplementStructuredParseResultV2


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
    parser: SupplementOCRTextParser | None = None,
    parser_input_text: str | None = None,
    layout_context: SupplementLayoutContextV1 | None = None,
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
        parser: Optional parser adapter, primarily for tests.
        parser_input_text: Optional sectioned parser input. The original OCR text
            remains the hash/conflict source of truth.
        layout_context: Optional bounded layout context derived from OCR coordinates.

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
    normalized_parser_text = (
        normalize_ocr_text(parser_input_text, settings.supplement_ocr_text_max_chars)
        if parser_input_text is not None
        else normalized_text
    )
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
    raw_parse_result = await active_parser.parse_supplement_ocr_text(normalized_parser_text)
    parse_result = coerce_supplement_structured_parse_result_v2(raw_parse_result)
    _validate_parser_result(parse_result, settings.supplement_parser_max_ingredients)

    record.ocr_provider = normalized_provider
    record.ocr_confidence = normalized_confidence
    record.ocr_text_hash = text_hash
    record.parsed_snapshot = _build_parsed_snapshot(
        parse_result=parse_result,
        analysis_id=analysis_id,
        ocr_confidence=normalized_confidence,
        ocr_provider=normalized_provider,
        settings=settings,
        layout_context=layout_context,
    )
    record.warnings = _build_warning_list(
        parse_result.warnings,
        normalized_provider,
        layout_warnings=layout_context.warnings if layout_context is not None else None,
    )
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
    parse_result: SupplementStructuredParseResultV2,
    max_ingredients: int,
) -> None:
    """Validate runtime parser bounds not expressed by static JSON schema settings.

    Args:
        parse_result: Validated structured parser result.
        max_ingredients: Runtime maximum ingredient candidates.

    Raises:
        SupplementParserInputError: If the parser result exceeds runtime bounds.
    """
    if len(parse_result.ingredients) > max_ingredients:
        raise SupplementParserInputError("Parser returned too many ingredient candidates.")


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
    parse_result: SupplementStructuredParseResultV2,
    analysis_id: UUID,
    ocr_confidence: Decimal | None,
    ocr_provider: str,
    settings: Settings,
    layout_context: SupplementLayoutContextV1 | None = None,
) -> dict[str, Any]:
    """Build the sanitized JSON snapshot persisted for user confirmation.

    Args:
        parse_result: Validated structured parser result.
        analysis_id: Supplement analysis preview identifier.
        ocr_confidence: Provider-level OCR confidence.
        ocr_provider: OCR-like provider that produced the parser input.
        settings: Runtime settings used for model and algorithm metadata.
        layout_context: Optional deterministic layout context.

    Returns:
        Sanitized parsed snapshot with no raw OCR text or model response.
    """
    low_confidence_fields = _build_low_confidence_fields(
        parse_result.low_confidence_fields,
        ocr_confidence,
        settings,
        layout_fields=layout_context.low_confidence_fields if layout_context is not None else None,
    )
    daily_servings = parse_result.serving.daily_servings
    domain_correction = apply_parser_domain_corrections(parse_result, settings)
    parser_evidence_spans = [
        SupplementSnapshotEvidenceSpan.model_validate(span.model_dump(exclude_none=True))
        for span in parse_result.evidence_spans
    ]
    layout_evidence_spans = _layout_context_evidence_spans(layout_context)
    evidence_spans = _merge_evidence_spans(parser_evidence_spans, layout_evidence_spans)
    included_span_ids = {span.span_id for span in evidence_spans}
    label_sections = _merge_label_sections(
        _layout_context_label_sections(layout_context, included_span_ids),
        [
            SupplementSnapshotLabelSectionV3(
                section_type=section.section_type,
                heading_text=section.heading_text,
                evidence_refs=[ref for ref in section.evidence_refs if ref in included_span_ids],
            )
            for section in parse_result.label_sections
        ],
    )
    snapshot_warnings = _merge_strings(
        [
            *(layout_context.warnings if layout_context is not None else []),
            *parse_result.warnings,
            *domain_correction.warnings,
        ]
    )
    snapshot = SupplementParsedSnapshotV3(
        source=SupplementParsedSnapshotSourceV3(
            analysis_id=analysis_id,
            ocr_provider=_normalize_snapshot_ocr_provider(ocr_provider),
            ocr_confidence=float(ocr_confidence) if ocr_confidence is not None else None,
            layout_available=bool(layout_context and layout_context.layout_available),
            raw_image_stored=False,
            raw_ocr_text_stored=False,
            raw_provider_payload_stored=False,
            raw_model_response_stored=False,
        ),
        layout_context=layout_context,
        product=SupplementSnapshotProductV3(
            product_name=parse_result.product.product_name,
            manufacturer=parse_result.product.manufacturer,
            evidence_refs=parse_result.product.evidence_refs,
        ),
        serving=SupplementSnapshotServingV3(
            serving_size_text=parse_result.serving.serving_size_text,
            serving_amount=parse_result.serving.serving_amount,
            serving_unit=parse_result.serving.serving_unit,
            daily_servings=daily_servings,
            total_amount=parse_result.serving.total_amount,
            total_unit=parse_result.serving.total_unit,
            evidence_refs=parse_result.serving.evidence_refs,
        ),
        ingredients=[
            SupplementSnapshotIngredientV3(
                display_name=ingredient.display_name,
                normalized_name=normalize_nutrient_alias(ingredient.display_name),
                amount=ingredient.amount,
                unit=domain_correction.unit_overrides_by_ingredient_index.get(
                    index,
                    ingredient.unit,
                ),
                amount_text=ingredient.amount_text,
                daily_amount=_calculate_daily_amount(ingredient.amount, daily_servings),
                daily_unit=(
                    domain_correction.unit_overrides_by_ingredient_index.get(
                        index,
                        ingredient.unit,
                    )
                    if daily_servings is not None
                    else None
                ),
                nutrient_code_candidates=match_nutrient_code_candidates(
                    ingredient.display_name,
                    domain_correction.alias_catalog_by_ingredient_index.get(index, ()),
                ),
                confidence=ingredient.confidence,
                source="ocr_llm_preview",
                evidence_refs=ingredient.evidence_refs,
            )
            for index, ingredient in enumerate(parse_result.ingredients)
        ],
        label_sections=label_sections,
        intake_method=SupplementSnapshotIntakeMethodV3(
            text=parse_result.intake_method.text,
            structured=StructuredIntakeMethodV3(
                frequency=parse_result.intake_method.structured.frequency,
                times_per_day=parse_result.intake_method.structured.times_per_day,
                amount_per_time=parse_result.intake_method.structured.amount_per_time,
                amount_unit=parse_result.intake_method.structured.amount_unit,
                time_of_day=parse_result.intake_method.structured.time_of_day,
                with_food=parse_result.intake_method.structured.with_food,
            ),
            evidence_refs=parse_result.intake_method.evidence_refs,
        ),
        precautions=[
            SupplementSnapshotPrecautionV3(
                text=precaution.text,
                category=precaution.category,
                severity=precaution.severity,
                evidence_refs=precaution.evidence_refs,
            )
            for precaution in parse_result.precautions
        ],
        functional_claims=[
            SupplementSnapshotFunctionalClaimV3(
                text=claim.text,
                claim_type=claim.claim_type,
                evidence_refs=claim.evidence_refs,
            )
            for claim in parse_result.functional_claims
        ],
        evidence_spans=evidence_spans,
        domain_correction_audit=list(domain_correction.audit_entries),
        low_confidence_fields=low_confidence_fields,
        warnings=snapshot_warnings,
    )
    return snapshot.model_dump(mode="json", exclude_none=True)


def _calculate_daily_amount(amount: float | None, daily_servings: float | None) -> float | None:
    """Calculate label-derived daily amount when both inputs are explicit.

    Args:
        amount: Amount per serving.
        daily_servings: Label-stated serving count per day.

    Returns:
        Daily amount candidate, or None when not computable.
    """
    if amount is None or daily_servings is None:
        return None
    return amount * daily_servings


def _normalize_snapshot_ocr_provider(ocr_provider: str) -> OCRSnapshotProvider:
    """Map runtime OCR provider labels into the bounded snapshot enum.

    Args:
        ocr_provider: Runtime OCR provider label.

    Returns:
        Snapshot OCR provider label.
    """
    if ocr_provider in {
        "google_vision_document",
        "clova_ocr",
        "paddleocr_local",
        "ollama_vision_assist",
        "manual",
        "intake-only",
        "noop",
        "none",
    }:
        return ocr_provider  # type: ignore[return-value]
    if ocr_provider.startswith("manual"):
        return "manual"
    return "none"


def _layout_context_evidence_spans(
    layout_context: SupplementLayoutContextV1 | None,
) -> list[SupplementSnapshotEvidenceSpan]:
    """Convert layout context cell evidence into persisted snapshot spans.

    Args:
        layout_context: Optional deterministic layout context.

    Returns:
        Snapshot evidence spans derived from layout cells.
    """
    if layout_context is None:
        return []
    return [
        SupplementSnapshotEvidenceSpan(
            span_id=span.span_id,
            source_type="label_layout",
            section_type=span.section_type,
            text_excerpt=span.text_excerpt,
            page_index=span.page_index,
            cell_ref=span.cell_ref,
            confidence=span.confidence,
        )
        for span in layout_context.evidence_spans
    ]


def _layout_context_label_sections(
    layout_context: SupplementLayoutContextV1 | None,
    included_span_ids: set[str],
) -> list[SupplementSnapshotLabelSectionV3]:
    """Convert layout context sections into persisted label sections.

    Args:
        layout_context: Optional deterministic layout context.
        included_span_ids: Evidence spans available in the final snapshot.

    Returns:
        Snapshot label sections derived from layout context.
    """
    if layout_context is None:
        return []
    return [
        SupplementSnapshotLabelSectionV3(
            section_type=section.section_type,
            heading_text=section.heading_text,
            evidence_refs=[ref for ref in section.evidence_refs if ref in included_span_ids],
        )
        for section in layout_context.sections
    ]


def _merge_evidence_spans(
    primary_spans: list[SupplementSnapshotEvidenceSpan],
    secondary_spans: list[SupplementSnapshotEvidenceSpan],
) -> list[SupplementSnapshotEvidenceSpan]:
    """Merge evidence spans without creating dangling parser references.

    Parser spans are primary because parser output validation already guarantees
    parser field refs point to them. Layout spans fill the remaining capacity.

    Args:
        primary_spans: Parser-produced evidence spans.
        secondary_spans: Layout-derived evidence spans.

    Returns:
        Deduplicated evidence spans within the snapshot bound.
    """
    merged: list[SupplementSnapshotEvidenceSpan] = []
    seen: set[str] = set()
    for span in [*primary_spans, *secondary_spans]:
        if span.span_id in seen:
            continue
        if len(merged) >= SNAPSHOT_MAX_EVIDENCE_SPANS:
            break
        merged.append(span)
        seen.add(span.span_id)
    return merged


def _merge_label_sections(
    primary_sections: list[SupplementSnapshotLabelSectionV3],
    secondary_sections: list[SupplementSnapshotLabelSectionV3],
) -> list[SupplementSnapshotLabelSectionV3]:
    """Merge label sections while preserving layout-derived evidence first.

    Args:
        primary_sections: Layout-derived label sections.
        secondary_sections: Parser-produced label sections.

    Returns:
        Deduplicated label sections within the snapshot bound.
    """
    merged: list[SupplementSnapshotLabelSectionV3] = []
    index_by_key: dict[tuple[str, str], int] = {}
    for section in [*primary_sections, *secondary_sections]:
        key = (section.section_type, section.heading_text or "")
        if key in index_by_key:
            existing = merged[index_by_key[key]]
            merged[index_by_key[key]] = SupplementSnapshotLabelSectionV3(
                section_type=existing.section_type,
                heading_text=existing.heading_text,
                evidence_refs=_merge_strings([*existing.evidence_refs, *section.evidence_refs]),
            )
            continue
        if len(merged) >= SNAPSHOT_MAX_LABEL_SECTIONS:
            break
        index_by_key[key] = len(merged)
        merged.append(section)
    return merged


def _build_low_confidence_fields(
    parser_fields: list[str],
    ocr_confidence: Decimal | None,
    settings: Settings,
    *,
    layout_fields: list[str] | None = None,
) -> list[str]:
    """Merge parser field warnings with OCR-level confidence review signals.

    Args:
        parser_fields: Field paths reported by the structured parser.
        ocr_confidence: Provider-level OCR confidence.
        settings: Runtime settings containing the OCR confidence threshold.
        layout_fields: Layout-derived field paths requiring user review.

    Returns:
        Deduplicated field paths that require user review.
    """
    fields = [*parser_fields, *(layout_fields or [])]
    threshold = Decimal(str(settings.ocr_confidence_threshold))
    if ocr_confidence is not None and ocr_confidence < threshold:
        fields.append("ocr_text")

    return _merge_strings(fields)


def _build_warning_list(
    parser_warnings: list[str],
    ocr_provider: str,
    *,
    layout_warnings: list[str] | None = None,
) -> list[str]:
    """Merge parser warnings with the required user-confirmation warning.

    Args:
        parser_warnings: Safe parser-produced warning strings.
        ocr_provider: OCR-like provider that produced parser input.
        layout_warnings: Optional layout-derived warnings.

    Returns:
        Deduplicated warning list.
    """
    warnings = [SUPPLEMENT_PARSER_CONFIRMATION_WARNING, *(layout_warnings or []), *parser_warnings]
    if ocr_provider == OLLAMA_VISION_ASSIST_PROVIDER:
        warnings.append(SUPPLEMENT_IMAGE_ASSIST_WARNING)
    return _merge_strings(warnings)


def _merge_strings(values: list[str]) -> list[str]:
    """Normalize and deduplicate strings while preserving first-seen order.

    Args:
        values: Candidate strings.

    Returns:
        Trimmed unique strings.
    """
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = value.strip()
        if not stripped or stripped in seen:
            continue
        normalized.append(stripped)
        seen.add(stripped)
    return normalized
