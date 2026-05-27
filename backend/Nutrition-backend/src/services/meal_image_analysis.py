"""Food image intake and preview persistence service."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from io import BytesIO
from typing import Any
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

FOOD_IMAGE_ANALYSIS_ALGORITHM_VERSION = "food-image-preview-v1.0.0"
FOOD_IMAGE_ANALYSIS_WARNING_CODES = (
    "food_analysis_unavailable",
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
    """

    sha256: str
    mime_type: str
    size_bytes: int
    width: int
    height: int


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
) -> MealImageAnalysisStoreResult:
    """Persist a manual-entry food image preview for the current owner.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        image_metadata: Validated image metadata.
        meal_type: User-selected meal type.
        eaten_at: User-selected meal timestamp.
        client_request_id: Optional client idempotency key.
        settings: Runtime settings containing the privacy hash secret.

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
                nutrition_summary={"items": [], "totals": {}},
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
                detector_model=None,
                classifier_model=None,
                status=MealAnalysisStatus.REQUIRES_CONFIRMATION.value,
                detected_items_snapshot={"items": []},
                nutrition_estimate_snapshot={
                    "status": "analysis_unavailable",
                    "totals": {},
                },
                warning_codes=list(FOOD_IMAGE_ANALYSIS_WARNING_CODES),
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
        food_candidates=[],
        nutrition_estimate_summary=_dict_or_empty(analysis_run.nutrition_estimate_snapshot),
        warning_codes=list(_string_items(analysis_run.warning_codes)),
        pipeline_metadata=FoodImagePipelineMetadata(
            intake_completed=True,
            detector_model=analysis_run.detector_model,
            classifier_model=analysis_run.classifier_model,
            detector_used=False,
            classifier_used=False,
            raw_image_stored=False,
            raw_provider_payload_stored=False,
            requires_manual_entry=True,
        ),
        algorithm_version=FOOD_IMAGE_ANALYSIS_ALGORITHM_VERSION,
        created_at=analysis_run.created_at,
    )


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
