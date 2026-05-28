"""Food image intake and preview persistence service."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http import HTTPStatus
from io import BytesIO
from typing import Any, Protocol
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models.db.meal import FoodImageAnalysisRun, MealRecord
from src.models.schemas.meal import (
    FoodImagePipelineMetadata,
    MealAnalysisStatus,
    MealFoodCandidate,
    MealImageAnalysisPreview,
    MealType,
)
from src.security.auth import AuthenticatedUser
from src.security.subjects import build_owner_subject
from src.services.supplement_intake import derive_idempotency_key, detect_image_mime
from src.utils.image_safety import (
    ImageSafetyError,
    safe_load_with_bomb_guard,
    strip_image_metadata,
)
from src.vision.base import VisionError
from src.vision.food_yolo import FoodDetection, FoodYoloDetector, food_model_label

FOOD_IMAGE_ANALYSIS_ALGORITHM_VERSION = "food-image-preview-v1.0.0"
FOOD_IMAGE_ANALYSIS_WARNING_CODES = (
    "food_analysis_unavailable",
    "manual_entry_required",
)
FOOD_IMAGE_DETECTION_REVIEW_WARNING_CODES = ("food_detection_review_required",)
FOOD_IMAGE_DETECTOR_EMPTY_WARNING_CODES = (
    "food_detector_empty",
    "manual_entry_required",
)
FOOD_IMAGE_DETECTOR_UNAVAILABLE_WARNING_CODES = (
    "food_detector_unavailable",
    "manual_entry_required",
)
ALLOWED_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
READ_CHUNK_SIZE_BYTES = 64 * 1024


@dataclass(frozen=True)
class ValidatedMealImage:
    """Validated food image metadata.

    Attributes:
        sha256: SHA-256 hex digest of normalized image bytes.
        mime_type: Detected and accepted image MIME type.
        size_bytes: Normalized image size in bytes.
        width: Decoded image width in pixels.
        height: Decoded image height in pixels.
        normalized_bytes: Sanitized in-memory bytes used only for current-request
            detector inference. Not stored in the database or API response.
    """

    sha256: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    normalized_bytes: bytes = field(repr=False, compare=False)


@dataclass(frozen=True)
class MealImageAnalysisStoreResult:
    """Stored food image preview result.

    Attributes:
        meal_record: Persisted or reused meal preview row.
        analysis_run: Persisted or reused food image analysis run row.
        image_metadata: Validated image metadata.
        reused_existing: Whether idempotency returned an existing analysis run.
    """

    meal_record: MealRecord
    analysis_run: FoodImageAnalysisRun
    image_metadata: ValidatedMealImage
    reused_existing: bool


@dataclass(frozen=True)
class FoodDetectionResult:
    """Sanitized food detector outcome for one request.

    Attributes:
        detections: Review-only detector candidates.
        detector_model: Sanitized model label when configured.
        detector_used: Whether detector inference ran.
        warning_codes: Stable warning codes for the preview.
    """

    detections: tuple[FoodDetection, ...]
    detector_model: str | None
    detector_used: bool
    warning_codes: tuple[str, ...]


class FoodDetector(Protocol):
    """Protocol for request-local food image detectors."""

    def detect_foods(self, image_bytes: bytes) -> list[FoodDetection]:
        """Detect food candidates.

        Args:
            image_bytes: Request-local normalized image bytes.

        Returns:
            Review-only food detections.
        """
        ...


class MealImageValidationError(ValueError):
    """Raised when an uploaded food image fails validation."""

    def __init__(self, *, code: str, message: str, status_code: int) -> None:
        """Initialize a safe food image validation error.

        Args:
            code: Stable API error code.
            message: Safe user-facing message.
            status_code: HTTP status code for the route.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class MealImageAnalysisConflictError(ValueError):
    """Raised when an idempotency key is reused for different image bytes."""


async def read_and_validate_meal_image(image: UploadFile, settings: Settings) -> ValidatedMealImage:
    """Read, bound, hash, and validate a food image upload.

    Args:
        image: Uploaded food image.
        settings: Runtime settings containing shared image upload limits.

    Returns:
        Validated food image metadata.

    Raises:
        MealImageValidationError: If the upload is empty, too large, unsupported,
            spoofed, or not a valid image.
    """
    data = await _read_limited_upload(image, settings.supplement_image_max_bytes)
    content_type = image.content_type
    detected_mime = detect_image_mime(data[:16])

    if not data:
        raise MealImageValidationError(
            code="invalid_image",
            message="Uploaded food image is empty.",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    if content_type not in ALLOWED_IMAGE_MIME_TYPES or detected_mime is None:
        raise MealImageValidationError(
            code="unsupported_media_type",
            message="Only JPEG, PNG, and WebP food images are accepted.",
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        )
    if content_type != detected_mime:
        raise MealImageValidationError(
            code="unsupported_media_type",
            message="Uploaded food image content does not match its declared media type.",
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        )

    width, height = _validate_decodable_image(data, settings.supplement_image_max_pixels)

    try:
        sanitized = strip_image_metadata(data, detected_mime)
    except ImageSafetyError as exc:
        raise MealImageValidationError(
            code="invalid_image",
            message="Uploaded food image cannot be normalized.",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        ) from exc

    return ValidatedMealImage(
        sha256=hashlib.sha256(sanitized).hexdigest(),
        mime_type=detected_mime,
        size_bytes=len(sanitized),
        width=width,
        height=height,
        normalized_bytes=sanitized,
    )


async def create_meal_image_analysis_preview(
    *,
    session: AsyncSession,
    user: AuthenticatedUser,
    image_metadata: ValidatedMealImage,
    meal_type: MealType,
    eaten_at: datetime | None,
    client_request_id: str | None,
    settings: Settings,
    food_detector: FoodDetector | None = None,
) -> MealImageAnalysisStoreResult:
    """Persist a review-required food image preview for the current owner.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        image_metadata: Validated image metadata.
        meal_type: User-selected meal type.
        eaten_at: User-selected meal timestamp.
        client_request_id: Optional client idempotency key.
        settings: Runtime settings containing the privacy hash secret.
        food_detector: Optional injected local detector for tests.

    Returns:
        Stored meal and food image preview rows.

    Raises:
        MealImageAnalysisConflictError: If the idempotency key exists with a
            different image hash.
        ValueError: If owner identity cannot be persisted safely.
    """
    owner_subject = build_owner_subject(user)
    normalized_client_request_id = derive_idempotency_key(
        client_request_id,
        owner_subject,
        settings.privacy_hash_secret,
    )
    detection = _detect_food_candidates_if_enabled(
        image_metadata=image_metadata,
        settings=settings,
        food_detector=food_detector,
    )
    detected_items_snapshot = _food_detections_to_snapshot(detection.detections)
    nutrition_estimate_snapshot = _nutrition_estimate_snapshot(
        detection.detections,
        detector_used=detection.detector_used,
    )
    analysis_run: FoodImageAnalysisRun | None = None
    meal_record: MealRecord | None = None
    reused_existing = False

    async with session.begin():
        if normalized_client_request_id is not None:
            analysis_run = await session.scalar(
                select(FoodImageAnalysisRun).where(
                    FoodImageAnalysisRun.owner_subject == owner_subject,
                    FoodImageAnalysisRun.client_request_id == normalized_client_request_id,
                )
            )
            if analysis_run is not None:
                if analysis_run.image_sha256 != image_metadata.sha256:
                    raise MealImageAnalysisConflictError(
                        "client_request_id has already been used for a different image."
                    )
                reused_existing = True
                if analysis_run.meal_id is not None:
                    meal_record = await session.scalar(
                        select(MealRecord).where(
                            MealRecord.id == analysis_run.meal_id,
                            MealRecord.owner_subject == owner_subject,
                        )
                    )

        if analysis_run is not None and meal_record is None:
            raise MealImageAnalysisConflictError("stored meal preview is incomplete.")

        if analysis_run is None:
            meal_id = uuid4()
            meal_record = MealRecord(
                id=meal_id,
                owner_subject=owner_subject,
                client_request_id=normalized_client_request_id,
                eaten_at=_normalize_eaten_at(eaten_at),
                meal_type=meal_type.value,
                source="camera",
                status=MealAnalysisStatus.REQUIRES_CONFIRMATION.value,
                nutrition_summary=nutrition_estimate_snapshot,
                confidence=None,
                confirmed_at=None,
                deleted_at=None,
            )
            analysis_run = FoodImageAnalysisRun(
                id=uuid4(),
                owner_subject=owner_subject,
                client_request_id=normalized_client_request_id,
                media_object_id=None,
                meal_id=meal_id,
                image_sha256=image_metadata.sha256,
                image_mime_type=image_metadata.mime_type,
                image_size_bytes=image_metadata.size_bytes,
                detector_model=detection.detector_model,
                classifier_model=None,
                status=MealAnalysisStatus.REQUIRES_CONFIRMATION.value,
                detected_items_snapshot=detected_items_snapshot,
                nutrition_estimate_snapshot=nutrition_estimate_snapshot,
                warning_codes=list(detection.warning_codes),
            )
            session.add(meal_record)
            session.add(analysis_run)
            reused_existing = False

    if not reused_existing:
        await session.refresh(meal_record)
        await session.refresh(analysis_run)
    return MealImageAnalysisStoreResult(
        meal_record=meal_record,
        analysis_run=analysis_run,
        image_metadata=image_metadata,
        reused_existing=reused_existing,
    )


def meal_image_analysis_to_preview(
    result: MealImageAnalysisStoreResult,
) -> MealImageAnalysisPreview:
    """Convert stored food image rows to a safe API preview response.

    Args:
        result: Persisted food image preview result.

    Returns:
        Meal image analysis preview response.
    """
    analysis_run = result.analysis_run
    meal_record = result.meal_record
    return MealImageAnalysisPreview(
        analysis_id=analysis_run.id,
        meal_id=meal_record.id,
        status=MealAnalysisStatus(analysis_run.status),
        meal_type=MealType(meal_record.meal_type),
        eaten_at=meal_record.eaten_at,
        food_candidates=_snapshot_to_food_candidates(analysis_run.detected_items_snapshot),
        nutrition_estimate_summary=_dict_or_empty(analysis_run.nutrition_estimate_snapshot),
        warning_codes=list(_string_items(analysis_run.warning_codes)),
        pipeline_metadata=FoodImagePipelineMetadata(
            intake_completed=True,
            detector_model=analysis_run.detector_model,
            classifier_model=analysis_run.classifier_model,
            detector_used=bool(analysis_run.detector_model)
            and not _contains_warning(analysis_run.warning_codes, "food_detector_unavailable"),
            classifier_used=False,
            raw_image_stored=False,
            raw_provider_payload_stored=False,
            requires_manual_entry=not bool(_snapshot_items(analysis_run.detected_items_snapshot)),
        ),
        algorithm_version=FOOD_IMAGE_ANALYSIS_ALGORITHM_VERSION,
        created_at=analysis_run.created_at,
    )


def _detect_food_candidates_if_enabled(
    *,
    image_metadata: ValidatedMealImage,
    settings: Settings,
    food_detector: FoodDetector | None,
) -> FoodDetectionResult:
    """Run optional food YOLO without storing image bytes or provider payloads.

    Args:
        image_metadata: Validated in-memory image metadata and bytes.
        settings: Runtime settings.
        food_detector: Optional injected detector.

    Returns:
        Sanitized detector outcome for persistence.
    """
    if not settings.enable_food_yolo_detector:
        return FoodDetectionResult(
            detections=(),
            detector_model=None,
            detector_used=False,
            warning_codes=FOOD_IMAGE_ANALYSIS_WARNING_CODES,
        )

    detector_model = food_model_label(
        settings.meal_yolo_model_path,
        settings.meal_yolo_model_label,
    )
    if detector_model is None:
        return FoodDetectionResult(
            detections=(),
            detector_model=None,
            detector_used=False,
            warning_codes=FOOD_IMAGE_DETECTOR_UNAVAILABLE_WARNING_CODES,
        )

    detector = food_detector or FoodYoloDetector(
        model_path=settings.meal_yolo_model_path or "",
        model_label=detector_model,
        min_confidence=settings.meal_yolo_min_confidence,
        max_detections=settings.meal_yolo_max_detections,
    )
    try:
        detections = tuple(detector.detect_foods(image_metadata.normalized_bytes))
    except (OSError, ValueError, VisionError):
        return FoodDetectionResult(
            detections=(),
            detector_model=detector_model,
            detector_used=False,
            warning_codes=FOOD_IMAGE_DETECTOR_UNAVAILABLE_WARNING_CODES,
        )
    if not detections:
        return FoodDetectionResult(
            detections=(),
            detector_model=detector_model,
            detector_used=True,
            warning_codes=FOOD_IMAGE_DETECTOR_EMPTY_WARNING_CODES,
        )
    return FoodDetectionResult(
        detections=detections,
        detector_model=detector_model,
        detector_used=True,
        warning_codes=FOOD_IMAGE_DETECTION_REVIEW_WARNING_CODES,
    )


def _food_detections_to_snapshot(
    detections: tuple[FoodDetection, ...],
) -> dict[str, object]:
    """Convert food detections into sanitized JSON snapshot data.

    Args:
        detections: Detector candidates.

    Returns:
        JSON object without image bytes or provider payloads.
    """
    return {
        "items": [
            {
                "display_name": detection.label,
                "confidence": detection.confidence,
                "source": "vision",
                "bbox": {
                    "x": detection.bbox.x,
                    "y": detection.bbox.y,
                    "width": detection.bbox.width,
                    "height": detection.bbox.height,
                },
                "model": detection.model,
            }
            for detection in detections
        ]
    }


def _nutrition_estimate_snapshot(
    detections: tuple[FoodDetection, ...],
    *,
    detector_used: bool,
) -> dict[str, object]:
    """Build a bounded pre-confirmation nutrition summary.

    Args:
        detections: Detector candidates.
        detector_used: Whether detector inference ran.

    Returns:
        Safe nutrition summary placeholder for user review.
    """
    status = "detected_review_required" if detections else "analysis_unavailable"
    return {
        "status": status,
        "items": [
            {
                "display_name": detection.label,
                "confidence": detection.confidence,
                "source": "vision",
            }
            for detection in detections
        ],
        "totals": {},
        "detector_used": detector_used,
    }


def _snapshot_to_food_candidates(value: Any) -> list[MealFoodCandidate]:
    """Convert stored snapshot JSON into API food candidates.

    Args:
        value: Stored JSON snapshot.

    Returns:
        Review-only food candidates.
    """
    candidates: list[MealFoodCandidate] = []
    for item in _snapshot_items(value):
        display_name = item.get("display_name")
        confidence = item.get("confidence")
        if not isinstance(display_name, str):
            continue
        if not isinstance(confidence, int | float):
            continue
        candidates.append(
            MealFoodCandidate(
                display_name=display_name,
                portion_amount=None,
                portion_unit=None,
                kcal=None,
                carb_g=None,
                protein_g=None,
                fat_g=None,
                sodium_mg=None,
                confidence=float(confidence),
                source="vision",
            )
        )
    return candidates


def _snapshot_items(value: Any) -> list[dict[str, object]]:
    """Return dictionary items from snapshot JSON.

    Args:
        value: Stored snapshot JSON.

    Returns:
        Snapshot item dictionaries.
    """
    if not isinstance(value, dict):
        return []
    items = value.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _contains_warning(value: Any, warning_code: str) -> bool:
    """Return whether warning JSON contains a code.

    Args:
        value: Stored warning JSON.
        warning_code: Warning to find.

    Returns:
        True when present.
    """
    return isinstance(value, list) and warning_code in value


async def _read_limited_upload(image: UploadFile, max_bytes: int) -> bytes:
    """Read an uploaded file while enforcing a byte limit.

    Args:
        image: Uploaded file.
        max_bytes: Maximum accepted byte count.

    Returns:
        Uploaded bytes.

    Raises:
        MealImageValidationError: If the upload exceeds the size limit.
    """
    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await image.read(READ_CHUNK_SIZE_BYTES)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_bytes:
            raise MealImageValidationError(
                code="payload_too_large",
                message="Uploaded food image exceeds the configured size limit.",
                status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _validate_decodable_image(data: bytes, max_pixels: int) -> tuple[int, int]:
    """Verify image structure and pixel bounds without persisting image bytes.

    Args:
        data: Uploaded image bytes.
        max_pixels: Maximum accepted pixel count.

    Returns:
        Image width and height.

    Raises:
        MealImageValidationError: If the image is malformed or too large.
    """
    try:
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            if width <= 0 or height <= 0:
                raise MealImageValidationError(
                    code="invalid_image",
                    message="Uploaded food image has invalid dimensions.",
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                )
            if width * height > max_pixels:
                raise MealImageValidationError(
                    code="payload_too_large",
                    message="Uploaded food image exceeds the configured pixel limit.",
                    status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                )
            image.verify()
    except MealImageValidationError:
        raise
    except Image.DecompressionBombError as exc:
        raise MealImageValidationError(
            code="payload_too_large",
            message="Uploaded food image exceeds the configured pixel limit.",
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        ) from exc
    except (OSError, SyntaxError, UnidentifiedImageError) as exc:
        raise MealImageValidationError(
            code="invalid_image",
            message="Uploaded food image cannot be decoded.",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        ) from exc

    try:
        with safe_load_with_bomb_guard(data) as decoded:
            width, height = decoded.size
            return int(width), int(height)
    except ImageSafetyError as exc:
        raise MealImageValidationError(
            code="payload_too_large",
            message="Uploaded food image is too large to decode safely.",
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        ) from exc


def _normalize_eaten_at(value: datetime | None) -> datetime:
    """Return a timezone-aware meal timestamp.

    Args:
        value: User-selected timestamp or None.

    Returns:
        UTC-aware timestamp.
    """
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _dict_or_empty(value: Any) -> dict[str, object]:
    """Return a dictionary value or an empty dictionary.

    Args:
        value: Candidate JSON value.

    Returns:
        Dictionary value when present.
    """
    return value if isinstance(value, dict) else {}


def _string_items(value: Any) -> tuple[str, ...]:
    """Return bounded string items from a JSON value.

    Args:
        value: Candidate JSON array.

    Returns:
        Tuple of string values.
    """
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))
