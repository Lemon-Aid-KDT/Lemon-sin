"""Supplement label image intake service."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from io import BytesIO
from typing import Any

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.image_quality import ImageQualityReport
from src.models.schemas.supplement import (
    MatchedSupplementCandidate,
    SupplementAnalysisPreview,
    SupplementAnalysisStatus,
    SupplementIngredientCandidate,
    SupplementOCRProviderObservation,
    SupplementParsedProduct,
)
from src.security.auth import AuthenticatedUser
from src.security.subjects import build_owner_subject
from src.utils.image_safety import (
    ImageSafetyError,
    safe_load_with_bomb_guard,
    strip_image_metadata,
)

SUPPLEMENT_INTAKE_ALGORITHM_VERSION = "supplement-intake-v1.0.0"
SUPPLEMENT_INTAKE_PROVIDER = "intake-only"
SUPPLEMENT_INTAKE_WARNING = (
    "Image intake is complete. OCR and LLM extraction are pending and require user review."
)
ALLOWED_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
READ_CHUNK_SIZE_BYTES = 64 * 1024
WEBP_HEADER_MIN_BYTES = 12


@dataclass(frozen=True)
class ValidatedSupplementImage:
    """Validated supplement label image metadata.

    Attributes:
        sha256: SHA-256 hex digest of the uploaded image bytes.
        mime_type: Detected and accepted image MIME type.
        size_bytes: Uploaded image size in bytes.
        width: Decoded image width in pixels.
        height: Decoded image height in pixels.
    """

    sha256: str
    mime_type: str
    size_bytes: int
    width: int
    height: int


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

    width, height = _validate_decodable_image(data, settings.supplement_image_max_pixels)

    try:
        sanitized = strip_image_metadata(data, detected_mime)
    except ImageSafetyError as exc:
        raise SupplementImageValidationError(
            code="invalid_image",
            message="Uploaded label image cannot be normalized.",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        ) from exc

    return ValidatedSupplementImage(
        sha256=hashlib.sha256(sanitized).hexdigest(),
        mime_type=detected_mime,
        size_bytes=len(sanitized),
        width=width,
        height=height,
    )


def supplement_analysis_run_to_preview(
    record: SupplementAnalysisRun,
) -> SupplementAnalysisPreview:
    """Convert an intake preview ORM row to its API response model.

    Args:
        record: Persisted supplement analysis run.

    Returns:
        Supplement analysis preview response.
    """
    parsed_snapshot = _dict_or_empty(record.parsed_snapshot)
    match_snapshot = _dict_or_empty(record.match_snapshot)
    image_quality_report = _image_quality_report_from_snapshot(parsed_snapshot)
    return SupplementAnalysisPreview(
        analysis_id=record.id,
        status=SupplementAnalysisStatus(record.status),
        parsed_product=SupplementParsedProduct.model_validate(
            _dict_or_empty(parsed_snapshot.get("parsed_product"))
        ),
        ingredient_candidates=[
            SupplementIngredientCandidate.model_validate(item)
            for item in _dict_items(parsed_snapshot.get("ingredient_candidates"))
        ],
        matched_product_candidates=[
            MatchedSupplementCandidate.model_validate(item)
            for item in _dict_items(match_snapshot.get("matched_product_candidates"))
        ],
        low_confidence_fields=list(_string_items(parsed_snapshot.get("low_confidence_fields"))),
        provider_observations=[
            SupplementOCRProviderObservation.model_validate(item)
            for item in _dict_items(parsed_snapshot.get("provider_observations"))
        ],
        image_quality_report=image_quality_report,
        analysis_scope=_snapshot_string(parsed_snapshot, "analysis_scope", "unknown"),
        action_required=_snapshot_string(parsed_snapshot, "action_required", "none"),
        missing_required_sections=list(
            _string_items(parsed_snapshot.get("missing_required_sections"))
        ),
        image_role=_snapshot_string(parsed_snapshot, "image_role", "unknown"),
        source_type=_snapshot_string(parsed_snapshot, "source_type", "uploaded_image"),
        warnings=list(_string_items(record.warnings)),
        algorithm_version=record.algorithm_version,
        source_manifest_version=record.source_manifest_version,
        expires_at=record.expires_at,
    )


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
    normalized_client_request_id = derive_idempotency_key(
        client_request_id,
        owner_subject,
        settings.privacy_hash_secret,
    )
    record: SupplementAnalysisRun | None = None
    reused_existing = False

    async with session.begin():
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


def _validate_decodable_image(data: bytes, max_pixels: int) -> tuple[int, int]:
    """Verify image structure and pixel bounds without persisting image bytes.

    Args:
        data: Uploaded image bytes.
        max_pixels: Maximum accepted pixel count.

    Returns:
        Image width and height.

    Raises:
        SupplementImageValidationError: If the image is malformed or too large.
    """
    try:
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
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
            image.verify()
    except SupplementImageValidationError:
        raise
    except Image.DecompressionBombError as exc:
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

    try:
        with safe_load_with_bomb_guard(data) as decoded:
            width, height = decoded.size
            return int(width), int(height)
    except ImageSafetyError as exc:
        raise SupplementImageValidationError(
            code="payload_too_large",
            message="Uploaded label image is too large to decode safely.",
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        ) from exc


def _build_intake_parsed_snapshot(
    image_metadata: ValidatedSupplementImage,
) -> dict[str, Any]:
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


def derive_idempotency_key(
    client_request_id: str | None,
    owner_subject: str,
    privacy_hash_secret: SecretStr,
) -> str | None:
    """Combine an owner-scoped HMAC prefix with the client's idempotency hint.

    The server never trusts client-supplied keys to be unique across owners.
    A short HMAC of the authenticated owner_subject is prepended so that two
    users cannot collide on the same hint by accident, and a single user
    cannot probe for another user's key by reusing the same string.

    Args:
        client_request_id: Raw client idempotency key, possibly ``None``.
        owner_subject: Hashed owner identifier used as the HMAC input.
        privacy_hash_secret: Application HMAC secret already used for OCR text
            hashing in :func:`hash_ocr_text`.

    Returns:
        Owner-scoped idempotency key, or ``None`` when no client value was
        provided.
    """
    normalized = _normalize_client_request_id(client_request_id)
    if normalized is None:
        return None
    secret = privacy_hash_secret.get_secret_value().encode("utf-8")
    digest = hmac.new(secret, owner_subject.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return f"{digest}:{normalized[:120]}"


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


def _snapshot_string(
    snapshot: dict[str, Any],
    key: str,
    default: str,
) -> str:
    """Return a bounded string from a parsed snapshot.

    Args:
        snapshot: Parsed snapshot dictionary.
        key: Snapshot field name.
        default: Fallback value.

    Returns:
        Snapshot string or fallback.
    """
    value = snapshot.get(key)
    if isinstance(value, str) and value:
        return value
    return default


def _image_quality_report_from_snapshot(
    snapshot: dict[str, Any],
) -> ImageQualityReport | None:
    """Return a validated image-quality report from the snapshot.

    Args:
        snapshot: Parsed snapshot dictionary.

    Returns:
        Image quality report or None.
    """
    candidate = snapshot.get("image_quality_report")
    if isinstance(candidate, dict):
        return ImageQualityReport.model_validate(candidate)
    return None
