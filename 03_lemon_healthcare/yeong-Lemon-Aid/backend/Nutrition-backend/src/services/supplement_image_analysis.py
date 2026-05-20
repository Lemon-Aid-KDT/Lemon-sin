"""Supplement image analysis orchestration service.

This service keeps the existing intake flow intact while creating a stable place
to plug in OCR, vision ROI detection, and future learning pipelines. Default
runtime behavior remains intake-only unless adapters are explicitly provided.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher
from random import random
from typing import Literal

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.learning.consent_gate import evaluate_image_learning_gate
from src.learning.object_storage import LearningImageObjectStore
from src.learning.pipeline import maybe_store_learning_image_object
from src.llm.ollama import (
    OllamaClientError,
    OllamaConfigurationError,
    OllamaStructuredOutputError,
)
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.image_quality import ImageQualityReport, QualityIssue
from src.models.schemas.privacy import ConsentType
from src.ocr.base import OCRAdapter, OCRError, OCRImageInput, OCRResult
from src.security.auth import AuthenticatedUser
from src.services.supplement_image_quality import (
    ImageQualityAnalysisError,
    analyze_supplement_image_quality,
)
from src.services.supplement_intake import (
    SupplementIntakeStoreResult,
    ValidatedSupplementImage,
    create_supplement_analysis_intake,
    read_and_validate_supplement_image,
)
from src.services.supplement_layout_context import build_supplement_layout_context
from src.services.supplement_parser import (
    SupplementOCRTextParser,
    SupplementParserInputError,
    parse_supplement_analysis_ocr_text,
)
from src.vision.base import BoundingBox, VisionAdapter, VisionError
from src.vision.preprocessing import (
    VisionPreprocessingError,
    crop_image_to_bounding_box,
    select_best_label_region,
)

AUTOMATIC_OCR_UNAVAILABLE_WARNING = (
    "Automatic text extraction is unavailable. Continue by entering label details manually."
)
OCR_TEXT_EMPTY_WARNING = (
    "No readable label text was extracted. Continue by entering label details manually."
)
OCR_PARSE_PREVIEW_UNAVAILABLE_WARNING = (
    "Automatic text parsing is unavailable. Continue by reviewing or entering details manually."
)
OCR_ROI_CROP_UNAVAILABLE_WARNING = (
    "Label-region crop was unavailable. Automatic text extraction used the full image."
)
OCR_VERIFICATION_MISMATCH_WARNING = (
    "Automatic text verification found a mismatch. Review the extracted label details manually."
)
IMAGE_QUALITY_REVIEW_WARNING = (
    "Image quality may limit automatic text extraction. Review the label photo before confirming."
)
AUTOMATIC_OCR_UNAVAILABLE_CODE = "automatic_ocr_unavailable"
OCR_TEXT_EMPTY_CODE = "ocr_text_empty"
OCR_PARSE_PREVIEW_UNAVAILABLE_CODE = "ocr_parse_preview_unavailable"
OCR_ROI_CROP_UNAVAILABLE_CODE = "ocr_roi_crop_unavailable"
OCR_VERIFICATION_MISMATCH_CODE = "ocr_verification_mismatch"
IMAGE_QUALITY_WARNING_CODE_PREFIX = "image_quality"
OCR_PROVIDER_UNAVAILABLE_CODE_PREFIX = "ocr_provider_unavailable"
OCR_PROVIDER_EMPTY_CODE_PREFIX = "ocr_provider_empty"
OCR_PROVIDER_LOW_CONFIDENCE_CODE_PREFIX = "ocr_provider_low_confidence"
OCR_PROVIDER_UNAVAILABLE_WARNING = (
    "An OCR provider was unavailable. A fallback provider was tried when configured."
)
OCR_PROVIDER_EMPTY_WARNING = (
    "An OCR provider returned no readable label text. Review or enter details manually."
)
OCR_PROVIDER_LOW_CONFIDENCE_WARNING = (
    "An OCR provider returned low-confidence text. Review the extracted label details manually."
)
ROI_CROP_DEGRADE_REASON_CODES = frozenset(
    {"multi_product", "roi_not_found", "cover_only", "partial_table", "too_small_text"}
)
PARSER_RECOVERABLE_ERRORS = (
    SupplementParserInputError,
    OllamaClientError,
    OllamaConfigurationError,
    OllamaStructuredOutputError,
)
ProviderAttemptStatus = Literal["success", "empty_text", "low_confidence", "error"]
ProviderAttemptRole = Literal["primary", "fallback"]


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
        fallback_ocr_adapters: Optional secondary OCR fallback adapters.
    """

    ocr: OCRAdapter | None = None
    parser: SupplementOCRTextParser | None = None
    vision: VisionAdapter | None = None
    multimodal_ocr: OCRAdapter | None = None
    fallback_ocr_adapters: tuple[OCRAdapter, ...] = ()


@dataclass(frozen=True)
class SupplementImageAnalysisResult:
    """Result returned by the image analysis orchestration service.

    Attributes:
        record: Persisted supplement analysis preview.
        reused_existing: Whether idempotency returned an existing preview.
        image_metadata: Validated image metadata.
        vision_region: Optional label-region ROI used by OCR.
        image_quality_report: Optional deterministic quality report.
        ocr_result: Optional OCR output used by the parser.
        parser_used: Whether structured OCR text parsing was invoked.
        ocr_attempted: Whether a primary OCR adapter was configured and called.
        ocr_warning_codes: Recoverable OCR/parser warning codes added to the preview.
        learning_image_object_created: Whether a learning image object row was created or reused.
    """

    record: SupplementAnalysisRun
    reused_existing: bool
    image_metadata: ValidatedSupplementImage
    vision_region: BoundingBox | None
    image_quality_report: ImageQualityReport | None
    ocr_result: OCRResult | None
    parser_used: bool
    ocr_attempted: bool
    ocr_warning_codes: tuple[str, ...]
    learning_image_object_created: bool


@dataclass(frozen=True)
class _OCRExtractionResult:
    """Internal OCR extraction result with recoverable warning metadata."""

    ocr_result: OCRResult | None
    warning_code: str | None = None
    warning_message: str | None = None


@dataclass(frozen=True)
class _OCRProviderAttempt:
    """Sanitized request-local OCR provider attempt metadata."""

    provider: str
    role: ProviderAttemptRole
    status: ProviderAttemptStatus
    confidence: float | None = None
    warning_code: str | None = None
    warning_message: str | None = None


@dataclass(frozen=True)
class _OCRPipelineResult:
    """OCR provider-chain result with sanitized warning metadata."""

    selected_result: OCRResult | None
    providers_attempted: tuple[_OCRProviderAttempt, ...]
    warning_pairs: tuple[tuple[str | None, str | None], ...]


@dataclass(frozen=True)
class _VisionDetectionResult:
    """Sanitized ROI detector result used by quality analysis and OCR crop selection."""

    selected_region: BoundingBox | None
    detected_regions: tuple[BoundingBox, ...] = ()


async def analyze_supplement_image(
    session: AsyncSession,
    user: AuthenticatedUser,
    image: UploadFile,
    client_request_id: str | None,
    settings: Settings,
    adapters: SupplementImageAnalysisAdapters | None = None,
    learning_consents: tuple[ConsentType, ...] = (),
    learning_object_store: LearningImageObjectStore | None = None,
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
        learning_consents: Active learning consent grants. Used only for optional
            image retention.
        learning_object_store: Optional object storage adapter for retained learning images.

    Returns:
        Image analysis result with the current preview record.

    Raises:
        SupplementImageAnalysisConfigurationError: If vision is enabled without an adapter.
        SupplementImageValidationError: If image validation fails.
        SupplementIntakeConflictError: If idempotency conflicts.
        SupplementParserInputError: If manual parser validation fails outside recoverable OCR flow.
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

    learning_gate_allowed = evaluate_image_learning_gate(settings, learning_consents).allowed
    image_bytes = await _read_validated_image_bytes_if_needed(
        image_metadata,
        active_adapters=active_adapters,
        settings=settings,
        needs_learning_image_bytes=learning_gate_allowed,
    )
    vision_detection = await _detect_label_regions_if_enabled(
        image_bytes=image_bytes,
        settings=settings,
        vision_adapter=active_adapters.vision,
    )
    vision_region = vision_detection.selected_region
    image_quality_report = _analyze_quality_if_image_bytes_loaded(
        image_bytes=image_bytes,
        image_metadata=image_metadata,
        label_region=vision_region,
        detected_regions=vision_detection.detected_regions,
        roi_detection_enabled=settings.enable_vision_classifier,
    )
    ocr_pipeline = await _run_ocr_provider_chain(
        image_bytes=image_bytes,
        image_metadata=image_metadata,
        label_region=vision_region,
        image_quality_report=image_quality_report,
        primary_adapter=active_adapters.ocr,
        fallback_adapters=active_adapters.fallback_ocr_adapters,
        settings=settings,
    )
    ocr_result = ocr_pipeline.selected_result
    verification_warning_code, verification_warning_message = (
        await _verify_ocr_with_multimodal_if_allowed(
            image_bytes=image_bytes,
            image_metadata=image_metadata,
            label_region=vision_region,
            ocr_result=ocr_result,
            settings=settings,
            multimodal_adapter=active_adapters.multimodal_ocr,
        )
    )
    parsed_record, parse_warning_code, parse_warning_message = await _parse_ocr_if_available(
        session=session,
        user=user,
        intake=intake,
        ocr_result=ocr_result,
        settings=settings,
        parser=active_adapters.parser,
    )
    warning_pairs = [
        *_quality_warning_pairs(image_quality_report),
        *ocr_pipeline.warning_pairs,
        (verification_warning_code, verification_warning_message),
        (parse_warning_code, parse_warning_message),
    ]
    warning_codes = tuple(code for code, message in warning_pairs if code and message)
    warning_messages = [message for code, message in warning_pairs if code and message]
    active_record = parsed_record or intake.record
    if image_quality_report is not None:
        await _store_image_quality_report(session, active_record, image_quality_report)
    if warning_messages:
        await _store_preview_warnings(session, active_record, warning_messages)

    learning_object = None
    if learning_object_store is not None:
        learning_object = await maybe_store_learning_image_object(
            session=session,
            user=user,
            analysis=active_record,
            image_bytes=image_bytes,
            image_metadata=image_metadata,
            settings=settings,
            object_store=learning_object_store,
            granted_consents=learning_consents,
        )

    return SupplementImageAnalysisResult(
        record=active_record,
        reused_existing=intake.reused_existing,
        image_metadata=image_metadata,
        vision_region=vision_region,
        image_quality_report=image_quality_report,
        ocr_result=ocr_result,
        parser_used=parsed_record is not None,
        ocr_attempted=bool(ocr_pipeline.providers_attempted),
        ocr_warning_codes=warning_codes,
        learning_image_object_created=learning_object is not None,
    )


async def _read_validated_image_bytes_if_needed(
    image_metadata: ValidatedSupplementImage,
    *,
    active_adapters: SupplementImageAnalysisAdapters,
    settings: Settings,
    needs_learning_image_bytes: bool = False,
) -> bytes | None:
    """Read image bytes for adapters only when an adapter path may execute.

    Args:
        image_metadata: Already validated metadata carrying sanitized image bytes.
        active_adapters: Pipeline adapters requested for this call.
        settings: Runtime settings containing feature flags.
        needs_learning_image_bytes: Whether learning retention needs sanitized image bytes.

    Returns:
        Image bytes, or None when no adapter needs them.
    """
    needs_bytes = active_adapters.ocr is not None or settings.enable_vision_classifier
    needs_bytes = needs_bytes or bool(active_adapters.fallback_ocr_adapters)
    needs_bytes = needs_bytes or needs_learning_image_bytes
    needs_bytes = needs_bytes or (
        active_adapters.multimodal_ocr is not None and settings.enable_multimodal_llm
    )
    if not needs_bytes:
        return None
    return image_metadata.image_bytes


async def _detect_label_regions_if_enabled(
    *,
    image_bytes: bytes | None,
    settings: Settings,
    vision_adapter: VisionAdapter | None,
) -> _VisionDetectionResult:
    """Run label-region detection only when the vision feature flag is enabled.

    Args:
        image_bytes: Validated image bytes, if loaded for adapter use.
        settings: Runtime settings.
        vision_adapter: Optional vision adapter.

    Returns:
        Selected ROI and candidate ROIs, or an empty result when disabled/fallback.

    Raises:
        SupplementImageAnalysisConfigurationError: If the flag is enabled without an adapter.
    """
    if not settings.enable_vision_classifier:
        return _VisionDetectionResult(selected_region=None)
    if vision_adapter is None or image_bytes is None:
        raise SupplementImageAnalysisConfigurationError(
            "ENABLE_VISION_CLASSIFIER=true requires a VisionAdapter."
        )
    try:
        detected_regions = tuple(await vision_adapter.detect_label_regions(image_bytes))
    except VisionError:
        return _VisionDetectionResult(selected_region=None)
    try:
        selected_region = select_best_label_region(list(detected_regions))
    except VisionPreprocessingError:
        selected_region = None
    return _VisionDetectionResult(
        selected_region=selected_region,
        detected_regions=detected_regions,
    )


def _analyze_quality_if_image_bytes_loaded(
    *,
    image_bytes: bytes | None,
    image_metadata: ValidatedSupplementImage,
    label_region: BoundingBox | None,
    detected_regions: tuple[BoundingBox, ...],
    roi_detection_enabled: bool,
) -> ImageQualityReport | None:
    """Analyze image quality only when image bytes are already needed by the pipeline.

    Args:
        image_bytes: Validated image bytes, if loaded for adapter or learning use.
        image_metadata: Validated image metadata.
        label_region: Optional selected ROI.
        detected_regions: Candidate ROI metadata.
        roi_detection_enabled: Whether ROI detection was configured for this request.

    Returns:
        Image quality report, or None when the pipeline did not need image bytes.
    """
    if image_bytes is None:
        return None
    try:
        return analyze_supplement_image_quality(
            image_bytes,
            image_width=image_metadata.width,
            image_height=image_metadata.height,
            label_region=label_region,
            detected_regions=detected_regions,
            roi_detection_enabled=roi_detection_enabled,
        )
    except ImageQualityAnalysisError:
        return ImageQualityReport(
            status="blocked",
            issues=[
                QualityIssue(
                    reason_code="unsupported_layout",
                    severity="blocked",
                    message="Image quality analysis could not decode the validated image.",
                    evidence={"decode_failed": True},
                )
            ],
            metrics={
                "image_width": image_metadata.width,
                "image_height": image_metadata.height,
            },
            retake_reasons=["unsupported_layout"],
        )


def _quality_warning_pairs(
    image_quality_report: ImageQualityReport | None,
) -> tuple[tuple[str | None, str | None], ...]:
    """Return safe warning pairs for quality issues.

    Args:
        image_quality_report: Optional deterministic quality report.

    Returns:
        Warning code and message pairs.
    """
    if image_quality_report is None or image_quality_report.status == "acceptable":
        return ()
    return tuple(
        (
            f"{IMAGE_QUALITY_WARNING_CODE_PREFIX}:{issue.reason_code}",
            IMAGE_QUALITY_REVIEW_WARNING,
        )
        for issue in image_quality_report.issues
    )


async def _extract_ocr_if_configured(
    *,
    image_bytes: bytes | None,
    image_metadata: ValidatedSupplementImage,
    label_region: BoundingBox | None,
    ocr_adapter: OCRAdapter | None,
    settings: Settings,
) -> _OCRExtractionResult:
    """Run OCR only when an OCR adapter is injected.

    Args:
        image_bytes: Validated image bytes, if loaded for adapter use.
        image_metadata: Validated image metadata.
        label_region: Optional label-region ROI from the vision layer.
        ocr_adapter: Optional OCR adapter.
        settings: Runtime settings controlling ROI preprocessing.

    Returns:
        OCR extraction result and optional recoverable warning metadata.
    """
    if ocr_adapter is None or image_bytes is None:
        return _OCRExtractionResult(ocr_result=None)
    ocr_input, warning_code, warning_message = _prepare_primary_ocr_image_input(
        image_bytes=image_bytes,
        image_metadata=image_metadata,
        label_region=label_region,
        settings=settings,
    )
    try:
        result = await ocr_adapter.extract_text(ocr_input)
    except OCRError:
        return _OCRExtractionResult(
            ocr_result=None,
            warning_code=AUTOMATIC_OCR_UNAVAILABLE_CODE,
            warning_message=AUTOMATIC_OCR_UNAVAILABLE_WARNING,
        )
    return _OCRExtractionResult(
        ocr_result=result,
        warning_code=warning_code,
        warning_message=warning_message,
    )


async def _run_ocr_provider_chain(
    *,
    image_bytes: bytes | None,
    image_metadata: ValidatedSupplementImage,
    label_region: BoundingBox | None,
    image_quality_report: ImageQualityReport | None,
    primary_adapter: OCRAdapter | None,
    fallback_adapters: tuple[OCRAdapter, ...],
    settings: Settings,
) -> _OCRPipelineResult:
    """Run primary and fallback OCR providers in deterministic order.

    Args:
        image_bytes: Validated image bytes, if loaded for adapter use.
        image_metadata: Validated image metadata.
        label_region: Optional detected label-region ROI.
        image_quality_report: Optional deterministic image quality report.
        primary_adapter: Optional primary OCR adapter.
        fallback_adapters: Secondary OCR providers in configured order.
        settings: Runtime settings controlling confidence and ROI policy.

    Returns:
        Selected OCR result, provider attempts, and safe warning metadata.
    """
    if primary_adapter is None and not fallback_adapters:
        return _OCRPipelineResult(
            selected_result=None,
            providers_attempted=(),
            warning_pairs=(),
        )
    if image_bytes is None:
        return _OCRPipelineResult(
            selected_result=None,
            providers_attempted=(),
            warning_pairs=((AUTOMATIC_OCR_UNAVAILABLE_CODE, AUTOMATIC_OCR_UNAVAILABLE_WARNING),),
        )

    attempts: list[_OCRProviderAttempt] = []
    warning_pairs: list[tuple[str | None, str | None]] = []
    selected_result: OCRResult | None = None

    if primary_adapter is not None:
        primary_input, warning_code, warning_message = _prepare_primary_ocr_image_input(
            image_bytes=image_bytes,
            image_metadata=image_metadata,
            label_region=label_region,
            image_quality_report=image_quality_report,
            settings=settings,
        )
        warning_pairs.append((warning_code, warning_message))
        attempt, candidate = await _try_ocr_provider(
            adapter=primary_adapter,
            image=primary_input,
            role="primary",
            index=0,
            settings=settings,
        )
        attempts.append(attempt)
        warning_pairs.append((attempt.warning_code, attempt.warning_message))
        selected_result = _select_ocr_candidate(selected_result, candidate)

    fallback_input = OCRImageInput(
        image_bytes=image_bytes,
        mime_type=image_metadata.mime_type,
        width=image_metadata.width,
        height=image_metadata.height,
        label_region=label_region,
    )
    for index, adapter in enumerate(fallback_adapters):
        if not _should_run_secondary_fallback(selected_result, settings):
            break
        attempt, candidate = await _try_ocr_provider(
            adapter=adapter,
            image=fallback_input,
            role="fallback",
            index=index,
            settings=settings,
        )
        attempts.append(attempt)
        warning_pairs.append((attempt.warning_code, attempt.warning_message))
        selected_result = _select_ocr_candidate(selected_result, candidate)

    if attempts and (selected_result is None or not selected_result.text.strip()):
        warning_pairs.append((AUTOMATIC_OCR_UNAVAILABLE_CODE, AUTOMATIC_OCR_UNAVAILABLE_WARNING))

    return _OCRPipelineResult(
        selected_result=selected_result,
        providers_attempted=tuple(attempts),
        warning_pairs=tuple(warning_pairs),
    )


async def _try_ocr_provider(
    *,
    adapter: OCRAdapter,
    image: OCRImageInput,
    role: ProviderAttemptRole,
    index: int,
    settings: Settings,
) -> tuple[_OCRProviderAttempt, OCRResult | None]:
    """Run one OCR provider and return sanitized attempt metadata.

    Args:
        adapter: OCR provider adapter.
        image: Validated OCR input.
        role: Provider role in the chain.
        index: Zero-based provider index within the role group.
        settings: Runtime settings controlling confidence threshold.

    Returns:
        Provider attempt metadata and candidate OCR result, if produced.
    """
    provider_hint = _provider_label_for_adapter(adapter, role=role, index=index)
    try:
        candidate = await adapter.extract_text(image)
    except OCRError:
        code = _provider_warning_code(OCR_PROVIDER_UNAVAILABLE_CODE_PREFIX, provider_hint)
        return (
            _OCRProviderAttempt(
                provider=provider_hint,
                role=role,
                status="error",
                warning_code=code,
                warning_message=OCR_PROVIDER_UNAVAILABLE_WARNING,
            ),
            None,
        )

    provider = candidate.provider.strip() or provider_hint
    if not candidate.text.strip():
        code = _provider_warning_code(OCR_PROVIDER_EMPTY_CODE_PREFIX, provider)
        return (
            _OCRProviderAttempt(
                provider=provider,
                role=role,
                status="empty_text",
                confidence=candidate.confidence,
                warning_code=code,
                warning_message=OCR_PROVIDER_EMPTY_WARNING,
            ),
            candidate,
        )
    if _is_low_confidence(candidate.confidence, settings):
        code = _provider_warning_code(OCR_PROVIDER_LOW_CONFIDENCE_CODE_PREFIX, provider)
        return (
            _OCRProviderAttempt(
                provider=provider,
                role=role,
                status="low_confidence",
                confidence=candidate.confidence,
                warning_code=code,
                warning_message=OCR_PROVIDER_LOW_CONFIDENCE_WARNING,
            ),
            candidate,
        )
    return (
        _OCRProviderAttempt(
            provider=provider,
            role=role,
            status="success",
            confidence=candidate.confidence,
        ),
        candidate,
    )


def _select_ocr_candidate(
    current: OCRResult | None,
    candidate: OCRResult | None,
) -> OCRResult | None:
    """Select the best available OCR candidate without storing raw provider payloads.

    Args:
        current: Current selected OCR candidate.
        candidate: Newly produced OCR candidate.

    Returns:
        Best OCR candidate for downstream parsing.
    """
    selected = current
    if candidate is None:
        return selected
    if selected is None:
        return candidate

    current_has_text = bool(selected.text.strip())
    candidate_has_text = bool(candidate.text.strip())
    candidate_is_better = candidate_has_text and (
        not current_has_text
        or (
            current_has_text
            and selected.confidence is not None
            and candidate.confidence is not None
            and candidate.confidence > selected.confidence
        )
    )
    if candidate_is_better:
        selected = candidate
    return selected


def _provider_label_for_adapter(
    adapter: OCRAdapter,
    *,
    role: ProviderAttemptRole,
    index: int,
) -> str:
    """Return a safe provider label for warning codes.

    Args:
        adapter: OCR provider adapter.
        role: Provider role in the chain.
        index: Zero-based provider index within the role group.

    Returns:
        Sanitized provider label.
    """
    provider = getattr(adapter, "provider", None)
    if isinstance(provider, str) and provider.strip():
        return _sanitize_provider_label(provider)
    class_name = adapter.__class__.__name__.lower()
    if "google" in class_name:
        return "google_vision_document"
    if "clova" in class_name:
        return "clova_ocr"
    if "paddle" in class_name:
        return "paddleocr_local"
    return f"{role}_ocr_{index}"


def _provider_warning_code(prefix: str, provider: str) -> str:
    """Build a stable provider warning code.

    Args:
        prefix: Warning code prefix.
        provider: OCR provider label.

    Returns:
        Provider-specific warning code.
    """
    return f"{prefix}:{_sanitize_provider_label(provider)}"


def _sanitize_provider_label(provider: str) -> str:
    """Sanitize a provider label for warning code use.

    Args:
        provider: Candidate provider label.

    Returns:
        Lowercase provider code containing only safe characters.
    """
    sanitized = "".join(
        character if character.isalnum() or character in {"_", "-"} else "_"
        for character in provider.strip().lower()
    )
    return sanitized or "unknown_ocr"


def _prepare_primary_ocr_image_input(
    *,
    image_bytes: bytes,
    image_metadata: ValidatedSupplementImage,
    label_region: BoundingBox | None,
    image_quality_report: ImageQualityReport | None = None,
    settings: Settings,
) -> tuple[OCRImageInput, str | None, str | None]:
    """Build primary OCR input, cropping ROI only when policy and metadata allow it.

    Args:
        image_bytes: Validated source image bytes.
        image_metadata: Validated image metadata.
        label_region: Optional detected label-region ROI.
        image_quality_report: Optional quality report used to avoid risky automatic crops.
        settings: Runtime settings controlling ROI preprocessing.

    Returns:
        OCR input plus optional warning code and message.
    """
    original_input = OCRImageInput(
        image_bytes=image_bytes,
        mime_type=image_metadata.mime_type,
        width=image_metadata.width,
        height=image_metadata.height,
        label_region=label_region,
    )
    if settings.ocr_roi_preprocessing_policy != "crop_before_primary" or label_region is None:
        return original_input, None, None
    if _has_quality_issue(image_quality_report, ROI_CROP_DEGRADE_REASON_CODES):
        return original_input, OCR_ROI_CROP_UNAVAILABLE_CODE, OCR_ROI_CROP_UNAVAILABLE_WARNING

    try:
        cropped_bytes = crop_image_to_bounding_box(image_bytes, label_region)
    except VisionPreprocessingError:
        return original_input, OCR_ROI_CROP_UNAVAILABLE_CODE, OCR_ROI_CROP_UNAVAILABLE_WARNING

    return (
        OCRImageInput(
            image_bytes=cropped_bytes,
            mime_type="image/png",
            width=label_region.width,
            height=label_region.height,
            label_region=None,
        ),
        None,
        None,
    )


def _has_quality_issue(
    image_quality_report: ImageQualityReport | None,
    reason_codes: frozenset[str],
) -> bool:
    """Return whether a quality report contains any matching reason code.

    Args:
        image_quality_report: Optional deterministic quality report.
        reason_codes: Issue reason codes that should degrade automatic crop.

    Returns:
        True when a matching issue is present.
    """
    if image_quality_report is None:
        return False
    return any(issue.reason_code in reason_codes for issue in image_quality_report.issues)


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
    try:
        return await multimodal_adapter.extract_text(
            OCRImageInput(
                image_bytes=image_bytes,
                mime_type=image_metadata.mime_type,
                width=image_metadata.width,
                height=image_metadata.height,
                label_region=label_region,
            )
        )
    except (OCRError, OllamaClientError, OllamaConfigurationError, OllamaStructuredOutputError):
        return ocr_result


async def _extract_secondary_ocr_if_allowed(
    *,
    image_bytes: bytes | None,
    image_metadata: ValidatedSupplementImage,
    label_region: BoundingBox | None,
    ocr_result: OCRResult | None,
    primary_ocr_attempted: bool,
    settings: Settings,
    fallback_adapters: tuple[OCRAdapter, ...],
) -> OCRResult | None:
    """Run optional secondary OCR providers after primary/multimodal weakness.

    Args:
        image_bytes: Validated image bytes, if loaded for adapter use.
        image_metadata: Validated image metadata.
        label_region: Optional YOLO ROI metadata.
        ocr_result: Current OCR result candidate.
        primary_ocr_attempted: Whether a primary OCR adapter was configured.
        settings: Runtime settings containing the OCR confidence threshold.
        fallback_adapters: Optional secondary OCR fallback adapters.

    Returns:
        Current OCR result or the first usable fallback result.
    """
    if not primary_ocr_attempted or image_bytes is None or not fallback_adapters:
        return ocr_result
    if not _should_run_secondary_fallback(ocr_result, settings):
        return ocr_result

    fallback_input = OCRImageInput(
        image_bytes=image_bytes,
        mime_type=image_metadata.mime_type,
        width=image_metadata.width,
        height=image_metadata.height,
        label_region=label_region,
    )
    for adapter in fallback_adapters:
        try:
            candidate = await adapter.extract_text(fallback_input)
        except OCRError:
            continue
        if candidate.text.strip():
            return candidate
    return ocr_result


async def _verify_ocr_with_multimodal_if_allowed(
    *,
    image_bytes: bytes | None,
    image_metadata: ValidatedSupplementImage,
    label_region: BoundingBox | None,
    ocr_result: OCRResult | None,
    settings: Settings,
    multimodal_adapter: OCRAdapter | None,
) -> tuple[str | None, str | None]:
    """Optionally verify accepted OCR text with the local vision assist adapter.

    Args:
        image_bytes: Validated image bytes, if loaded.
        image_metadata: Validated image metadata.
        label_region: Optional YOLO ROI metadata.
        ocr_result: OCR result selected for parsing.
        settings: Runtime settings controlling verification.
        multimodal_adapter: Local vision assist adapter.

    Returns:
        Optional warning code and message.
    """
    if not _should_run_multimodal_verification(
        ocr_result=ocr_result,
        settings=settings,
        multimodal_adapter=multimodal_adapter,
        image_bytes=image_bytes,
    ):
        return None, None

    assert ocr_result is not None
    assert multimodal_adapter is not None
    assert image_bytes is not None
    try:
        candidate = await multimodal_adapter.extract_text(
            OCRImageInput(
                image_bytes=image_bytes,
                mime_type=image_metadata.mime_type,
                width=image_metadata.width,
                height=image_metadata.height,
                label_region=label_region,
            )
        )
    except (OCRError, OllamaClientError, OllamaConfigurationError, OllamaStructuredOutputError):
        return None, None

    similarity = _normalized_text_similarity(ocr_result.text, candidate.text)
    if similarity < Decimal(str(settings.multimodal_verification_threshold)):
        return OCR_VERIFICATION_MISMATCH_CODE, OCR_VERIFICATION_MISMATCH_WARNING
    return None, None


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
    return _is_low_confidence(ocr_result.confidence, settings)


def _should_run_secondary_fallback(ocr_result: OCRResult | None, settings: Settings) -> bool:
    """Determine whether secondary OCR fallback providers should run.

    Args:
        ocr_result: Current OCR candidate.
        settings: Runtime settings containing the OCR confidence threshold.

    Returns:
        True when the current OCR candidate is empty or low confidence.
    """
    if ocr_result is None:
        return True
    if not ocr_result.text.strip():
        return True
    return _is_low_confidence(ocr_result.confidence, settings)


def _should_run_multimodal_verification(
    *,
    ocr_result: OCRResult | None,
    settings: Settings,
    multimodal_adapter: OCRAdapter | None,
    image_bytes: bytes | None,
) -> bool:
    """Determine whether local vision verification should run.

    Args:
        ocr_result: OCR result selected for parsing.
        settings: Runtime settings.
        multimodal_adapter: Local vision assist adapter.
        image_bytes: Validated image bytes.

    Returns:
        True only when verification is enabled and sampled.
    """
    if not settings.enable_multimodal_verification or not settings.enable_multimodal_llm:
        return False
    if multimodal_adapter is None or image_bytes is None or ocr_result is None:
        return False
    if not ocr_result.text.strip() or ocr_result.provider == "ollama_vision_assist":
        return False
    sample_rate = settings.multimodal_verification_sample_rate
    if sample_rate <= 0:
        return False
    if sample_rate >= 1:
        return True
    return random() < sample_rate


def _is_low_confidence(confidence: float | None, settings: Settings) -> bool:
    """Check whether OCR confidence should trigger vision assist review.

    Args:
        confidence: Provider-level confidence.
        settings: Runtime settings containing the OCR confidence threshold.

    Returns:
        True when confidence is present and below the configured threshold.
    """
    if confidence is None:
        return False
    return Decimal(str(confidence)) < Decimal(str(settings.ocr_confidence_threshold))


def _normalized_text_similarity(left: str, right: str) -> Decimal:
    """Return normalized similarity between OCR text candidates.

    Args:
        left: Primary OCR text.
        right: Verification text.

    Returns:
        Decimal similarity in the inclusive range 0.0 to 1.0.
    """
    left_normalized = " ".join(left.casefold().split())
    right_normalized = " ".join(right.casefold().split())
    if not left_normalized and not right_normalized:
        return Decimal("1")
    ratio = SequenceMatcher(a=left_normalized, b=right_normalized).ratio()
    return Decimal(str(ratio))


async def _parse_ocr_if_available(
    *,
    session: AsyncSession,
    user: AuthenticatedUser,
    intake: SupplementIntakeStoreResult,
    ocr_result: OCRResult | None,
    settings: Settings,
    parser: SupplementOCRTextParser | None,
) -> tuple[SupplementAnalysisRun | None, str | None, str | None]:
    """Parse OCR text only when OCR produced non-empty text.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        intake: Stored intake result.
        ocr_result: OCR result to parse.
        settings: Runtime settings.
        parser: Optional parser adapter.

    Returns:
        Updated analysis row and optional warning metadata.
    """
    if ocr_result is None or not ocr_result.text.strip():
        if ocr_result is None:
            return None, None, None
        return None, OCR_TEXT_EMPTY_CODE, OCR_TEXT_EMPTY_WARNING
    try:
        layout_context = build_supplement_layout_context(ocr_result, settings)
        parsed = await parse_supplement_analysis_ocr_text(
            session=session,
            user=user,
            analysis_id=intake.record.id,
            ocr_text=ocr_result.text,
            ocr_provider=ocr_result.provider,
            ocr_confidence=ocr_result.confidence,
            settings=settings,
            parser=parser,
            parser_input_text=layout_context.parser_input_text,
            layout_context=layout_context,
        )
    except PARSER_RECOVERABLE_ERRORS:
        return (
            None,
            OCR_PARSE_PREVIEW_UNAVAILABLE_CODE,
            OCR_PARSE_PREVIEW_UNAVAILABLE_WARNING,
        )
    return parsed.record, None, None


async def _store_preview_warnings(
    session: AsyncSession,
    record: SupplementAnalysisRun,
    warnings: list[str],
) -> None:
    """Persist recoverable OCR/parser warnings on an intake preview.

    Args:
        session: Request-scoped async database session.
        record: Intake preview row.
        warnings: Safe warning strings to add.
    """
    existing_warnings = list(record.warnings or [])
    for warning in warnings:
        if warning not in existing_warnings:
            existing_warnings.append(warning)
    record.warnings = existing_warnings
    await session.commit()
    await session.refresh(record)


async def _store_image_quality_report(
    session: AsyncSession,
    record: SupplementAnalysisRun,
    report: ImageQualityReport,
) -> None:
    """Persist a redacted image quality report in preview metadata.

    Args:
        session: Request-scoped async database session.
        record: Intake preview row.
        report: Deterministic quality report without raw image or OCR text.
    """
    parsed_snapshot = dict(record.parsed_snapshot or {})
    parsed_snapshot["image_quality_report"] = report.model_dump(mode="json")
    record.parsed_snapshot = parsed_snapshot
    await session.commit()
    await session.refresh(record)
