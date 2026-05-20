"""Supplement image intake service tests."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Self, cast
from uuid import uuid4

import pytest
from fastapi import UploadFile
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import Settings
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.supplement import SupplementAnalysisStatus
from src.security.auth import AuthenticatedUser
from src.services.supplement_intake import (
    SUPPLEMENT_INTAKE_ALGORITHM_VERSION,
    SupplementImageValidationError,
    SupplementIntakeConflictError,
    ValidatedSupplementImage,
    create_supplement_analysis_intake,
    detect_image_mime,
    read_and_validate_supplement_image,
    supplement_analysis_run_to_preview,
)
from starlette.datastructures import Headers


class _TransactionContext:
    """Async context manager used by the fake session transaction."""

    async def __aenter__(self) -> Self:
        """Enter the fake transaction.

        Returns:
            Context manager instance.
        """
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Exit the fake transaction.

        Args:
            *_exc_info: Exception information ignored by the fake context.

        Returns:
            None.
        """


class _FakeStoreSession:
    """Fake async session for supplement intake write tests."""

    def __init__(self, existing: SupplementAnalysisRun | None = None) -> None:
        self.existing = existing
        self.added: SupplementAnalysisRun | None = None
        self.refreshed: SupplementAnalysisRun | None = None
        self.committed = False
        self.rolled_back = False

    def begin(self) -> _TransactionContext:
        """Return a fake transaction context.

        Returns:
            Fake async transaction context.
        """
        return _TransactionContext()

    async def scalar(self, _statement: object) -> SupplementAnalysisRun | None:
        """Return a fake existing row for idempotency lookup.

        Args:
            _statement: SQLAlchemy select statement.

        Returns:
            Existing supplement analysis run or None.
        """
        return self.existing

    def add(self, record: object) -> None:
        """Capture the ORM record being added.

        Args:
            record: ORM object passed by the service.

        Returns:
            None.
        """
        self.added = cast(SupplementAnalysisRun, record)

    async def refresh(self, record: object) -> None:
        """Populate server-generated fields after fake persistence.

        Args:
            record: ORM object to refresh.

        Returns:
            None.
        """
        supplement_run = cast(SupplementAnalysisRun, record)
        supplement_run.id = uuid4()
        supplement_run.created_at = datetime.now(UTC)
        supplement_run.updated_at = datetime.now(UTC)
        self.refreshed = supplement_run

    async def commit(self) -> None:
        """Record a fake transaction commit.

        Returns:
            None.
        """
        self.committed = True

    async def rollback(self) -> None:
        """Record a fake transaction rollback.

        Returns:
            None.
        """
        self.rolled_back = True


def _settings(
    *,
    supplement_image_max_bytes: int = 5 * 1024 * 1024,
    supplement_image_max_pixels: int = 12_000_000,
    supplement_preview_ttl_minutes: int = 30,
) -> Settings:
    """Return settings for supplement intake tests.

    Args:
        supplement_image_max_bytes: Maximum image byte size.
        supplement_image_max_pixels: Maximum decoded image pixels.
        supplement_preview_ttl_minutes: Preview TTL in minutes.

    Returns:
        Settings object.
    """
    return Settings(
        supplement_image_max_bytes=supplement_image_max_bytes,
        supplement_image_max_pixels=supplement_image_max_pixels,
        supplement_preview_ttl_minutes=supplement_preview_ttl_minutes,
    )


def _user() -> AuthenticatedUser:
    """Return an authenticated user fixture.

    Returns:
        Authenticated user model.
    """
    return AuthenticatedUser(
        subject="user_123",
        issuer="https://auth.example.com/",
        claims={"sub": "user_123"},
    )


def _png_bytes(size: tuple[int, int] = (3, 2)) -> bytes:
    """Return a tiny PNG image.

    Args:
        size: Image size.

    Returns:
        PNG image bytes.
    """
    buffer = BytesIO()
    Image.new("RGB", size, color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_with_exif_bytes() -> bytes:
    """Return a tiny JPEG containing client-supplied EXIF metadata.

    Returns:
        JPEG image bytes with EXIF tags.
    """
    buffer = BytesIO()
    exif = Image.Exif()
    exif[0x010E] = "client-supplied-label-description"
    exif[0x0110] = "client-camera-model"
    Image.new("RGB", (4, 3), color=(255, 255, 255)).save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def _upload(data: bytes, content_type: str = "image/png") -> UploadFile:
    """Build an UploadFile for service tests.

    Args:
        data: File bytes.
        content_type: Declared upload MIME type.

    Returns:
        UploadFile object.
    """
    return UploadFile(
        file=BytesIO(data),
        filename="raw-client-name.png",
        headers=Headers({"content-type": content_type}),
    )


def _image_metadata(sha256: str = "a" * 64) -> ValidatedSupplementImage:
    """Return validated image metadata fixture.

    Args:
        sha256: Image SHA-256 hex digest.

    Returns:
        Validated image metadata.
    """
    return ValidatedSupplementImage(
        sha256=sha256,
        mime_type="image/png",
        size_bytes=128,
        width=3,
        height=2,
        image_bytes=_png_bytes(),
    )


def _existing_run(image_sha256: str) -> SupplementAnalysisRun:
    """Return an existing supplement analysis run fixture.

    Args:
        image_sha256: Stored image hash.

    Returns:
        Existing supplement analysis run.
    """
    now = datetime.now(UTC)
    return SupplementAnalysisRun(
        id=uuid4(),
        owner_subject="https://auth.example.com/::user_123",
        client_request_id="client-1",
        status=SupplementAnalysisStatus.REQUIRES_CONFIRMATION.value,
        image_sha256=image_sha256,
        image_mime_type="image/png",
        image_size_bytes=128,
        ocr_provider="intake-only",
        parsed_snapshot={"parsed_product": {}, "ingredient_candidates": []},
        match_snapshot={"matched_product_candidates": []},
        warnings=[],
        algorithm_version=SUPPLEMENT_INTAKE_ALGORITHM_VERSION,
        expires_at=now + timedelta(minutes=30),
        created_at=now,
        updated_at=now,
    )


def test_detect_image_mime_supports_allowed_magic_bytes() -> None:
    """Verify image MIME detection uses magic bytes rather than filenames."""
    assert detect_image_mime(b"\xff\xd8\xff\xe0") == "image/jpeg"
    assert detect_image_mime(b"\x89PNG\r\n\x1a\nrest") == "image/png"
    assert detect_image_mime(b"RIFFxxxxWEBPrest") == "image/webp"
    assert detect_image_mime(b"not-an-image") is None


@pytest.mark.asyncio
async def test_read_and_validate_supplement_image_returns_hash_and_dimensions() -> None:
    """Verify valid PNG uploads return bounded sanitized image metadata."""
    data = _png_bytes()

    result = await read_and_validate_supplement_image(_upload(data), _settings())

    assert result.sha256 == hashlib.sha256(result.image_bytes).hexdigest()
    assert result.mime_type == "image/png"
    assert result.size_bytes == len(result.image_bytes)
    assert (result.width, result.height) == (3, 2)


@pytest.mark.asyncio
async def test_read_and_validate_supplement_image_strips_exif_metadata() -> None:
    """Verify client EXIF metadata is removed before downstream image use."""
    data = _jpeg_with_exif_bytes()
    with Image.open(BytesIO(data)) as raw_image:
        assert raw_image.getexif()

    result = await read_and_validate_supplement_image(_upload(data, "image/jpeg"), _settings())

    assert result.mime_type == "image/jpeg"
    assert result.sha256 == hashlib.sha256(result.image_bytes).hexdigest()
    with Image.open(BytesIO(result.image_bytes)) as sanitized_image:
        assert not sanitized_image.getexif()


@pytest.mark.asyncio
async def test_read_and_validate_rejects_media_type_spoofing() -> None:
    """Verify declared MIME type must match image magic bytes."""
    with pytest.raises(SupplementImageValidationError) as exc_info:
        await read_and_validate_supplement_image(_upload(_png_bytes(), "image/jpeg"), _settings())

    assert exc_info.value.code == "unsupported_media_type"
    assert exc_info.value.status_code == 415


@pytest.mark.asyncio
async def test_read_and_validate_rejects_oversized_byte_payload() -> None:
    """Verify uploads are rejected before decoding when byte size exceeds the limit."""
    data = b"x" * 1025

    with pytest.raises(SupplementImageValidationError) as exc_info:
        await read_and_validate_supplement_image(
            _upload(data),
            _settings(supplement_image_max_bytes=1024),
        )

    assert exc_info.value.code == "payload_too_large"
    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_read_and_validate_rejects_corrupt_supported_image() -> None:
    """Verify corrupt images with supported magic bytes are rejected as invalid images."""
    with pytest.raises(SupplementImageValidationError) as exc_info:
        await read_and_validate_supplement_image(
            _upload(b"\x89PNG\r\n\x1a\ncorrupt"),
            _settings(),
        )

    assert exc_info.value.code == "invalid_image"
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_read_and_validate_rejects_excessive_pixel_count() -> None:
    """Verify decoded image dimensions are bounded to reduce decompression risk."""
    with pytest.raises(SupplementImageValidationError) as exc_info:
        await read_and_validate_supplement_image(
            _upload(_png_bytes(size=(10, 10))),
            _settings(supplement_image_max_pixels=50),
        )

    assert exc_info.value.code == "payload_too_large"
    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_create_supplement_analysis_intake_stores_sanitized_preview() -> None:
    """Verify intake persistence stores owner, hash, and sanitized snapshots only."""
    fake_session = _FakeStoreSession()

    result = await create_supplement_analysis_intake(
        cast(AsyncSession, fake_session),
        _user(),
        _image_metadata(),
        " client-1 ",
        _settings(),
    )

    assert result.reused_existing is False
    assert result.record is fake_session.added
    assert result.record is fake_session.refreshed
    assert fake_session.committed is True
    assert fake_session.rolled_back is False
    assert result.record.owner_subject == "https://auth.example.com/::user_123"
    assert result.record.client_request_id == "client-1"
    assert result.record.image_sha256 == "a" * 64
    assert result.record.ocr_text_hash is None
    assert result.record.parsed_snapshot["intake"] == {
        "mime_type": "image/png",
        "size_bytes": 128,
        "width": 3,
        "height": 2,
    }
    assert "filename" not in result.record.parsed_snapshot["intake"]


@pytest.mark.asyncio
async def test_create_supplement_analysis_intake_reuses_existing_same_hash() -> None:
    """Verify matching idempotency key and image hash return the existing row."""
    existing = _existing_run("a" * 64)
    fake_session = _FakeStoreSession(existing=existing)

    result = await create_supplement_analysis_intake(
        cast(AsyncSession, fake_session),
        _user(),
        _image_metadata(),
        "client-1",
        _settings(),
    )

    assert result.record is existing
    assert result.reused_existing is True
    assert fake_session.added is None
    assert fake_session.refreshed is None
    assert fake_session.committed is True


@pytest.mark.asyncio
async def test_create_supplement_analysis_intake_rejects_idempotency_conflict() -> None:
    """Verify reused idempotency keys cannot point to different image bytes."""
    fake_session = _FakeStoreSession(existing=_existing_run("b" * 64))

    with pytest.raises(SupplementIntakeConflictError):
        await create_supplement_analysis_intake(
            cast(AsyncSession, fake_session),
            _user(),
            _image_metadata(),
            "client-1",
            _settings(),
        )
    assert fake_session.rolled_back is True


def test_supplement_analysis_run_to_preview_omits_intake_metadata() -> None:
    """Verify API preview omits stored image hash and intake metadata."""
    record = _existing_run("a" * 64)
    record.parsed_snapshot = {
        "parsed_product": {},
        "ingredient_candidates": [],
        "low_confidence_fields": ["label_text"],
        "intake": {"mime_type": "image/png", "size_bytes": 128},
    }

    preview = supplement_analysis_run_to_preview(record)
    body = preview.model_dump()

    assert body["analysis_id"] == record.id
    assert body["low_confidence_fields"] == ["label_text"]
    assert "image_sha256" not in body
    assert "intake" not in body


def test_supplement_analysis_run_to_preview_exposes_bounded_section_review() -> None:
    """Verify mobile preview exposes bounded sections without raw OCR text."""
    record = _existing_run("a" * 64)
    record.parsed_snapshot = {
        "schema_version": "supplement-parsed-snapshot-v3",
        "requires_user_confirmation": True,
        "source": {
            "ocr_provider": "google_vision_document",
            "ocr_confidence": 0.86,
            "layout_available": True,
            "raw_image_stored": False,
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "raw_model_response_stored": False,
        },
        "layout_context": {
            "schema_version": "supplement-layout-context-v1",
            "provider": "google_vision_document",
            "layout_available": True,
            "sections": [
                {
                    "section_id": "section-001",
                    "section_type": "ingredients",
                    "source_section_type": "ingredients",
                    "heading_text": "영양정보",
                    "text_bundle": "Vitamin D 25 ug",
                    "confidence": 0.92,
                    "requires_review": False,
                    "evidence_refs": ["span-ingredient"],
                    "row_count": 1,
                    "cell_count": 2,
                }
            ],
            "evidence_spans": [],
            "low_confidence_sections": [],
            "low_confidence_fields": [],
            "warnings": [],
            "fallback_reason": None,
        },
        "product": {"product_name": "Vitamin D", "manufacturer": "Lemon Labs"},
        "serving": {
            "serving_size_text": "1 tablet",
            "serving_amount": 1,
            "serving_unit": "tablet",
            "daily_servings": 1,
        },
        "ingredients": [
            {
                "display_name": "Vitamin D",
                "amount": 25,
                "unit": "ug",
                "nutrient_code_candidates": [
                    {
                        "nutrient_code": "vitamin_d_ug",
                        "match_method": "alias_exact",
                        "confidence": 0.98,
                    }
                ],
                "confidence": 0.92,
                "source": "ocr_llm_preview",
                "evidence_refs": ["span-ingredient"],
            }
        ],
        "label_sections": [
            {
                "section_type": "ingredients",
                "heading_text": "영양정보",
                "evidence_refs": ["span-ingredient"],
            }
        ],
        "intake_method": {
            "text": "Take 1 tablet daily.",
            "structured": {
                "frequency": "daily",
                "times_per_day": 1,
                "amount_per_time": 1,
                "amount_unit": "tablet",
                "time_of_day": [],
                "with_food": "unknown",
            },
            "evidence_refs": ["span-intake"],
        },
        "precautions": [
            {
                "text": "Consult a professional if pregnant.",
                "category": "pregnancy",
                "severity": "label_caution",
                "evidence_refs": ["span-precaution"],
            }
        ],
        "functional_claims": [
            {
                "text": "Supports normal bone health.",
                "claim_type": "label_claim",
                "evidence_refs": ["span-claim"],
            }
        ],
        "evidence_spans": [
            {
                "span_id": "span-ingredient",
                "source_type": "label_layout",
                "section_type": "ingredients",
                "text_excerpt": "Vitamin D 25 ug",
                "confidence": 0.92,
            },
            {
                "span_id": "span-intake",
                "source_type": "label_layout",
                "section_type": "intake_method",
                "text_excerpt": "Take 1 tablet daily.",
                "confidence": 0.6,
            },
            {
                "span_id": "span-precaution",
                "source_type": "label_layout",
                "section_type": "precautions",
                "text_excerpt": "Consult a professional if pregnant.",
                "confidence": 0.91,
            },
            {
                "span_id": "span-claim",
                "source_type": "label_layout",
                "section_type": "functional_info",
                "text_excerpt": "Supports normal bone health.",
                "confidence": 0.88,
            },
        ],
        "low_confidence_fields": ["intake_method"],
        "warnings": [],
    }

    preview = supplement_analysis_run_to_preview(record)
    body = preview.model_dump()

    assert body["layout_available"] is True
    assert body["label_sections"][0]["text_bundle"] == "Vitamin D 25 ug"
    assert body["intake_method"]["requires_review"] is True
    assert body["precautions"][0]["category"] == "pregnancy"
    assert body["functional_claims"][0]["claim_type"] == "label_claim"
    assert body["evidence_spans"][0]["text_excerpt"] == "Vitamin D 25 ug"
    assert "raw_ocr_text" not in str(body)


def test_supplement_analysis_run_to_preview_exposes_image_risk_action() -> None:
    """Verify preview conversion exposes structured image risk actions."""
    record = _existing_run("a" * 64)
    record.parsed_snapshot = {
        "schema_version": "supplement-parsed-snapshot-v3",
        "requires_user_confirmation": True,
        "source": {
            "ocr_provider": "google_vision_document",
            "raw_image_stored": False,
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "raw_model_response_stored": False,
        },
        "product": {"product_name": "Vitamin D"},
        "serving": {},
        "ingredients": [],
        "warnings": [],
        "image_quality_report": {
            "status": "retake_recommended",
            "issues": [
                {
                    "reason_code": "cover_only",
                    "severity": "retake",
                    "message": "Only the front label is visible.",
                    "evidence": {"label": "brand_front_label"},
                }
            ],
            "metrics": {"image_width": 400, "image_height": 300},
            "detected_rois": [
                {
                    "label": "brand_front_label",
                    "x": 10,
                    "y": 20,
                    "width": 180,
                    "height": 220,
                    "confidence": 0.94,
                    "area_ratio": 0.33,
                }
            ],
            "retake_reasons": ["cover_only"],
        },
    }

    preview = supplement_analysis_run_to_preview(record)
    body = preview.model_dump()

    assert body["action_required"] == "additional_label_image_required"
    assert body["analysis_scope"] == "identity_only"
    assert body["image_role"] == "front_label"
    assert body["missing_required_sections"] == ["supplement_facts"]
    assert body["detected_product_regions"][0]["region_id"] == "roi-001"
    assert body["detected_product_regions"][0]["selected"] is True
