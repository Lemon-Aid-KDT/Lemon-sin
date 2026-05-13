"""Supplement image analysis orchestration service.

This service keeps the existing intake flow intact while creating a stable place
to plug in OCR, vision ROI detection, and future learning pipelines. Default
runtime behavior remains intake-only unless adapters are explicitly provided.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models.db.supplement import SupplementAnalysisRun
from src.ocr.base import OCRAdapter, OCRImageInput, OCRResult
from src.security.auth import AuthenticatedUser
from src.services.supplement_intake import (
    SupplementIntakeStoreResult,
    ValidatedSupplementImage,
    create_supplement_analysis_intake,
    read_and_validate_supplement_image,
)
from src.services.supplement_parser import (
    OCR_LOW_CONFIDENCE_THRESHOLD,
    SupplementOCRTextParser,
    parse_supplement_analysis_ocr_text,
)
from src.vision.base import BoundingBox, VisionAdapter, VisionError


class SupplementImageAnalysisConfigurationError(RuntimeError):
    """Raised when a feature flag is enabled without the required adapter."""


@dataclass(frozen=True)
class SupplementImageAnalysisAdapters:
    """Optional adapters used by the image analysis pipeline.

    Attributes:
        ocr: OCR adapter. When absent, the pipeline remains intake-only.
        parser: Structured OCR text parser, primarily injected by tests.
        vision: Label-region detector. Used only when ``enable_vision_classifier`` is true.
        multimodal_ocr: Local vision LLM assist adapter used only as OCR fallback.
    """

    ocr: OCRAdapter | None = None
    parser: SupplementOCRTextParser | None = None
    vision: VisionAdapter | None = None
    multimodal_ocr: OCRAdapter | None = None


@dataclass(frozen=True)
class SupplementImageAnalysisResult:
    """Result returned by the image analysis orchestration service.

    Attributes:
        record: Persisted supplement analysis preview.
        reused_existing: Whether idempotency returned an existing preview.
        image_metadata: Validated image metadata.
        vision_region: Optional label-region ROI used by OCR.
        ocr_result: Optional OCR output used by the parser.
        parser_used: Whether structured OCR text parsing was invoked.
    """

    record: SupplementAnalysisRun
    reused_existing: bool
    image_metadata: ValidatedSupplementImage
    vision_region: BoundingBox | None
    ocr_result: OCRResult | None
    parser_used: bool


async def analyze_supplement_image(
    session: AsyncSession,
    user: AuthenticatedUser,
    image: UploadFile,
    client_request_id: str | None,
    settings: Settings,
    adapters: SupplementImageAnalysisAdapters | None = None,
) -> SupplementImageAnalysisResult:
    """Validate, persist, and optionally OCR/parse a supplement label image.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        image: Uploaded supplement label image.
        client_request_id: Optional client idempotency key.
        settings: Runtime settings.
        adapters: Optional OCR/parser/vision adapters. Missing adapters keep the flow
            intake-only unless a corresponding feature flag requires one.

    Returns:
        Image analysis result with the current preview record.

    Raises:
        SupplementImageAnalysisConfigurationError: If vision is enabled without an adapter.
        SupplementImageValidationError: If image validation fails.
        SupplementIntakeConflictError: If idempotency conflicts.
        SupplementParserInputError: If OCR text parsing input is invalid.
    """
    active_adapters = adapters or SupplementImageAnalysisAdapters()
    image_metadata = await read_and_validate_supplement_image(image, settings)
    intake = await create_supplement_analysis_intake(
        session=session,
        user=user,
        image_metadata=image_metadata,
        client_request_id=client_request_id,
        settings=settings,
    )

    image_bytes = await _read_validated_image_bytes_if_needed(
        image,
        active_adapters=active_adapters,
        settings=settings,
    )
    vision_region = await _detect_label_region_if_enabled(
        image_bytes=image_bytes,
        settings=settings,
        vision_adapter=active_adapters.vision,
    )
    ocr_result = await _extract_ocr_if_configured(
        image_bytes=image_bytes,
        image_metadata=image_metadata,
        label_region=vision_region,
        ocr_adapter=active_adapters.ocr,
    )
    ocr_result = await _extract_multimodal_ocr_if_allowed(
        image_bytes=image_bytes,
        image_metadata=image_metadata,
        label_region=vision_region,
        ocr_result=ocr_result,
        primary_ocr_attempted=active_adapters.ocr is not None,
        settings=settings,
        multimodal_adapter=active_adapters.multimodal_ocr,
    )
    parsed_record = await _parse_ocr_if_available(
        session=session,
        user=user,
        intake=intake,
        ocr_result=ocr_result,
        settings=settings,
        parser=active_adapters.parser,
    )

    return SupplementImageAnalysisResult(
        record=parsed_record or intake.record,
        reused_existing=intake.reused_existing,
        image_metadata=image_metadata,
        vision_region=vision_region,
        ocr_result=ocr_result,
        parser_used=parsed_record is not None,
    )


async def _read_validated_image_bytes_if_needed(
    image: UploadFile,
    *,
    active_adapters: SupplementImageAnalysisAdapters,
    settings: Settings,
) -> bytes | None:
    """Read image bytes for adapters only when an adapter path may execute.

    Args:
        image: Already validated upload file.
        active_adapters: Pipeline adapters requested for this call.
        settings: Runtime settings containing feature flags.

    Returns:
        Image bytes, or None when no adapter needs them.
    """
    needs_bytes = active_adapters.ocr is not None or settings.enable_vision_classifier
    needs_bytes = needs_bytes or (
        active_adapters.multimodal_ocr is not None and settings.enable_multimodal_llm
    )
    if not needs_bytes:
        return None
    await image.seek(0)
    return await image.read()


async def _detect_label_region_if_enabled(
    *,
    image_bytes: bytes | None,
    settings: Settings,
    vision_adapter: VisionAdapter | None,
) -> BoundingBox | None:
    """Run label-region detection only when the vision feature flag is enabled.

    Args:
        image_bytes: Validated image bytes, if loaded for adapter use.
        settings: Runtime settings.
        vision_adapter: Optional vision adapter.

    Returns:
        Detected label region, or None when disabled.

    Raises:
        SupplementImageAnalysisConfigurationError: If the flag is enabled without an adapter.
    """
    if not settings.enable_vision_classifier:
        return None
    if vision_adapter is None or image_bytes is None:
        raise SupplementImageAnalysisConfigurationError(
            "ENABLE_VISION_CLASSIFIER=true requires a VisionAdapter."
        )
    try:
        return await vision_adapter.detect_label_region(image_bytes)
    except VisionError:
        return None


async def _extract_ocr_if_configured(
    *,
    image_bytes: bytes | None,
    image_metadata: ValidatedSupplementImage,
    label_region: BoundingBox | None,
    ocr_adapter: OCRAdapter | None,
) -> OCRResult | None:
    """Run OCR only when an OCR adapter is injected.

    Args:
        image_bytes: Validated image bytes, if loaded for adapter use.
        image_metadata: Validated image metadata.
        label_region: Optional label-region ROI from the vision layer.
        ocr_adapter: Optional OCR adapter.

    Returns:
        OCR result, or None in intake-only mode.
    """
    if ocr_adapter is None or image_bytes is None:
        return None
    return await ocr_adapter.extract_text(
        OCRImageInput(
            image_bytes=image_bytes,
            mime_type=image_metadata.mime_type,
            width=image_metadata.width,
            height=image_metadata.height,
            label_region=label_region,
        )
    )


async def _extract_multimodal_ocr_if_allowed(
    *,
    image_bytes: bytes | None,
    image_metadata: ValidatedSupplementImage,
    label_region: BoundingBox | None,
    ocr_result: OCRResult | None,
    primary_ocr_attempted: bool,
    settings: Settings,
    multimodal_adapter: OCRAdapter | None,
) -> OCRResult | None:
    """Run local vision LLM candidate extraction only as an OCR fallback.

    Args:
        image_bytes: Validated image bytes, if loaded for adapter use.
        image_metadata: Validated image metadata.
        label_region: Optional YOLO ROI that may reduce the image sent to the model.
        ocr_result: Primary OCR result, if any.
        primary_ocr_attempted: Whether a primary OCR adapter was actually configured.
        settings: Runtime settings controlling fallback policy.
        multimodal_adapter: Optional local vision LLM adapter.

    Returns:
        Primary OCR result, fallback candidate result, or None.
    """
    if not primary_ocr_attempted:
        return ocr_result
    if ocr_result is not None and not _should_run_multimodal_fallback(ocr_result, settings):
        return ocr_result
    if not settings.enable_multimodal_llm or multimodal_adapter is None or image_bytes is None:
        return ocr_result
    return await multimodal_adapter.extract_text(
        OCRImageInput(
            image_bytes=image_bytes,
            mime_type=image_metadata.mime_type,
            width=image_metadata.width,
            height=image_metadata.height,
            label_region=label_region,
        )
    )


def _should_run_multimodal_fallback(ocr_result: OCRResult | None, settings: Settings) -> bool:
    """Determine whether OCR output is weak enough to call vision assist.

    Args:
        ocr_result: Primary OCR output, if any.
        settings: Runtime settings containing fallback policy.

    Returns:
        True only for configured OCR-empty or low-confidence fallback cases.
    """
    if settings.multimodal_ocr_assist_policy == "disabled":
        return False
    if ocr_result is None:
        return settings.multimodal_ocr_assist_policy in {"ocr_empty_only", "low_confidence"}
    if not ocr_result.text.strip():
        return settings.multimodal_ocr_assist_policy in {"ocr_empty_only", "low_confidence"}
    if settings.multimodal_ocr_assist_policy != "low_confidence":
        return False
    return _is_low_confidence(ocr_result.confidence)


def _is_low_confidence(confidence: float | None) -> bool:
    """Check whether OCR confidence should trigger vision assist review.

    Args:
        confidence: Provider-level confidence.

    Returns:
        True when confidence is present and below the parser low-confidence threshold.
    """
    if confidence is None:
        return False
    return Decimal(str(confidence)) < OCR_LOW_CONFIDENCE_THRESHOLD


async def _parse_ocr_if_available(
    *,
    session: AsyncSession,
    user: AuthenticatedUser,
    intake: SupplementIntakeStoreResult,
    ocr_result: OCRResult | None,
    settings: Settings,
    parser: SupplementOCRTextParser | None,
) -> SupplementAnalysisRun | None:
    """Parse OCR text only when OCR produced non-empty text.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        intake: Stored intake result.
        ocr_result: OCR result to parse.
        settings: Runtime settings.
        parser: Optional parser adapter.

    Returns:
        Updated analysis row when structured parsing was invoked, otherwise None.
    """
    if ocr_result is None or not ocr_result.text.strip():
        return None
    parsed = await parse_supplement_analysis_ocr_text(
        session=session,
        user=user,
        analysis_id=intake.record.id,
        ocr_text=ocr_result.text,
        ocr_provider=ocr_result.provider,
        ocr_confidence=ocr_result.confidence,
        settings=settings,
        parser=parser,
    )
    return parsed.record
