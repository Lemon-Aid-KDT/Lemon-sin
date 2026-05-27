"""Meal image analysis preview service tests."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from io import BytesIO
from typing import Self, cast
from uuid import uuid4

import pytest
from fastapi import UploadFile
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import Settings
from src.models.db.meal import FoodImageAnalysisRun, MealRecord
from src.models.schemas.meal import MealAnalysisStatus, MealType
from src.security.auth import AuthenticatedUser
from src.services.meal_image_analysis import (
    FOOD_IMAGE_ANALYSIS_ALGORITHM_VERSION,
    MealImageAnalysisConflictError,
    MealImageValidationError,
    ValidatedMealImage,
    create_meal_image_analysis_preview,
    meal_image_analysis_to_preview,
    read_and_validate_meal_image,
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
    """Fake async session for meal image preview write tests."""

    def __init__(
        self,
        *,
        existing_run: FoodImageAnalysisRun | None = None,
        existing_meal: MealRecord | None = None,
    ) -> None:
        """Initialize fake persisted records.

        Args:
            existing_run: Existing food image analysis run returned for idempotency lookup.
            existing_meal: Existing meal record returned for idempotency lookup.
        """
        self.existing_run = existing_run
        self.existing_meal = existing_meal
        self.added: list[object] = []
        self.refreshed: list[object] = []

    def begin(self) -> _TransactionContext:
        """Return a fake transaction context.

        Returns:
            Fake async transaction context.
        """
        return _TransactionContext()

    async def scalar(self, statement: object) -> object | None:
        """Return fake existing rows based on selected ORM entity.

        Args:
            statement: SQLAlchemy select statement.

        Returns:
            Existing ORM row or None.
        """
        column_descriptions = getattr(statement, "column_descriptions", [])
        model = column_descriptions[0].get("entity") if column_descriptions else None
        if model is FoodImageAnalysisRun:
            return self.existing_run
        if model is MealRecord:
            return self.existing_meal
        return None

    def add(self, record: object) -> None:
        """Capture the ORM record being added.

        Args:
            record: ORM object passed by the service.

        Returns:
            None.
        """
        self.added.append(record)

    async def refresh(self, record: object) -> None:
        """Populate server-generated timestamps after fake persistence.

        Args:
            record: ORM object to refresh.

        Returns:
            None.
        """
        if hasattr(record, "created_at"):
            record.created_at = datetime.now(UTC)
        if hasattr(record, "updated_at"):
            record.updated_at = datetime.now(UTC)
        self.refreshed.append(record)


def _settings(
    *,
    supplement_image_max_bytes: int = 5 * 1024 * 1024,
    supplement_image_max_pixels: int = 12_000_000,
) -> Settings:
    """Return settings for meal image analysis tests.

    Args:
        supplement_image_max_bytes: Maximum image byte size.
        supplement_image_max_pixels: Maximum decoded image pixels.

    Returns:
        Settings object.
    """
    return Settings(
        supplement_image_max_bytes=supplement_image_max_bytes,
        supplement_image_max_pixels=supplement_image_max_pixels,
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


def _image_metadata(sha256: str = "a" * 64) -> ValidatedMealImage:
    """Return validated image metadata fixture.

    Args:
        sha256: Image SHA-256 hex digest.

    Returns:
        Validated meal image metadata.
    """
    return ValidatedMealImage(
        sha256=sha256,
        mime_type="image/png",
        size_bytes=128,
        width=3,
        height=2,
    )


def _existing_preview(image_sha256: str) -> tuple[MealRecord, FoodImageAnalysisRun]:
    """Return an existing meal preview and analysis run fixture.

    Args:
        image_sha256: Stored image hash.

    Returns:
        Meal record and food image analysis run.
    """
    now = datetime.now(UTC)
    meal = MealRecord(
        id=uuid4(),
        owner_subject="https://auth.example.com/::user_123",
        client_request_id="client-1",
        eaten_at=now,
        meal_type=MealType.LUNCH.value,
        source="camera",
        status=MealAnalysisStatus.REQUIRES_CONFIRMATION.value,
        nutrition_summary={"items": [], "totals": {}},
        created_at=now,
        updated_at=now,
    )
    run = FoodImageAnalysisRun(
        id=uuid4(),
        owner_subject=meal.owner_subject,
        client_request_id=meal.client_request_id,
        meal_id=meal.id,
        image_sha256=image_sha256,
        image_mime_type="image/png",
        image_size_bytes=128,
        status=MealAnalysisStatus.REQUIRES_CONFIRMATION.value,
        detected_items_snapshot={"items": []},
        nutrition_estimate_snapshot={"status": "analysis_unavailable", "totals": {}},
        warning_codes=["manual_entry_required"],
        created_at=now,
        updated_at=now,
    )
    return meal, run


@pytest.mark.asyncio
async def test_read_and_validate_meal_image_returns_hash_and_dimensions() -> None:
    """Verify valid food images return only bounded image metadata."""
    data = _png_bytes()

    result = await read_and_validate_meal_image(_upload(data), _settings())

    assert result.sha256 == hashlib.sha256(data).hexdigest()
    assert result.mime_type == "image/png"
    assert result.size_bytes == len(data)
    assert (result.width, result.height) == (3, 2)


@pytest.mark.asyncio
async def test_read_and_validate_meal_image_rejects_spoofed_content_type() -> None:
    """Verify declared MIME type must match image magic bytes."""
    with pytest.raises(MealImageValidationError) as exc_info:
        await read_and_validate_meal_image(_upload(_png_bytes(), "image/jpeg"), _settings())

    assert exc_info.value.code == "unsupported_media_type"
    assert exc_info.value.status_code == 415


@pytest.mark.asyncio
async def test_create_meal_image_preview_stores_manual_entry_preview_only() -> None:
    """Verify food image preview rows contain no raw image or provider payload."""
    fake_session = _FakeStoreSession()
    eaten_at = datetime(2026, 5, 27, 12, 30, tzinfo=UTC)

    result = await create_meal_image_analysis_preview(
        session=cast(AsyncSession, fake_session),
        user=_user(),
        image_metadata=_image_metadata(),
        meal_type=MealType.LUNCH,
        eaten_at=eaten_at,
        client_request_id="client-1",
        settings=_settings(),
    )

    assert result.reused_existing is False
    assert fake_session.added == [result.meal_record, result.analysis_run]
    assert fake_session.refreshed == [result.meal_record, result.analysis_run]
    assert result.meal_record.meal_type == "lunch"
    assert result.meal_record.eaten_at == eaten_at
    assert result.meal_record.nutrition_summary == {"items": [], "totals": {}}
    assert result.analysis_run.media_object_id is None
    assert result.analysis_run.image_sha256 == "a" * 64
    assert result.analysis_run.detected_items_snapshot == {"items": []}
    assert result.analysis_run.nutrition_estimate_snapshot == {
        "status": "analysis_unavailable",
        "totals": {},
    }
    serialized_records = str(result.meal_record.__dict__) + str(result.analysis_run.__dict__)
    assert "raw-client-name" not in serialized_records
    assert "provider_payload" not in serialized_records
    assert "image_bytes" not in serialized_records


@pytest.mark.asyncio
async def test_create_meal_image_preview_reuses_matching_idempotency_key() -> None:
    """Verify matching idempotency keys reuse existing safe previews."""
    meal, run = _existing_preview("a" * 64)
    fake_session = _FakeStoreSession(existing_run=run, existing_meal=meal)

    result = await create_meal_image_analysis_preview(
        session=cast(AsyncSession, fake_session),
        user=_user(),
        image_metadata=_image_metadata(),
        meal_type=MealType.DINNER,
        eaten_at=None,
        client_request_id="client-1",
        settings=_settings(),
    )

    assert result.reused_existing is True
    assert result.meal_record is meal
    assert result.analysis_run is run
    assert fake_session.added == []
    assert fake_session.refreshed == []


@pytest.mark.asyncio
async def test_create_meal_image_preview_rejects_idempotency_conflict() -> None:
    """Verify idempotency keys cannot be reused for different image hashes."""
    meal, run = _existing_preview("b" * 64)
    fake_session = _FakeStoreSession(existing_run=run, existing_meal=meal)

    with pytest.raises(MealImageAnalysisConflictError):
        await create_meal_image_analysis_preview(
            session=cast(AsyncSession, fake_session),
            user=_user(),
            image_metadata=_image_metadata("a" * 64),
            meal_type=MealType.LUNCH,
            eaten_at=None,
            client_request_id="client-1",
            settings=_settings(),
        )


def test_meal_image_analysis_to_preview_is_sanitized() -> None:
    """Verify API preview exposes only structured metadata and warning codes."""
    meal, run = _existing_preview("a" * 64)
    result = meal_image_analysis_to_preview(
        result=type(
            "Result",
            (),
            {
                "meal_record": meal,
                "analysis_run": run,
                "image_metadata": _image_metadata(),
                "reused_existing": True,
            },
        )()
    )

    assert result.analysis_id == run.id
    assert result.meal_id == meal.id
    assert result.status == MealAnalysisStatus.REQUIRES_CONFIRMATION
    assert result.meal_type == MealType.LUNCH
    assert result.food_candidates == []
    assert result.pipeline_metadata.raw_image_stored is False
    assert result.pipeline_metadata.raw_provider_payload_stored is False
    assert result.pipeline_metadata.requires_manual_entry is True
    assert result.algorithm_version == FOOD_IMAGE_ANALYSIS_ALGORITHM_VERSION
