"""Supplement label image intake service."""

from __future__ import annotations

import hashlib
import warnings
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from io import BytesIO
from typing import Any

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.image_quality import ImageQualityReport
from src.models.schemas.supplement import (
    MatchedSupplementCandidate,
    SupplementAnalysisPreview,
    SupplementAnalysisStatus,
    SupplementBarcodeLookupResponse,
    SupplementIngredientCandidate,
    SupplementParsedProduct,
    SupplementPreviewEvidenceSpan,
    SupplementPreviewFunctionalClaim,
    SupplementPreviewIntakeMethod,
    SupplementPreviewLabelSection,
    SupplementPreviewPrecaution,
    SupplementPreviewStructuredIntakeMethod,
)
from src.models.schemas.supplement_snapshot import (
    SupplementParsedSnapshotV3,
    SupplementSnapshotEvidenceSpan,
    parse_supplement_snapshot,
)
from src.security.auth import AuthenticatedUser
from src.security.subjects import build_owner_subject
from src.services.supplement_image_risk_actions import build_supplement_image_risk_action

SUPPLEMENT_INTAKE_ALGORITHM_VERSION = "supplement-intake-v1.0.0"
SUPPLEMENT_INTAKE_PROVIDER = "intake-only"
SUPPLEMENT_INTAKE_WARNING = (
    "Image intake is complete. OCR and LLM extraction are pending and require user review."
)
ALLOWED_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
SUPPORTED_IMAGE_SAVE_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
READ_CHUNK_SIZE_BYTES = 64 * 1024
WEBP_HEADER_MIN_BYTES = 12
MOBILE_REVIEW_CONFIDENCE_THRESHOLD = 0.75


@dataclass(frozen=True)
class ValidatedSupplementImage:
    """Validated supplement label image metadata.

    Attributes:
        sha256: SHA-256 hex digest of the sanitized image bytes.
        mime_type: Detected and accepted image MIME type.
        size_bytes: Sanitized image size in bytes.
        width: Decoded image width in pixels.
        height: Decoded image height in pixels.
        image_bytes: Metadata-stripped image bytes retained request-locally for
            OCR, multimodal verification, and consent-gated learning paths.
    """

    sha256: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    image_bytes: bytes = field(repr=False)


@dataclass(frozen=True)
class SupplementIntakeStoreResult:
    """Stored supplement intake preview result.

    Attributes:
        record: Persisted or reused supplement analysis row.
        reused_existing: Whether the row was returned through idempotency.
    """

    record: SupplementAnalysisRun
    reused_existing: bool


class SupplementImageValidationError(ValueError):
    """Raised when an uploaded supplement image fails intake validation."""

    def __init__(self, *, code: str, message: str, status_code: int) -> None:
        """Initialize a safe validation error.

        Args:
            code: Stable API error code.
            message: Safe user-facing error message.
            status_code: HTTP status code to return from the route.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class SupplementIntakeConflictError(ValueError):
    """Raised when an idempotency key is reused for different image bytes."""


def detect_image_mime(data: bytes) -> str | None:
    """Detect supported image MIME type from magic bytes.

    Args:
        data: Beginning or full image bytes.

    Returns:
        Detected MIME type, or None when unsupported.
    """
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= WEBP_HEADER_MIN_BYTES and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


async def read_and_validate_supplement_image(
    image: UploadFile,
    settings: Settings,
) -> ValidatedSupplementImage:
    """Read, bound, hash, and validate a supplement label upload.

    Args:
        image: Uploaded supplement label image.
        settings: Runtime settings containing upload limits.

    Returns:
        Validated image metadata.

    Raises:
        SupplementImageValidationError: If the upload is empty, too large,
            unsupported, spoofed, or not a valid image.
    """
    data = await _read_limited_upload(image, settings.supplement_image_max_bytes)
    content_type = image.content_type
    detected_mime = detect_image_mime(data[:16])

    if not data:
        raise SupplementImageValidationError(
            code="invalid_image",
            message="Uploaded label image is empty.",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    if content_type not in ALLOWED_IMAGE_MIME_TYPES or detected_mime is None:
        raise SupplementImageValidationError(
            code="unsupported_media_type",
            message="Only JPEG, PNG, and WebP label images are accepted.",
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        )
    if content_type != detected_mime:
        raise SupplementImageValidationError(
            code="unsupported_media_type",
            message="Uploaded label image content does not match its declared media type.",
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        )

    sanitized_bytes, width, height = _sanitize_decodable_image(
        data,
        detected_mime,
        settings.supplement_image_max_pixels,
    )
    if len(sanitized_bytes) > settings.supplement_image_max_bytes:
        raise SupplementImageValidationError(
            code="payload_too_large",
            message="Uploaded label image exceeds the configured size limit after sanitization.",
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        )
    return ValidatedSupplementImage(
        sha256=hashlib.sha256(sanitized_bytes).hexdigest(),
        mime_type=detected_mime,
        size_bytes=len(sanitized_bytes),
        width=width,
        height=height,
        image_bytes=sanitized_bytes,
    )


def supplement_analysis_run_to_preview(record: SupplementAnalysisRun) -> SupplementAnalysisPreview:
    """Convert an intake preview ORM row to its API response model.

    Args:
        record: Persisted supplement analysis run.

    Returns:
        Supplement analysis preview response.
    """
    parsed_snapshot = _dict_or_empty(record.parsed_snapshot)
    snapshot_v3 = parse_supplement_snapshot(_structured_snapshot_payload(parsed_snapshot))
    match_snapshot = _dict_or_empty(record.match_snapshot)
    layout_context = snapshot_v3.layout_context
    image_quality_report = _image_quality_report(parsed_snapshot.get("image_quality_report"))
    barcode_lookup = _barcode_lookup_response(parsed_snapshot.get("barcode_lookup"))
    image_risk_action = build_supplement_image_risk_action(
        image_quality_report=image_quality_report,
        barcode_lookup=barcode_lookup,
        parsed_product_name=snapshot_v3.product.product_name,
    )
    return SupplementAnalysisPreview(
        analysis_id=record.id,
        status=SupplementAnalysisStatus(record.status),
        parsed_product=SupplementParsedProduct.model_validate(
            {
                "product_name": snapshot_v3.product.product_name,
                "manufacturer": snapshot_v3.product.manufacturer,
                "serving_size": snapshot_v3.serving.serving_size_text,
                "daily_servings": snapshot_v3.serving.daily_servings,
            }
        ),
        ingredient_candidates=[
            SupplementIngredientCandidate.model_validate(
                {
                    "display_name": item.display_name,
                    "nutrient_code": (
                        item.nutrient_code_candidates[0].nutrient_code
                        if item.nutrient_code_candidates
                        else None
                    ),
                    "amount": item.amount,
                    "unit": item.unit,
                    "confidence": item.confidence,
                    "source": item.source,
                }
            )
            for item in snapshot_v3.ingredients
        ],
        matched_product_candidates=[
            MatchedSupplementCandidate.model_validate(item)
            for item in _dict_items(match_snapshot.get("matched_product_candidates"))
        ],
        barcode_lookup=barcode_lookup,
        layout_available=bool(layout_context and layout_context.layout_available),
        layout_fallback_reason=layout_context.fallback_reason if layout_context else None,
        label_sections=_preview_label_sections(snapshot_v3),
        intake_method=_preview_intake_method(snapshot_v3),
        precautions=_preview_precautions(snapshot_v3),
        functional_claims=_preview_functional_claims(snapshot_v3),
        evidence_spans=_preview_evidence_spans(snapshot_v3),
        image_quality_report=image_quality_report,
        analysis_scope=image_risk_action.analysis_scope,
        action_required=image_risk_action.action_required,
        detected_product_regions=image_risk_action.detected_product_regions,
        selected_region_id=image_risk_action.selected_region_id,
        missing_required_sections=image_risk_action.missing_required_sections,
        image_role=image_risk_action.image_role,
        multi_image_group_id=image_risk_action.multi_image_group_id,
        source_type=image_risk_action.source_type,
        identity_conflict=image_risk_action.identity_conflict,
        low_confidence_fields=snapshot_v3.low_confidence_fields,
        warnings=list(_string_items(record.warnings)),
        algorithm_version=record.algorithm_version,
        source_manifest_version=record.source_manifest_version,
        expires_at=record.expires_at,
    )


def _image_quality_report(value: Any) -> ImageQualityReport | None:
    """Parse a redacted image-quality report from preview metadata.

    Args:
        value: Candidate parsed snapshot value.

    Returns:
        Image quality report, or None when absent/invalid.
    """
    if not isinstance(value, dict):
        return None
    try:
        return ImageQualityReport.model_validate(value)
    except ValidationError:
        return None


def _structured_snapshot_payload(parsed_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return parser-owned snapshot fields without operational preview metadata.

    Args:
        parsed_snapshot: Persisted preview snapshot.

    Returns:
        Snapshot payload suitable for schema validation.
    """
    snapshot_payload = dict(parsed_snapshot)
    snapshot_payload.pop("image_quality_report", None)
    snapshot_payload.pop("barcode_lookup", None)
    return snapshot_payload


def _preview_evidence_spans(
    snapshot: SupplementParsedSnapshotV3,
) -> list[SupplementPreviewEvidenceSpan]:
    """Build mobile-safe evidence spans from the parsed snapshot.

    Args:
        snapshot: Parsed snapshot normalized to V3.

    Returns:
        Short redacted evidence excerpts for preview UI.
    """
    return [
        SupplementPreviewEvidenceSpan(
            span_id=span.span_id,
            source_type=span.source_type,
            section_type=span.section_type,
            text_excerpt=span.text_excerpt,
            page_index=span.page_index,
            cell_ref=span.cell_ref,
            confidence=span.confidence,
        )
        for span in snapshot.evidence_spans
    ]


def _preview_label_sections(
    snapshot: SupplementParsedSnapshotV3,
) -> list[SupplementPreviewLabelSection]:
    """Build bounded mobile label-section summaries.

    Args:
        snapshot: Parsed snapshot normalized to V3.

    Returns:
        Label sections for mobile confirmation.
    """
    layout_context = snapshot.layout_context
    if layout_context is not None and layout_context.sections:
        return [
            SupplementPreviewLabelSection(
                section_id=section.section_id,
                section_type=section.section_type,
                heading_text=section.heading_text,
                text_bundle=section.text_bundle,
                confidence=section.confidence,
                requires_review=section.requires_review
                or section.section_id in layout_context.low_confidence_sections
                or _is_low_confidence(section.confidence),
                evidence_refs=section.evidence_refs,
            )
            for section in layout_context.sections
        ]

    evidence_by_id = _evidence_by_id(snapshot.evidence_spans)
    return [
        SupplementPreviewLabelSection(
            section_id=f"section-{index + 1:03d}",
            section_type=section.section_type,
            heading_text=section.heading_text,
            text_bundle=_evidence_text_bundle(section.evidence_refs, evidence_by_id),
            confidence=_average_evidence_confidence(section.evidence_refs, evidence_by_id),
            requires_review=_field_requires_review(
                f"label_sections.{index}",
                snapshot.low_confidence_fields,
            )
            or _refs_need_review(section.evidence_refs, evidence_by_id),
            evidence_refs=section.evidence_refs,
        )
        for index, section in enumerate(snapshot.label_sections)
    ]


def _preview_intake_method(snapshot: SupplementParsedSnapshotV3) -> SupplementPreviewIntakeMethod:
    """Build the mobile intake-method preview.

    Args:
        snapshot: Parsed snapshot normalized to V3.

    Returns:
        Intake method preview for mobile confirmation.
    """
    evidence_by_id = _evidence_by_id(snapshot.evidence_spans)
    intake = snapshot.intake_method
    return SupplementPreviewIntakeMethod(
        text=intake.text,
        structured=SupplementPreviewStructuredIntakeMethod(
            frequency=intake.structured.frequency,
            times_per_day=intake.structured.times_per_day,
            amount_per_time=intake.structured.amount_per_time,
            amount_unit=intake.structured.amount_unit,
            time_of_day=intake.structured.time_of_day,
            with_food=intake.structured.with_food,
        ),
        confidence=_average_evidence_confidence(intake.evidence_refs, evidence_by_id),
        requires_review=_field_requires_review("intake_method", snapshot.low_confidence_fields)
        or _refs_need_review(intake.evidence_refs, evidence_by_id),
        evidence_refs=intake.evidence_refs,
    )


def _preview_precautions(
    snapshot: SupplementParsedSnapshotV3,
) -> list[SupplementPreviewPrecaution]:
    """Build mobile-safe precaution previews.

    Args:
        snapshot: Parsed snapshot normalized to V3.

    Returns:
        Precaution rows for mobile review.
    """
    evidence_by_id = _evidence_by_id(snapshot.evidence_spans)
    return [
        SupplementPreviewPrecaution(
            text=precaution.text,
            category=precaution.category,
            severity=precaution.severity,
            confidence=_average_evidence_confidence(precaution.evidence_refs, evidence_by_id),
            requires_review=_field_requires_review(
                f"precautions.{index}",
                snapshot.low_confidence_fields,
            )
            or _refs_need_review(precaution.evidence_refs, evidence_by_id),
            evidence_refs=precaution.evidence_refs,
        )
        for index, precaution in enumerate(snapshot.precautions)
    ]


def _preview_functional_claims(
    snapshot: SupplementParsedSnapshotV3,
) -> list[SupplementPreviewFunctionalClaim]:
    """Build mobile-safe functional claim previews.

    Args:
        snapshot: Parsed snapshot normalized to V3.

    Returns:
        Functional claim rows for mobile review.
    """
    evidence_by_id = _evidence_by_id(snapshot.evidence_spans)
    return [
        SupplementPreviewFunctionalClaim(
            text=claim.text,
            claim_type=claim.claim_type,
            confidence=_average_evidence_confidence(claim.evidence_refs, evidence_by_id),
            requires_review=_field_requires_review(
                f"functional_claims.{index}",
                snapshot.low_confidence_fields,
            )
            or _refs_need_review(claim.evidence_refs, evidence_by_id),
            evidence_refs=claim.evidence_refs,
        )
        for index, claim in enumerate(snapshot.functional_claims)
    ]


def _evidence_by_id(
    spans: Iterable[SupplementSnapshotEvidenceSpan],
) -> dict[str, SupplementSnapshotEvidenceSpan]:
    """Index evidence spans by id.

    Args:
        spans: Snapshot evidence spans.

    Returns:
        Evidence span map keyed by span id.
    """
    return {span.span_id: span for span in spans}


def _average_evidence_confidence(
    refs: Iterable[str],
    evidence_by_id: dict[str, SupplementSnapshotEvidenceSpan],
) -> float | None:
    """Average non-null confidence values for evidence refs.

    Args:
        refs: Evidence ids.
        evidence_by_id: Evidence span map.

    Returns:
        Average confidence, or None when no confidence exists.
    """
    values = [
        span.confidence
        for ref in refs
        if (span := evidence_by_id.get(ref)) is not None and span.confidence is not None
    ]
    if not values:
        return None
    return sum(values) / len(values)


def _evidence_text_bundle(
    refs: Iterable[str],
    evidence_by_id: dict[str, SupplementSnapshotEvidenceSpan],
) -> str | None:
    """Join bounded evidence excerpts into a section text bundle.

    Args:
        refs: Evidence ids.
        evidence_by_id: Evidence span map.

    Returns:
        Bounded text bundle or None.
    """
    excerpts = [
        span.text_excerpt
        for ref in refs
        if (span := evidence_by_id.get(ref)) is not None and span.text_excerpt
    ]
    if not excerpts:
        return None
    return " / ".join(excerpts)[:2_000]


def _refs_need_review(
    refs: Iterable[str],
    evidence_by_id: dict[str, SupplementSnapshotEvidenceSpan],
) -> bool:
    """Return whether any referenced evidence is low confidence.

    Args:
        refs: Evidence ids.
        evidence_by_id: Evidence span map.

    Returns:
        True when any referenced confidence is below the mobile review threshold.
    """
    return any(
        _is_low_confidence(span.confidence)
        for ref in refs
        if (span := evidence_by_id.get(ref)) is not None
    )


def _field_requires_review(field_path: str, low_confidence_fields: Iterable[str]) -> bool:
    """Return whether a field path is covered by low-confidence metadata.

    Args:
        field_path: Field path to check.
        low_confidence_fields: Field paths from the snapshot.

    Returns:
        True when the field path requires review.
    """
    return any(
        field == field_path
        or field.startswith(f"{field_path}.")
        or field_path.startswith(f"{field}.")
        for field in low_confidence_fields
    )


def _is_low_confidence(confidence: float | None) -> bool:
    """Return whether a confidence value should be reviewed in mobile.

    Args:
        confidence: Optional confidence value.

    Returns:
        True when confidence is known and below the threshold.
    """
    return confidence is not None and confidence < MOBILE_REVIEW_CONFIDENCE_THRESHOLD


async def create_supplement_analysis_intake(
    session: AsyncSession,
    user: AuthenticatedUser,
    image_metadata: ValidatedSupplementImage,
    client_request_id: str | None,
    settings: Settings,
) -> SupplementIntakeStoreResult:
    """Persist an intake-only supplement analysis preview for the current owner.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        image_metadata: Validated image metadata.
        client_request_id: Optional client idempotency key.
        settings: Runtime settings containing preview TTL.

    Returns:
        Stored preview row and idempotency reuse flag.

    Raises:
        SupplementIntakeConflictError: If the idempotency key exists with a
            different image hash.
        ValueError: If owner identity cannot be persisted safely.
    """
    owner_subject = build_owner_subject(user)
    normalized_client_request_id = _normalize_client_request_id(client_request_id)
    record: SupplementAnalysisRun | None = None
    reused_existing = False

    try:
        if normalized_client_request_id is not None:
            record = await session.scalar(
                select(SupplementAnalysisRun).where(
                    SupplementAnalysisRun.owner_subject == owner_subject,
                    SupplementAnalysisRun.client_request_id == normalized_client_request_id,
                )
            )
            if record is not None:
                if record.image_sha256 != image_metadata.sha256:
                    raise SupplementIntakeConflictError(
                        "client_request_id has already been used for a different image."
                    )
                reused_existing = True

        if record is None:
            record = SupplementAnalysisRun(
                owner_subject=owner_subject,
                client_request_id=normalized_client_request_id,
                status=SupplementAnalysisStatus.REQUIRES_CONFIRMATION.value,
                image_sha256=image_metadata.sha256,
                image_mime_type=image_metadata.mime_type,
                image_size_bytes=image_metadata.size_bytes,
                ocr_provider=SUPPLEMENT_INTAKE_PROVIDER,
                ocr_confidence=None,
                ocr_text_hash=None,
                parsed_snapshot=_build_intake_parsed_snapshot(image_metadata),
                match_snapshot={"matched_product_candidates": []},
                warnings=[SUPPLEMENT_INTAKE_WARNING],
                algorithm_version=SUPPLEMENT_INTAKE_ALGORITHM_VERSION,
                source_manifest_version=None,
                expires_at=datetime.now(UTC)
                + timedelta(minutes=settings.supplement_preview_ttl_minutes),
            )
            session.add(record)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    if not reused_existing:
        await session.refresh(record)
    return SupplementIntakeStoreResult(record=record, reused_existing=reused_existing)


async def _read_limited_upload(image: UploadFile, max_bytes: int) -> bytes:
    """Read an uploaded file while enforcing a byte limit.

    Args:
        image: Uploaded file.
        max_bytes: Maximum accepted byte count.

    Returns:
        Uploaded bytes.

    Raises:
        SupplementImageValidationError: If the upload exceeds the size limit.
    """
    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await image.read(READ_CHUNK_SIZE_BYTES)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_bytes:
            raise SupplementImageValidationError(
                code="payload_too_large",
                message="Uploaded label image exceeds the configured size limit.",
                status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _sanitize_decodable_image(
    data: bytes, mime_type: str, max_pixels: int
) -> tuple[bytes, int, int]:
    """Decode, bound, and re-encode an image without client metadata.

    Args:
        data: Uploaded image bytes.
        mime_type: Detected MIME type used to choose the output encoder.
        max_pixels: Maximum accepted pixel count.

    Returns:
        Sanitized bytes, image width, and image height.

    Raises:
        SupplementImageValidationError: If the image is malformed or too large.
    """
    previous_max_pixels = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                _validate_image_dimensions(image.size, max_pixels)
                image.load()
                clean_image = ImageOps.exif_transpose(image)
                clean_image.info.clear()
                output = BytesIO()
                save_kwargs: dict[str, object] = {}
                if mime_type == "image/jpeg":
                    save_kwargs["quality"] = 95
                    if clean_image.mode not in {"RGB", "L", "CMYK"}:
                        clean_image = clean_image.convert("RGB")
                elif mime_type == "image/webp":
                    save_kwargs["lossless"] = True
                clean_image.save(
                    output, format=SUPPORTED_IMAGE_SAVE_FORMATS[mime_type], **save_kwargs
                )
                return output.getvalue(), clean_image.width, clean_image.height
    except SupplementImageValidationError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise SupplementImageValidationError(
            code="payload_too_large",
            message="Uploaded label image exceeds the configured pixel limit.",
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        ) from exc
    except (OSError, UnidentifiedImageError) as exc:
        raise SupplementImageValidationError(
            code="invalid_image",
            message="Uploaded label image cannot be decoded.",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        ) from exc
    finally:
        Image.MAX_IMAGE_PIXELS = previous_max_pixels


def _validate_image_dimensions(size: tuple[int, int], max_pixels: int) -> None:
    """Validate decoded dimensions before expensive downstream processing.

    Args:
        size: Pillow decoded image dimensions.
        max_pixels: Maximum accepted pixel count.

    Raises:
        SupplementImageValidationError: If the image dimensions are invalid or too large.
    """
    width, height = size
    if width <= 0 or height <= 0:
        raise SupplementImageValidationError(
            code="invalid_image",
            message="Uploaded label image has invalid dimensions.",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    if width * height > max_pixels:
        raise SupplementImageValidationError(
            code="payload_too_large",
            message="Uploaded label image exceeds the configured pixel limit.",
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        )


def _build_intake_parsed_snapshot(image_metadata: ValidatedSupplementImage) -> dict[str, Any]:
    """Build a bounded sanitized parsed snapshot for intake-only previews.

    Args:
        image_metadata: Validated image metadata.

    Returns:
        Parsed snapshot with no raw image bytes, filename, EXIF, or OCR text.
    """
    return {
        "parsed_product": {},
        "ingredient_candidates": [],
        "low_confidence_fields": ["label_text"],
        "intake": {
            "mime_type": image_metadata.mime_type,
            "size_bytes": image_metadata.size_bytes,
            "width": image_metadata.width,
            "height": image_metadata.height,
        },
    }


def _normalize_client_request_id(client_request_id: str | None) -> str | None:
    """Normalize an optional client idempotency key.

    Args:
        client_request_id: Raw client idempotency key.

    Returns:
        Trimmed idempotency key, or None when empty.
    """
    if client_request_id is None:
        return None
    normalized = client_request_id.strip()
    return normalized or None


def _dict_or_empty(value: Any) -> dict[str, Any]:
    """Return a dictionary when the value is a dictionary, otherwise empty.

    Args:
        value: Candidate value.

    Returns:
        Dictionary value or an empty dictionary.
    """
    if isinstance(value, dict):
        return value
    return {}


def _dict_items(value: Any) -> Iterable[dict[str, Any]]:
    """Yield dictionary items from a candidate list.

    Args:
        value: Candidate list value.

    Yields:
        Dictionary items only.
    """
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item


def _barcode_lookup_response(value: Any) -> SupplementBarcodeLookupResponse | None:
    """Return a barcode lookup response from a stored snapshot.

    Args:
        value: Stored barcode lookup snapshot.

    Returns:
        Parsed barcode lookup response, or None when absent/invalid.
    """

    if not isinstance(value, dict):
        return None
    return SupplementBarcodeLookupResponse.model_validate(value)


def _string_items(value: Any) -> Iterable[str]:
    """Yield string items from a candidate list.

    Args:
        value: Candidate list value.

    Yields:
        String items only.
    """
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                yield item
