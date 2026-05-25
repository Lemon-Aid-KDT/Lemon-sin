"""Learning pipeline gate tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from src.config import Settings
from src.learning.pipeline import (
    IMAGE_EMBEDDING_JOB_STATUS_PENDING,
    LEARNING_IMAGE_STATUS_PENDING_MANUAL_REVIEW,
    LEARNING_IMAGE_STATUS_READY,
    LEARNING_IMAGE_STATUS_REJECTED_BY_AUTO_FILTER,
    LEARNING_IMAGE_STATUS_REJECTED_BY_REVIEW,
    approve_learning_image_object_after_manual_review,
    enqueue_learning_embedding_job_for_confirmation,
    evaluate_learning_metadata_auto_filter,
    evaluate_learning_metadata_storage_filter,
    reject_learning_image_object_after_manual_review,
)
from src.models.db.learning import ImageEmbeddingJob, LearningImageObject
from src.models.schemas.privacy import ConsentType
from src.security.auth import AuthenticatedUser


class _FakeSession:
    """Minimal async session for learning pipeline tests."""

    def __init__(self, scalar_results: list[object | None]) -> None:
        """Initialize scalar result queue and write tracking.

        Args:
            scalar_results: Values returned by sequential ``scalar`` calls.
        """
        self.scalar_results = scalar_results
        self.added: list[object] = []
        self.commit_count = 0

    async def scalar(self, _statement: object) -> object | None:
        """Return the next queued scalar result.

        Args:
            _statement: SQLAlchemy statement ignored by the fake session.

        Returns:
            Queued scalar value.
        """
        return self.scalar_results.pop(0)

    def add(self, record: object) -> None:
        """Track ORM records added by the service.

        Args:
            record: ORM record.
        """
        self.added.append(record)

    async def commit(self) -> None:
        """Track commits."""
        self.commit_count += 1

    async def refresh(self, _record: object) -> None:
        """No-op refresh for ORM records.

        Args:
            _record: ORM record.
        """


def _user() -> AuthenticatedUser:
    """Return an authenticated user fixture.

    Returns:
        Authenticated user.
    """
    return AuthenticatedUser(
        subject="user_123",
        issuer="https://auth.example.com/",
        claims={"sub": "user_123"},
    )


def _settings(*, manual_review: bool = True, auto_filter: bool = True) -> Settings:
    """Return learning-enabled development settings.

    Args:
        manual_review: Whether operator review is required before embedding jobs.
        auto_filter: Whether deterministic learning metadata filtering runs.

    Returns:
        Settings object.
    """
    return Settings(
        enable_image_learning_pipeline=True,
        enable_pgvector_storage=True,
        image_retention_days=30,
        require_learning_manual_review=manual_review,
        enable_learning_auto_filter=auto_filter,
    )


def _learning_consents() -> tuple[ConsentType, ...]:
    """Return all consents required for image learning reuse.

    Returns:
        Consent tuple accepted by the learning gate.
    """
    return (
        ConsentType.OCR_IMAGE_PROCESSING,
        ConsentType.DATA_RETENTION,
        ConsentType.IMAGE_LEARNING_DATASET,
    )


def _image_object(analysis_id: UUID) -> LearningImageObject:
    """Build a retained learning image object.

    Args:
        analysis_id: Source analysis identifier.

    Returns:
        Learning image object.
    """
    return LearningImageObject(
        id=uuid4(),
        owner_subject_hash="a" * 64,
        analysis_id=analysis_id,
        image_sha256="b" * 64,
        object_uri="s3://private-learning-images/learning/images/a/image",
        object_storage_provider="s3",
        object_version_id="version-1",
        image_mime_type="image/png",
        image_size_bytes=123,
        retained_until=datetime.now(UTC) + timedelta(days=30),
        status="awaiting_confirmation",
        consent_snapshot={"consents": []},
    )


def _metadata(**overrides: object) -> dict[str, object]:
    """Return sanitized confirmed supplement metadata for learning tests.

    Args:
        **overrides: Top-level metadata fields to override.

    Returns:
        Confirmed metadata snapshot with ingredient signal.
    """
    metadata: dict[str, object] = {
        "display_name": "Vitamin C",
        "ingredients": [
            {
                "display_name": "Vitamin C",
                "nutrient_code": "vitamin_c",
                "amount": "1000",
                "unit": "mg",
            }
        ],
    }
    metadata.update(overrides)
    return metadata


def test_learning_metadata_auto_filter_accepts_sanitized_ingredients() -> None:
    """Verify deterministic learning filter accepts structured supplement data."""
    decision = evaluate_learning_metadata_auto_filter(_metadata())

    assert decision.allowed is True
    assert decision.reason == "passed"


def test_learning_metadata_storage_filter_allows_low_signal_review_metadata() -> None:
    """Verify manual-review metadata storage can hold low-signal structured data."""
    decision = evaluate_learning_metadata_storage_filter({"display_name": "Vitamin C"})

    assert decision.allowed is True
    assert decision.reason == "passed"


@pytest.mark.parametrize(
    "metadata",
    [
        {"display_name": "Vitamin C", "raw_ocr_text": "label"},
        {"display_name": "Vitamin C", "ingredients": []},
        {"display_name": "Vitamin C", "ingredients": [{"display_name": ""}]},
        {"display_name": "Vitamin C", "ingredients": [{"display_name": "010-1234-5678"}]},
    ],
)
def test_learning_metadata_auto_filter_rejects_unsafe_or_low_signal_metadata(
    metadata: dict[str, object],
) -> None:
    """Verify auto-filter blocks raw payloads, PII-like text, and empty labels."""
    decision = evaluate_learning_metadata_auto_filter(metadata)

    assert decision.allowed is False


@pytest.mark.asyncio
async def test_confirmation_requires_manual_review_before_embedding_job() -> None:
    """Verify opt-in learning images stop at operator review by default."""
    analysis_id = uuid4()
    image_object = _image_object(analysis_id)
    session = _FakeSession([image_object, None])

    job = await enqueue_learning_embedding_job_for_confirmation(
        session=session,  # type: ignore[arg-type]
        user=_user(),
        analysis_id=analysis_id,
        metadata_snapshot=_metadata(),
        settings=_settings(),
        granted_consents=_learning_consents(),
    )

    assert job is None
    assert image_object.status == LEARNING_IMAGE_STATUS_PENDING_MANUAL_REVIEW
    assert image_object.review_metadata_snapshot == _metadata()
    assert session.added == []
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_confirmation_rejects_metadata_that_fails_auto_filter() -> None:
    """Verify unsafe metadata never reaches manual review or embedding jobs."""
    analysis_id = uuid4()
    image_object = _image_object(analysis_id)
    session = _FakeSession([image_object, None])

    job = await enqueue_learning_embedding_job_for_confirmation(
        session=session,  # type: ignore[arg-type]
        user=_user(),
        analysis_id=analysis_id,
        metadata_snapshot={"display_name": "Vitamin C", "raw_ocr_text": "label"},
        settings=_settings(),
        granted_consents=_learning_consents(),
    )

    assert job is None
    assert image_object.status == LEARNING_IMAGE_STATUS_REJECTED_BY_AUTO_FILTER
    assert session.added == []
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_confirmation_falls_back_to_manual_review_when_auto_filter_disabled() -> None:
    """Verify unavailable auto-filter still leaves a manual review barrier."""
    analysis_id = uuid4()
    image_object = _image_object(analysis_id)
    session = _FakeSession([image_object, None])

    job = await enqueue_learning_embedding_job_for_confirmation(
        session=session,  # type: ignore[arg-type]
        user=_user(),
        analysis_id=analysis_id,
        metadata_snapshot={"display_name": "Vitamin C"},
        settings=_settings(auto_filter=False),
        granted_consents=_learning_consents(),
    )

    assert job is None
    assert image_object.status == LEARNING_IMAGE_STATUS_PENDING_MANUAL_REVIEW
    assert image_object.review_metadata_snapshot == {"display_name": "Vitamin C"}
    assert session.added == []
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_confirmation_can_enqueue_after_manual_review_gate_is_disabled() -> None:
    """Verify development tests can still exercise the embedding job path."""
    analysis_id = uuid4()
    image_object = _image_object(analysis_id)
    session = _FakeSession([image_object, None])

    job = await enqueue_learning_embedding_job_for_confirmation(
        session=session,  # type: ignore[arg-type]
        user=_user(),
        analysis_id=analysis_id,
        metadata_snapshot=_metadata(),
        settings=_settings(manual_review=False),
        granted_consents=_learning_consents(),
    )

    assert isinstance(job, ImageEmbeddingJob)
    assert image_object.status == LEARNING_IMAGE_STATUS_READY
    assert job.status == IMAGE_EMBEDDING_JOB_STATUS_PENDING
    assert session.added == [job]
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_manual_review_approval_enqueues_job_from_stored_metadata() -> None:
    """Verify operator-approved review metadata enters the worker queue."""
    analysis_id = uuid4()
    image_object = _image_object(analysis_id)
    image_object.status = LEARNING_IMAGE_STATUS_PENDING_MANUAL_REVIEW
    image_object.review_metadata_snapshot = _metadata()
    session = _FakeSession([image_object, None])

    job = await approve_learning_image_object_after_manual_review(
        session=session,  # type: ignore[arg-type]
        image_object_id=image_object.id,
        settings=_settings(),
    )

    assert isinstance(job, ImageEmbeddingJob)
    assert image_object.status == LEARNING_IMAGE_STATUS_READY
    assert job.metadata_snapshot == _metadata()
    assert job.status == IMAGE_EMBEDDING_JOB_STATUS_PENDING
    assert session.added == [job]
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_manual_review_approval_respects_feature_gates() -> None:
    """Verify the operator approval path cannot bypass disabled learning flags."""
    analysis_id = uuid4()
    image_object = _image_object(analysis_id)
    image_object.status = LEARNING_IMAGE_STATUS_PENDING_MANUAL_REVIEW
    image_object.review_metadata_snapshot = _metadata()
    session = _FakeSession([image_object, None])

    job = await approve_learning_image_object_after_manual_review(
        session=session,  # type: ignore[arg-type]
        image_object_id=image_object.id,
        settings=Settings(),
    )

    assert job is None
    assert session.added == []
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_manual_review_approval_rejects_stored_low_signal_metadata() -> None:
    """Verify approval cannot bypass deterministic embedding metadata checks."""
    analysis_id = uuid4()
    image_object = _image_object(analysis_id)
    image_object.status = LEARNING_IMAGE_STATUS_PENDING_MANUAL_REVIEW
    image_object.review_metadata_snapshot = {"display_name": "Vitamin C"}
    session = _FakeSession([image_object, None])

    job = await approve_learning_image_object_after_manual_review(
        session=session,  # type: ignore[arg-type]
        image_object_id=image_object.id,
        settings=_settings(),
    )

    assert job is None
    assert image_object.status == LEARNING_IMAGE_STATUS_REJECTED_BY_AUTO_FILTER
    assert session.added == []
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_manual_review_rejection_marks_image_object_rejected() -> None:
    """Verify operator rejection is persisted without creating a job."""
    analysis_id = uuid4()
    image_object = _image_object(analysis_id)
    image_object.status = LEARNING_IMAGE_STATUS_PENDING_MANUAL_REVIEW
    session = _FakeSession([image_object])

    rejected = await reject_learning_image_object_after_manual_review(
        session=session,  # type: ignore[arg-type]
        image_object_id=image_object.id,
    )

    assert rejected is True
    assert image_object.status == LEARNING_IMAGE_STATUS_REJECTED_BY_REVIEW
    assert session.added == []
    assert session.commit_count == 1
