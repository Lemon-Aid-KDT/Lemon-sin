"""Privacy service tests."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import TracebackType
from typing import cast
from uuid import uuid4

import pytest
from fastapi import Request
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import Settings
from src.models.db.analysis_result import AnalysisResult
from src.models.db.health import HealthDailySummary, HealthSyncBatch
from src.models.db.learning import ImageEmbeddingJob, ImageEmbeddingRecord, LearningImageObject
from src.models.db.privacy import AuditLog, ConsentRecord, DeletionRequest
from src.models.db.regulated import RegulatedDocument
from src.models.db.supplement import (
    SupplementAnalysisRun,
    UserSupplement,
    UserSupplementIngredient,
)
from src.models.schemas.privacy import ConsentType
from src.privacy.consent_policies import ACTIVE_CONSENT_POLICIES
from src.security.auth import AuthenticatedUser
from src.services.privacy import (
    create_delete_all_user_data_request,
    record_audit_event,
    revoke_consent,
)


class _FakeAuditSession:
    """Fake async session that captures audit writes."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False

    def add(self, record: object) -> None:
        """Capture a persisted object.

        Args:
            record: ORM object passed by the service.

        Returns:
            None.
        """
        self.added.append(record)

    async def commit(self) -> None:
        """Record a fake commit.

        Returns:
            None.
        """
        self.committed = True


class _FakeScalarResult:
    """Fake SQLAlchemy scalar result for predefined records."""

    def __init__(self, records: list[object]) -> None:
        self._records = records

    def all(self) -> list[object]:
        """Return captured records.

        Returns:
            Predefined scalar records.
        """
        return self._records


class _FakeTransaction:
    """Fake async transaction context manager."""

    async def __aenter__(self) -> None:
        """Enter the fake transaction.

        Returns:
            None.
        """

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """Exit the fake transaction.

        Args:
            exc_type: Exception type when the block failed.
            exc: Exception instance when the block failed.
            traceback: Exception traceback when the block failed.

        Returns:
            False so exceptions propagate.
        """
        return False


class _FakeDeletionSession:
    """Fake async session that serves model-specific query results."""

    def __init__(self, records_by_model: dict[type[object], list[object]]) -> None:
        self._records_by_model = records_by_model
        self.deleted: list[object] = []
        self.added: list[object] = []

    def begin(self) -> _FakeTransaction:
        """Return a fake transaction context manager.

        Returns:
            Fake async transaction.
        """
        return _FakeTransaction()

    async def scalars(self, statement: object) -> _FakeScalarResult:
        """Return records keyed by the selected ORM entity.

        Args:
            statement: SQLAlchemy select statement.

        Returns:
            Fake scalar result for the selected model.
        """
        column_descriptions = getattr(statement, "column_descriptions", [])
        model = column_descriptions[0].get("entity") if column_descriptions else None
        if not isinstance(model, type):
            return _FakeScalarResult([])
        return _FakeScalarResult(self._records_by_model.get(model, []))

    async def delete(self, record: object) -> None:
        """Capture a deleted object.

        Args:
            record: ORM object passed by the service.

        Returns:
            None.
        """
        self.deleted.append(record)

    def add(self, record: object) -> None:
        """Capture a persisted object.

        Args:
            record: ORM object passed by the service.

        Returns:
            None.
        """
        self.added.append(record)

    async def refresh(self, _record: object) -> None:
        """No-op refresh for fake ORM records.

        Args:
            _record: ORM object refreshed by the service.

        Returns:
            None.
        """


class _FakeLearningObjectStore:
    """Fake learning object store that records deletes."""

    def __init__(self) -> None:
        """Initialize captured object deletes."""
        self.deleted: list[tuple[str, str | None]] = []

    async def delete_image(self, object_uri: str, version_id: str | None = None) -> None:
        """Capture a private object deletion request.

        Args:
            object_uri: Private object URI.
            version_id: Optional object version.

        Returns:
            None.
        """
        self.deleted.append((object_uri, version_id))


def _request() -> Request:
    """Return a request fixture with auditable metadata.

    Returns:
        Starlette request object.
    """
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/analysis-results/activity-score",
            "headers": [
                (b"user-agent", b"raw-test-agent"),
                (b"x-request-id", b"req-123"),
            ],
            "client": ("203.0.113.10", 12345),
        }
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


def test_external_ocr_processing_policy_is_active() -> None:
    """Verify Google Vision OCR has a separate active consent bucket."""
    policy = ACTIVE_CONSENT_POLICIES[ConsentType.EXTERNAL_OCR_PROCESSING]

    assert policy.consent_type == ConsentType.EXTERNAL_OCR_PROCESSING
    assert policy.version == "2026-05-15"
    assert policy.required is False
    assert len(policy.content_hash) == 64


@pytest.mark.asyncio
async def test_revoke_image_learning_consent_deletes_learning_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify learning opt-out deletes retained image and vector artifacts."""
    now = datetime.now(UTC)
    analysis_id = uuid4()
    image_object = LearningImageObject(
        id=uuid4(),
        owner_subject_hash="a" * 64,
        analysis_id=analysis_id,
        image_sha256="b" * 64,
        object_uri="s3://learning-images/private/object.png",
        object_storage_provider="supabase_s3",
        object_version_id="version-1",
        image_mime_type="image/png",
        image_size_bytes=1024,
        retained_until=now + timedelta(days=30),
        status="ready",
        consent_snapshot={"consents": []},
    )
    embedding_job = ImageEmbeddingJob(
        id=uuid4(),
        image_object_id=image_object.id,
        analysis_id=analysis_id,
        owner_subject_hash="a" * 64,
        embedding_model="clip-test",
        status="pending",
        attempt_count=0,
        next_run_at=now,
        metadata_snapshot={"display_name": "Vitamin C"},
    )
    embedding_record = ImageEmbeddingRecord(
        id=uuid4(),
        owner_subject_hash="a" * 64,
        analysis_id=analysis_id,
        image_object_id=image_object.id,
        image_sha256=image_object.image_sha256,
        embedding_model="clip-test",
        embedding_dimensions=3,
        embedding=(0.1, 0.2, 0.3),
        embedding_metadata={"display_name": "Vitamin C"},
    )
    fake_session = _FakeDeletionSession(
        {
            ImageEmbeddingJob: [embedding_job],
            ImageEmbeddingRecord: [embedding_record],
            LearningImageObject: [image_object],
        }
    )
    fake_store = _FakeLearningObjectStore()
    monkeypatch.setattr(
        "src.services.privacy.build_learning_object_store",
        lambda _settings: fake_store,
    )
    settings = Settings(privacy_hash_secret=SecretStr("test-privacy-secret"))

    consent_record = await revoke_consent(
        cast(AsyncSession, fake_session),
        _user(),
        ConsentType.IMAGE_LEARNING_DATASET,
        _request(),
        settings,
    )

    assert consent_record.granted is False
    assert fake_store.deleted == [(image_object.object_uri, image_object.object_version_id)]
    assert fake_session.deleted == [embedding_job, embedding_record, image_object]
    audit_log = fake_session.added[1]
    assert isinstance(audit_log, AuditLog)
    assert audit_log.event_metadata["learning_deleted_counts"] == {
        "learning_image_objects": 1,
        "image_embedding_jobs": 1,
        "image_embedding_records": 1,
        "learning_image_object_blobs": 1,
        "learning_image_object_delete_failures": 0,
    }
    serialized_metadata = str(audit_log.event_metadata)
    assert image_object.object_uri not in serialized_metadata
    assert "owner_subject_hash" not in serialized_metadata


@pytest.mark.asyncio
async def test_record_audit_event_sanitizes_sensitive_metadata() -> None:
    """Verify audit logs exclude raw snapshots and store hashed request metadata."""
    fake_session = _FakeAuditSession()
    settings = Settings(privacy_hash_secret=SecretStr("test-privacy-secret"))

    audit_log = await record_audit_event(
        cast(AsyncSession, fake_session),
        _user(),
        action="analysis_result_created",
        resource_type="analysis_result",
        resource_id="result-123",
        outcome="success",
        request=_request(),
        settings=settings,
        event_metadata={
            "analysis_type": "activity_score",
            "input_snapshot": {"daily_steps": 7000},
            "authorization": "Bearer raw-token",
            "nested": {"token": "raw-nested-token", "safe": "ok"},
        },
    )

    assert fake_session.committed is True
    assert fake_session.added == [audit_log]
    assert isinstance(audit_log, AuditLog)
    assert audit_log.event_metadata == {
        "analysis_type": "activity_score",
        "nested": {"safe": "ok"},
    }
    assert audit_log.actor_subject_hash != "https://auth.example.com/::user_123"
    assert audit_log.ip_hash != "203.0.113.10"
    assert audit_log.user_agent_hash != "raw-test-agent"
    assert len(audit_log.record_hash) == 64


@pytest.mark.asyncio
async def test_delete_all_user_data_includes_p1_health_and_supplement_rows() -> None:
    """Verify all owner-scoped P1 rows are included in all-user-data deletion."""
    owner_subject = "https://auth.example.com/::user_123"
    now = datetime.now(UTC)
    supplement = UserSupplement(
        id=uuid4(),
        owner_subject=owner_subject,
        display_name="Vitamin C",
        serving_snapshot={"serving_size": "1 tablet"},
        intake_schedule={"daily_count": 1},
    )
    supplement_ingredient = UserSupplementIngredient(
        id=uuid4(),
        user_supplement_id=supplement.id,
        display_name="Vitamin C",
        amount=Decimal("500"),
        unit="mg",
        confidence=Decimal("1.0"),
        source="user_confirmed",
    )
    supplement_run = SupplementAnalysisRun(
        id=uuid4(),
        owner_subject=owner_subject,
        status="requires_confirmation",
        image_sha256="a" * 64,
        image_mime_type="image/png",
        image_size_bytes=1024,
        parsed_snapshot={"items": []},
        match_snapshot={"matches": []},
        warnings=[],
        algorithm_version="supplement-parser-v1",
        expires_at=now + timedelta(minutes=30),
    )
    health_summary = HealthDailySummary(
        id=uuid4(),
        owner_subject=owner_subject,
        measured_date=date(2026, 5, 12),
        source_platform="manual",
        steps=7000,
    )
    health_batch = HealthSyncBatch(
        id=uuid4(),
        owner_subject=owner_subject,
        client_batch_id="batch-123",
        source_platform="manual",
        record_count=1,
        accepted_count=1,
        rejected_count=0,
        input_snapshot={"source": "manual"},
        result_snapshot={"accepted": 1},
    )
    analysis_result = AnalysisResult(
        id=uuid4(),
        owner_subject=owner_subject,
        analysis_type="nutrition_analysis",
        algorithm_version="phase1-core-v1",
        input_snapshot={"meal": "sample"},
        result_snapshot={"score": 1},
    )
    consent_record = ConsentRecord(
        id=uuid4(),
        owner_subject=owner_subject,
        consent_type="sensitive_health_analysis",
        policy_version="2026-05-11",
        granted=True,
        occurred_at=now,
    )
    regulated_document = RegulatedDocument(
        id=uuid4(),
        owner_subject_hash="a" * 64,
        document_type="prescription",
        status="requires_confirmation",
        image_sha256="b" * 64,
        image_mime_type="image/png",
        image_size_bytes=1024,
        parsed_snapshot={"recognized_items": []},
        warning_codes=[],
        consult_cta={"type": "consult_professional"},
        algorithm_version="regulated-ocr-intake-v1.0.0",
        raw_image_deleted_at=now,
        expires_at=now + timedelta(minutes=30),
    )
    fake_session = _FakeDeletionSession(
        {
            HealthDailySummary: [health_summary],
            HealthSyncBatch: [health_batch],
            SupplementAnalysisRun: [supplement_run],
            UserSupplement: [supplement],
            UserSupplementIngredient: [supplement_ingredient],
            AnalysisResult: [analysis_result],
            RegulatedDocument: [regulated_document],
            ConsentRecord: [consent_record],
        }
    )
    settings = Settings(privacy_hash_secret=SecretStr("test-privacy-secret"))

    deletion_request = await create_delete_all_user_data_request(
        cast(AsyncSession, fake_session),
        _user(),
        _request(),
        settings,
    )

    assert fake_session.deleted == [
        supplement_ingredient,
        supplement,
        supplement_run,
        health_summary,
        health_batch,
        analysis_result,
        regulated_document,
        consent_record,
    ]
    assert isinstance(deletion_request, DeletionRequest)
    assert deletion_request.deleted_counts == {
        "analysis_results": 1,
        "consent_records": 1,
        "health_daily_summaries": 1,
        "health_sync_batches": 1,
        "image_embedding_jobs": 0,
        "image_embedding_records": 0,
        "learning_image_object_blobs": 0,
        "learning_image_object_delete_failures": 0,
        "learning_image_objects": 0,
        "regulated_documents": 1,
        "supplement_analysis_runs": 1,
        "user_supplement_ingredients": 1,
        "user_supplements": 1,
    }
    assert fake_session.added[0] is deletion_request
    assert isinstance(fake_session.added[1], AuditLog)
