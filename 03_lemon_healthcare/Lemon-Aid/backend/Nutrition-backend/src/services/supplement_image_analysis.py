"""Supplement image analysis orchestration service.

This service keeps the existing intake flow intact while creating a stable place
to plug in OCR, vision ROI detection, and future learning pipelines. Default
runtime behavior remains intake-only unless adapters are explicitly provided.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher
from http import HTTPStatus
from random import random
from time import perf_counter

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
from src.models.schemas.image_quality import ImageQualityReport
from src.models.schemas.privacy import ConsentType
from src.models.schemas.supplement import SupplementOCRProviderObservation
from src.ocr.base import OCRAdapter, OCRError, OCRImageInput, OCRResult
from src.security.auth import AuthenticatedUser
from src.services.supplement_image_quality import analyze_supplement_label_image_quality
from src.services.supplement_intake import (
    SupplementImageValidationError,
    SupplementIntakeStoreResult,
    ValidatedSupplementImage,
    create_supplement_analysis_intake,
    read_and_validate_supplement_image,
)
from src.services.supplement_parser import (
    OCR_LOW_CONFIDENCE_THRESHOLD,
    SupplementOCRTextParser,
    SupplementParserInputError,
    parse_supplement_analysis_ocr_text,
)
from src.utils.image_safety import ImageSafetyError, strip_image_metadata
from src.vision.base import BoundingBox, VisionAdapter, VisionError
from src.vision.preprocessing import (
    VisionPreprocessingError,
    crop_image_to_bounding_box,
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
AUTOMATIC_OCR_UNAVAILABLE_CODE = "automatic_ocr_unavailable"
OCR_TEXT_EMPTY_CODE = "ocr_text_empty"
OCR_PARSE_PREVIEW_UNAVAILABLE_CODE = "ocr_parse_preview_unavailable"
OCR_ROI_CROP_UNAVAILABLE_CODE = "ocr_roi_crop_unavailable"
OCR_VERIFICATION_MISMATCH_CODE = "ocr_verification_mismatch"
PARSER_RECOVERABLE_ERRORS = (
    SupplementParserInputError,
    OllamaClientError,
    OllamaConfigurationError,
    OllamaStructuredOutputError,
)


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
        image_quality_report: Optional deterministic image-quality report.
        ocr_result: Optional OCR output used by the parser.
        parser_used: Whether structured OCR text parsing was invoked.
        ocr_attempted: Whether a primary OCR adapter was configured and called.
        ocr_provider_observations: Sanitized OCR provider call observations.
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
    ocr_provider_observations: tuple[SupplementOCRProviderObservation, ...]
    ocr_warning_codes: tuple[str, ...]
    learning_image_object_created: bool


@dataclass(frozen=True)
class _OCRProviderCallObservation:
    """Internal OCR provider call observation before parser outcome is known."""

    provider: str
    stage: str
    status: str
    latency_ms: int | None = None
    text_non_empty: bool = False
    parser_success: bool | None = None
    error_code: str | None = None
    warning_codes: tuple[str, ...] = ()

    def to_schema(self) -> SupplementOCRProviderObservation:
        """Convert to the public sanitized observation schema."""
        return SupplementOCRProviderObservation.model_validate(
            {
                "provider": self.provider,
                "stage": self.stage,
                "status": self.status,
                "latency_ms": self.latency_ms,
                "text_non_empty": self.text_non_empty,
                "parser_success": self.parser_success,
                "error_code": self.error_code,
                "warning_codes": list(self.warning_codes),
                "raw_ocr_text_stored": False,
                "raw_provider_payload_stored": False,
            }
        )


@dataclass(frozen=True)
class _OCRExtractionResult:
    """Internal OCR extraction result with recoverable warning metadata."""

    ocr_result: OCRResult | None
    warning_code: str | None = None
    warning_message: str | None = None
    provider_observations: tuple[_OCRProviderCallObservation, ...] = ()


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
        image,
        active_adapters=active_adapters,
        settings=settings,
        needs_learning_image_bytes=learning_gate_allowed,
        needs_image_quality_report=True,
        image_metadata=image_metadata,
    )
    image_quality_report = _analyze_image_quality_if_available(
        image_bytes=image_bytes,
        image_metadata=image_metadata,
    )
    if image_quality_report is not None:
        await _store_image_quality_report(session, intake.record, image_quality_report)
    vision_region = await _detect_label_region_if_enabled(
        image_bytes=image_bytes,
        settings=settings,
        vision_adapter=active_adapters.vision,
    )
    ocr_attempted = active_adapters.ocr is not None
    ocr_extraction = await _extract_ocr_if_configured(
        image_bytes=image_bytes,
        image_metadata=image_metadata,
        label_region=vision_region,
        ocr_adapter=active_adapters.ocr,
        settings=settings,
    )
    provider_observations = list(ocr_extraction.provider_observations)
    ocr_result = ocr_extraction.ocr_result
    multimodal_extraction = await _extract_multimodal_ocr_if_allowed(
        image_bytes=image_bytes,
        image_metadata=image_metadata,
        label_region=vision_region,
        ocr_result=ocr_result,
        primary_ocr_attempted=active_adapters.ocr is not None,
        settings=settings,
        multimodal_adapter=active_adapters.multimodal_ocr,
    )
    provider_observations.extend(multimodal_extraction.provider_observations)
    ocr_result = multimodal_extraction.ocr_result
    secondary_extraction = await _extract_secondary_ocr_if_allowed(
        image_bytes=image_bytes,
        image_metadata=image_metadata,
        label_region=vision_region,
        ocr_result=ocr_result,
        primary_ocr_attempted=active_adapters.ocr is not None,
        fallback_adapters=active_adapters.fallback_ocr_adapters,
    )
    provider_observations.extend(secondary_extraction.provider_observations)
    ocr_result = secondary_extraction.ocr_result
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
        (ocr_extraction.warning_code, ocr_extraction.warning_message),
        (verification_warning_code, verification_warning_message),
        (parse_warning_code, parse_warning_message),
    ]
    warning_codes = tuple(code for code, message in warning_pairs if code and message)
    warning_messages = [message for code, message in warning_pairs if code and message]
    if warning_messages:
        await _store_preview_warnings(session, parsed_record or intake.record, warning_messages)
    ocr_provider_observations = _mark_parser_success(
        provider_observations,
        ocr_result=ocr_result,
        parser_success=parsed_record is not None,
    )
    if ocr_provider_observations:
        await _store_ocr_provider_observations(
            session,
            parsed_record or intake.record,
            ocr_provider_observations,
        )

    learning_object = None
    if learning_object_store is not None:
        learning_object = await maybe_store_learning_image_object(
            session=session,
            user=user,
            analysis=parsed_record or intake.record,
            image_bytes=image_bytes,
            image_metadata=image_metadata,
            settings=settings,
            object_store=learning_object_store,
            granted_consents=learning_consents,
        )

    return SupplementImageAnalysisResult(
        record=parsed_record or intake.record,
        reused_existing=intake.reused_existing,
        image_metadata=image_metadata,
        vision_region=vision_region,
        image_quality_report=image_quality_report,
        ocr_result=ocr_result,
        parser_used=parsed_record is not None,
        ocr_attempted=ocr_attempted,
        ocr_provider_observations=tuple(
            observation.to_schema() for observation in ocr_provider_observations
        ),
        ocr_warning_codes=warning_codes,
        learning_image_object_created=learning_object is not None,
    )


async def _read_validated_image_bytes_if_needed(
    image: UploadFile,
    *,
    active_adapters: SupplementImageAnalysisAdapters,
    settings: Settings,
    needs_learning_image_bytes: bool = False,
    needs_image_quality_report: bool = False,
    image_metadata: ValidatedSupplementImage,
) -> bytes | None:
    """Read image bytes for adapters only when an adapter path may execute.

    Bytes returned here are stripped of EXIF/XMP/IPTC metadata so downstream
    OCR adapters, learning storage, and audit consumers never observe user
    GPS coordinates or device identifiers.

    Args:
        image: Already validated upload file.
        active_adapters: Pipeline adapters requested for this call.
        settings: Runtime settings containing feature flags.
        needs_learning_image_bytes: Whether learning retention needs the original image bytes.
        needs_image_quality_report: Whether deterministic quality analysis needs image bytes.
        image_metadata: Validated metadata used to authorize the MIME for stripping.

    Returns:
        Sanitized image bytes, or None when no adapter needs them.

    Raises:
        SupplementImageValidationError: If the validated image fails the
            sanitization re-encode pass.
    """
    needs_bytes = active_adapters.ocr is not None or settings.enable_vision_classifier
    needs_bytes = needs_bytes or bool(active_adapters.fallback_ocr_adapters)
    needs_bytes = needs_bytes or needs_learning_image_bytes
    needs_bytes = needs_bytes or needs_image_quality_report
    needs_bytes = needs_bytes or (
        active_adapters.multimodal_ocr is not None and settings.enable_multimodal_llm
    )
    if not needs_bytes:
        return None
    await image.seek(0)
    raw = await image.read()
    try:
        return strip_image_metadata(raw, image_metadata.mime_type)
    except ImageSafetyError as exc:
        raise SupplementImageValidationError(
            code="invalid_image",
            message="Uploaded label image cannot be normalized for downstream use.",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        ) from exc


def _analyze_image_quality_if_available(
    *,
    image_bytes: bytes | None,
    image_metadata: ValidatedSupplementImage,
) -> ImageQualityReport | None:
    """Build a deterministic image-quality report when sanitized bytes exist.

    Args:
        image_bytes: Sanitized image bytes, if loaded for the current pipeline.
        image_metadata: Validated image metadata.

    Returns:
        Redacted image-quality report, or None when bytes are unavailable.
    """
    if image_bytes is None:
        return None
    return analyze_supplement_label_image_quality(image_bytes, image_metadata)


async def _store_image_quality_report(
    session: AsyncSession,
    record: SupplementAnalysisRun,
    report: ImageQualityReport,
) -> None:
    """Persist redacted image-quality metadata on the preview snapshot.

    Args:
        session: Request-scoped async database session.
        record: Intake preview row.
        report: Redacted deterministic quality report.
    """
    snapshot = dict(record.parsed_snapshot or {})
    snapshot["image_quality_report"] = report.model_dump(mode="json")
    snapshot.update(_image_quality_action_contract(report))
    record.parsed_snapshot = snapshot
    await session.commit()
    await session.refresh(record)


async def _store_ocr_provider_observations(
    session: AsyncSession,
    record: SupplementAnalysisRun,
    observations: tuple[_OCRProviderCallObservation, ...],
) -> None:
    """Persist sanitized OCR provider routing observations.

    Args:
        session: Request-scoped async database session.
        record: Preview row to update.
        observations: Sanitized provider observations without raw OCR text or payloads.
    """
    snapshot = dict(record.parsed_snapshot or {})
    snapshot["provider_observations"] = [
        observation.to_schema().model_dump(mode="json") for observation in observations
    ]
    record.parsed_snapshot = snapshot
    await session.commit()
    await session.refresh(record)


def _mark_parser_success(
    observations: list[_OCRProviderCallObservation],
    *,
    ocr_result: OCRResult | None,
    parser_success: bool,
) -> tuple[_OCRProviderCallObservation, ...]:
    """Mark the selected OCR provider observation with parser outcome."""
    if ocr_result is None:
        return tuple(observations)
    selected_index = _selected_observation_index(observations, ocr_result.provider)
    if selected_index is None:
        return tuple(observations)
    updated: list[_OCRProviderCallObservation] = []
    for index, observation in enumerate(observations):
        if index != selected_index:
            updated.append(observation)
            continue
        updated.append(
            _OCRProviderCallObservation(
                provider=observation.provider,
                stage=observation.stage,
                status=observation.status,
                latency_ms=observation.latency_ms,
                text_non_empty=observation.text_non_empty,
                parser_success=parser_success,
                error_code=observation.error_code,
                warning_codes=observation.warning_codes,
            )
        )
    return tuple(updated)


def _selected_observation_index(
    observations: list[_OCRProviderCallObservation],
    provider: str,
) -> int | None:
    """Return the latest completed non-empty observation for the selected provider."""
    for index in range(len(observations) - 1, -1, -1):
        observation = observations[index]
        if (
            observation.provider == provider
            and observation.status == "completed"
            and observation.text_non_empty
        ):
            return index
    return None


def _image_quality_action_contract(report: ImageQualityReport) -> dict[str, object]:
    """Map quality status to the existing mobile image-risk contract."""
    action_required = {
        "acceptable": "none",
        "needs_review": "review_required",
        "retake_recommended": "retake_recommended",
        "blocked": "blocked",
    }[report.status]
    missing_sections: list[str] = []
    if any(reason in report.retake_reasons for reason in ("cropped_label", "partial_table")):
        missing_sections.append("supplement_facts")
    return {
        "analysis_scope": "full_image_review",
        "action_required": action_required,
        "missing_required_sections": missing_sections,
        "image_role": "unknown",
        "source_type": "uploaded_image",
    }


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
    result, observation, error = await _call_ocr_adapter(
        ocr_adapter,
        ocr_input,
        stage="primary",
        warning_codes=(warning_code,) if warning_code else (),
    )
    if error is not None:
        return _OCRExtractionResult(
            ocr_result=None,
            warning_code=AUTOMATIC_OCR_UNAVAILABLE_CODE,
            warning_message=AUTOMATIC_OCR_UNAVAILABLE_WARNING,
            provider_observations=(observation,),
        )
    return _OCRExtractionResult(
        ocr_result=result,
        warning_code=warning_code,
        warning_message=warning_message,
        provider_observations=(observation,),
    )


def _prepare_primary_ocr_image_input(
    *,
    image_bytes: bytes,
    image_metadata: ValidatedSupplementImage,
    label_region: BoundingBox | None,
    settings: Settings,
) -> tuple[OCRImageInput, str | None, str | None]:
    """Build primary OCR input, cropping ROI only when policy and metadata allow it.

    Args:
        image_bytes: Validated source image bytes.
        image_metadata: Validated image metadata.
        label_region: Optional detected label-region ROI.
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

    try:
        cropped_bytes = crop_image_to_bounding_box(image_bytes, label_region)
    except VisionPreprocessingError:
        return (
            original_input,
            OCR_ROI_CROP_UNAVAILABLE_CODE,
            OCR_ROI_CROP_UNAVAILABLE_WARNING,
        )

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


async def _call_ocr_adapter(
    adapter: OCRAdapter,
    image: OCRImageInput,
    *,
    stage: str,
    warning_codes: tuple[str, ...] = (),
) -> tuple[OCRResult | None, _OCRProviderCallObservation, BaseException | None]:
    """Call an OCR adapter and return sanitized routing metadata.

    Args:
        adapter: OCR adapter to call.
        image: Validated OCR image input.
        stage: Pipeline stage label.
        warning_codes: Pre-existing warning codes tied to this call.

    Returns:
        OCR result, sanitized observation, and optional recoverable error.
    """
    start = perf_counter()
    try:
        result = await adapter.extract_text(image)
    except (
        OCRError,
        OllamaClientError,
        OllamaConfigurationError,
        OllamaStructuredOutputError,
    ) as exc:
        return (
            None,
            _OCRProviderCallObservation(
                provider=_adapter_label(adapter),
                stage=stage,
                status="error",
                latency_ms=_elapsed_ms(start),
                error_code=_ocr_error_code(exc),
                warning_codes=warning_codes,
            ),
            exc,
        )

    observation = _OCRProviderCallObservation(
        provider=result.provider or _adapter_label(adapter),
        stage=stage,
        status="completed",
        latency_ms=_elapsed_ms(start),
        text_non_empty=bool(result.text.strip()),
        warning_codes=tuple(
            _dedupe_strings((*warning_codes, *_ocr_observation_warning_codes(result)))
        ),
    )
    return result, observation, None


def _adapter_label(adapter: OCRAdapter) -> str:
    """Return a bounded adapter label without inspecting provider secrets."""
    label = getattr(adapter, "engine_name", None)
    if isinstance(label, str) and label.strip():
        return label.strip()[:80]
    return adapter.__class__.__name__[:80]


def _elapsed_ms(start: float) -> int:
    """Return elapsed wall-clock milliseconds."""
    return max(0, int((perf_counter() - start) * 1000))


def _ocr_error_code(exc: BaseException) -> str:
    """Return a bounded non-secret OCR error code."""
    return exc.__class__.__name__[:80]


def _ocr_observation_warning_codes(result: OCRResult) -> tuple[str, ...]:
    """Return bounded warning codes for an OCR result."""
    warnings: list[str] = []
    if not result.text.strip():
        warnings.append(OCR_TEXT_EMPTY_CODE)
    if _is_low_confidence(result.confidence):
        warnings.append("ocr_low_confidence")
    return tuple(warnings)


def _dedupe_strings(values: tuple[str | None, ...]) -> list[str]:
    """Normalize and deduplicate short warning codes."""
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        stripped = value.strip()
        if not stripped or stripped in seen:
            continue
        normalized.append(stripped)
        seen.add(stripped)
    return normalized


async def _extract_multimodal_ocr_if_allowed(
    *,
    image_bytes: bytes | None,
    image_metadata: ValidatedSupplementImage,
    label_region: BoundingBox | None,
    ocr_result: OCRResult | None,
    primary_ocr_attempted: bool,
    settings: Settings,
    multimodal_adapter: OCRAdapter | None,
) -> _OCRExtractionResult:
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
        OCR extraction result with any provider observations.
    """
    if not primary_ocr_attempted:
        return _OCRExtractionResult(ocr_result=ocr_result)
    if ocr_result is not None and not _should_run_multimodal_fallback(ocr_result, settings):
        return _OCRExtractionResult(ocr_result=ocr_result)
    if not settings.enable_multimodal_llm or multimodal_adapter is None or image_bytes is None:
        return _OCRExtractionResult(ocr_result=ocr_result)
    candidate, observation, error = await _call_ocr_adapter(
        multimodal_adapter,
        OCRImageInput(
            image_bytes=image_bytes,
            mime_type=image_metadata.mime_type,
            width=image_metadata.width,
            height=image_metadata.height,
            label_region=label_region,
        ),
        stage="multimodal_fallback",
    )
    if error is not None:
        return _OCRExtractionResult(
            ocr_result=ocr_result,
            provider_observations=(observation,),
        )
    return _OCRExtractionResult(
        ocr_result=candidate,
        provider_observations=(observation,),
    )


async def _extract_secondary_ocr_if_allowed(
    *,
    image_bytes: bytes | None,
    image_metadata: ValidatedSupplementImage,
    label_region: BoundingBox | None,
    ocr_result: OCRResult | None,
    primary_ocr_attempted: bool,
    fallback_adapters: tuple[OCRAdapter, ...],
) -> _OCRExtractionResult:
    """Run optional secondary OCR providers after primary/multimodal weakness.

    Args:
        image_bytes: Validated image bytes, if loaded for adapter use.
        image_metadata: Validated image metadata.
        label_region: Optional YOLO ROI metadata.
        ocr_result: Current OCR result candidate.
        primary_ocr_attempted: Whether a primary OCR adapter was configured.
        fallback_adapters: Optional secondary OCR fallback adapters.

    Returns:
        OCR extraction result with fallback provider observations.
    """
    if not primary_ocr_attempted or image_bytes is None or not fallback_adapters:
        return _OCRExtractionResult(ocr_result=ocr_result)
    if not _should_run_secondary_fallback(ocr_result):
        return _OCRExtractionResult(ocr_result=ocr_result)

    fallback_input = OCRImageInput(
        image_bytes=image_bytes,
        mime_type=image_metadata.mime_type,
        width=image_metadata.width,
        height=image_metadata.height,
        label_region=label_region,
    )
    observations: list[_OCRProviderCallObservation] = []
    for adapter in fallback_adapters:
        candidate, observation, error = await _call_ocr_adapter(
            adapter,
            fallback_input,
            stage="secondary_fallback",
        )
        observations.append(observation)
        if error is not None or candidate is None:
            continue
        if candidate.text.strip():
            return _OCRExtractionResult(
                ocr_result=candidate,
                provider_observations=tuple(observations),
            )
    return _OCRExtractionResult(
        ocr_result=ocr_result,
        provider_observations=tuple(observations),
    )


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
    except (
        OCRError,
        OllamaClientError,
        OllamaConfigurationError,
        OllamaStructuredOutputError,
    ):
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
        return settings.multimodal_ocr_assist_policy in {
            "ocr_empty_only",
            "low_confidence",
        }
    if not ocr_result.text.strip():
        return settings.multimodal_ocr_assist_policy in {
            "ocr_empty_only",
            "low_confidence",
        }
    if settings.multimodal_ocr_assist_policy != "low_confidence":
        return False
    return _is_low_confidence(ocr_result.confidence)


def _should_run_secondary_fallback(ocr_result: OCRResult | None) -> bool:
    """Determine whether secondary OCR fallback providers should run.

    Args:
        ocr_result: Current OCR candidate.

    Returns:
        True when the current OCR candidate is empty or low confidence.
    """
    if ocr_result is None:
        return True
    if not ocr_result.text.strip():
        return True
    return _is_low_confidence(ocr_result.confidence)


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
