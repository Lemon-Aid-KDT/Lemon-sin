"""Supplement image intake API tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Self, cast
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from PIL import Image
from src.api.v1 import supplements
from src.config import Settings, get_settings
from src.db.dependencies import get_async_session
from src.main import create_app
from src.models.db.privacy import AuditLog
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.supplement import SupplementAnalysisStatus
from src.services.privacy import ConsentRequiredError
from src.services.supplement_image_analysis import SupplementImageAnalysisAdapters


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


class _FakeScalarResult:
    """Minimal scalar result wrapper for fake async session queries."""

    def __init__(self, rows: list[SupplementAnalysisRun]) -> None:
        """Store rows for later ``all`` retrieval.

        Args:
            rows: Supplement analysis rows returned by a fake query.
        """
        self._rows = rows

    def all(self) -> list[SupplementAnalysisRun]:
        """Return all fake rows.

        Returns:
            Stored supplement analysis rows.
        """
        return list(self._rows)


class _FakeSupplementSession:
    """Fake async session for supplement intake route tests."""

    def __init__(
        self,
        existing: SupplementAnalysisRun | None = None,
        finalize_runs: list[SupplementAnalysisRun] | None = None,
    ) -> None:
        self.existing = existing
        self.finalize_runs = finalize_runs or []
        self.added_analysis: SupplementAnalysisRun | None = None
        self.added_analyses: list[SupplementAnalysisRun] = []
        self.added_audits: list[AuditLog] = []
        self.committed = False
        # A real AsyncSession always exposes ``.info``; persist_scope reads it.
        self.info: dict[str, object] = {}

    async def flush(self) -> None:
        """No-op flush (persist_scope flushes pending writes)."""

    async def rollback(self) -> None:
        """No-op rollback (persist_scope own-mode rolls back on exception)."""

    def begin(self) -> _TransactionContext:
        """Return a fake transaction context.

        Returns:
            Fake async transaction context.
        """
        return _TransactionContext()

    def in_transaction(self) -> bool:
        """Return whether the fake session has an active implicit transaction.

        Returns:
            False because these tests do not model SQLAlchemy's implicit read transaction.
        """
        return False

    async def scalar(self, _statement: object) -> SupplementAnalysisRun | None:
        """Return a fake existing row for idempotency lookup.

        Args:
            _statement: SQLAlchemy select statement.

        Returns:
            Existing supplement analysis run or None.
        """
        return self.existing

    async def scalars(self, _statement: object) -> _FakeScalarResult:
        """Return fake rows for analysis-session lookups.

        Args:
            _statement: SQLAlchemy select statement.

        Returns:
            Fake scalar result with configured finalize rows.
        """
        return _FakeScalarResult([*self.finalize_runs, *self.added_analyses])

    def add(self, record: object) -> None:
        """Capture ORM records passed by route services.

        Args:
            record: ORM object passed by a service.

        Returns:
            None.
        """
        if isinstance(record, SupplementAnalysisRun):
            self.added_analysis = record
            self.added_analyses.append(record)
            return
        if isinstance(record, AuditLog):
            self.added_audits.append(record)

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

    async def commit(self) -> None:
        """Record an audit commit.

        Returns:
            None.
        """
        self.committed = True


def _png_bytes() -> bytes:
    """Return a tiny PNG image.

    Returns:
        PNG image bytes.
    """
    buffer = BytesIO()
    Image.new("RGB", (3, 2), color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _existing_run(image_sha256: str = "a" * 64) -> SupplementAnalysisRun:
    """Return an existing supplement analysis run fixture.

    Args:
        image_sha256: Stored image hash.

    Returns:
        Existing supplement analysis run.
    """
    now = datetime.now(UTC)
    return SupplementAnalysisRun(
        id=uuid4(),
        owner_subject="local-development::local-dev-user",
        client_request_id="client-1",
        status=SupplementAnalysisStatus.REQUIRES_CONFIRMATION.value,
        image_sha256=image_sha256,
        image_mime_type="image/png",
        image_size_bytes=128,
        ocr_provider="intake-only",
        parsed_snapshot={"parsed_product": {}, "ingredient_candidates": []},
        match_snapshot={"matched_product_candidates": []},
        warnings=[],
        algorithm_version="supplement-intake-v1.0.0",
        expires_at=now + timedelta(minutes=30),
        created_at=now,
        updated_at=now,
    )


def _multi_image_run(
    *,
    group_id: str,
    image_role: str,
    parsed_snapshot: dict[str, object],
    image_sha256: str,
) -> SupplementAnalysisRun:
    """Return a grouped supplement analysis run fixture.

    Args:
        group_id: Multi-image analysis group id.
        image_role: Role assigned to this image.
        parsed_snapshot: Sanitized parsed snapshot overrides.
        image_sha256: Stored image hash.

    Returns:
        Existing supplement analysis run with safe multi-image metadata.
    """
    record = _existing_run(image_sha256=image_sha256)
    snapshot = {
        "parsed_product": {},
        "ingredient_candidates": [],
        "label_sections": [],
        "evidence_spans": [],
        "multi_image_group_id": group_id,
        "image_role": image_role,
        "pipeline_metadata": {
            "intake_completed": True,
            "image_count": 2,
            "image_role": image_role,
            "ocr_provider": "paddleocr_local",
            "ocr_text_present": True,
            "raw_image_stored": False,
            "raw_ocr_text_stored": False,
        },
    }
    snapshot.update(parsed_snapshot)
    record.client_request_id = f"client-{image_role}"
    record.ocr_provider = "paddleocr_local"
    record.ocr_text_hash = "c" * 64
    record.parsed_snapshot = snapshot
    return record


def _session_dependency(
    fake_session: _FakeSupplementSession,
) -> Callable[[], AsyncIterator[object]]:
    """Build a FastAPI dependency override yielding a fake session.

    Args:
        fake_session: Fake session to yield.

    Returns:
        Dependency callable.
    """

    async def dependency() -> AsyncIterator[object]:
        """Yield the fake session.

        Yields:
            Fake session object.
        """
        yield fake_session

    return dependency


async def _allow_consent(*_args: object, **_kwargs: object) -> None:
    """No-op consent dependency for route tests.

    Args:
        *_args: Positional call arguments.
        **_kwargs: Keyword call arguments.

    Returns:
        None.
    """


async def _deny_consent(*_args: object, **_kwargs: object) -> None:
    """Raise a missing-consent service error.

    Args:
        *_args: Positional call arguments.
        **_kwargs: Keyword call arguments.

    Returns:
        None.

    Raises:
        ConsentRequiredError: Always raised for this test.
    """
    raise ConsentRequiredError("OCR image processing consent is required.")


async def _record_noop_audit(*_args: object, **_kwargs: object) -> None:
    """No-op audit writer for error-path route tests.

    Args:
        *_args: Positional call arguments.
        **_kwargs: Keyword call arguments.

    Returns:
        None.
    """


def _empty_analysis_adapters() -> SupplementImageAnalysisAdapters:
    """Return an adapter bundle with OCR intentionally disabled for route tests.

    Returns:
        Empty supplement image analysis adapter bundle.
    """
    return SupplementImageAnalysisAdapters()


def _settings(
    *,
    supplement_image_max_bytes: int = 5 * 1024 * 1024,
    supplement_image_max_pixels: int = 12_000_000,
    supplement_preview_ttl_minutes: int = 30,
) -> Settings:
    """Return settings for route tests.

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
        ocr_primary_provider="paddleocr",
        allow_external_ocr=False,
        enable_clova_ocr=False,
        enable_local_ocr=True,
    )


def test_analyze_supplement_label_accepts_valid_png_and_stores_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify supplement analyze performs image intake and returns a preview."""
    fake_session = _FakeSupplementSession()
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    app.dependency_overrides[supplements.get_supplement_image_analysis_adapters] = (
        _empty_analysis_adapters
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", _png_bytes(), "image/png")},
        data={"client_request_id": "client-1"},
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert fake_session.added_analysis is not None
    assert fake_session.added_analysis.owner_subject == "local-development::local-dev-user"
    stored_idempotency_key = fake_session.added_analysis.client_request_id
    assert stored_idempotency_key is not None
    prefix, sep, suffix = stored_idempotency_key.partition(":")
    assert sep == ":"
    assert len(prefix) == 16
    assert all(char in "0123456789abcdef" for char in prefix)
    assert suffix == "client-1"
    assert fake_session.added_analysis.ocr_text_hash is None
    assert fake_session.added_analysis.parsed_snapshot["ingredient_candidates"] == []
    assert len(fake_session.added_audits) == 1
    body = response.json()
    assert body["status"] == "requires_confirmation"
    assert body["ingredient_candidates"] == []
    assert body["algorithm_version"] == "supplement-intake-v1.0.0"


def test_analyze_supplement_label_multi_accepts_roles_and_returns_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify multi-image intake preserves per-image previews and safe batch metadata."""
    fake_session = _FakeSupplementSession()
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    app.dependency_overrides[supplements.get_supplement_image_analysis_adapters] = (
        _empty_analysis_adapters
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze-multi",
        files=[
            ("images", ("front.png", _png_bytes(), "image/png")),
            ("images", ("facts.png", _png_bytes(), "image/png")),
        ],
        data={"image_roles": ["front_label", "intake_method"]},
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert len(fake_session.added_analyses) == 2
    body = response.json()
    assert body["analysis_group_id"].startswith("multi-")
    assert body["image_count"] == 2
    assert body["pipeline_metadata"]["image_count"] == 2
    assert body["pipeline_metadata"]["image_role"] == "mixed"
    assert body["pipeline_metadata"]["raw_image_stored"] is False
    assert body["pipeline_metadata"]["raw_ocr_text_stored"] is False
    assert body["previews"][0]["image_role"] == "front_label"
    assert body["previews"][1]["image_role"] == "intake_method"
    assert body["previews"][0]["multi_image_group_id"] == body["analysis_group_id"]
    assert body["previews"][1]["pipeline_metadata"]["image_count"] == 2
    assert body["merged_preview"]["multi_image_group_id"] == body["analysis_group_id"]
    assert body["merged_preview"]["image_role"] == "mixed"
    assert body["merged_preview"]["pipeline_metadata"]["image_count"] == 2
    assert body["merged_preview"]["missing_required_sections"] == [
        "product_name",
        "supplement_facts",
        "precautions",
    ]
    assert body["missing_required_sections"] == [
        "product_name",
        "supplement_facts",
        "precautions",
    ]
    assert body["action_required"] == "additional_label_image_required"
    assert all("ocr_text" not in preview for preview in body["previews"])
    assert "ocr_text" not in body["merged_preview"]


def test_analyze_supplement_label_multi_accepts_json_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify mobile clients can send role lists as a JSON form field."""
    fake_session = _FakeSupplementSession()
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    app.dependency_overrides[supplements.get_supplement_image_analysis_adapters] = (
        _empty_analysis_adapters
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze-multi",
        files=[
            ("images", ("front.png", _png_bytes(), "image/png")),
            ("images", ("facts.png", _png_bytes(), "image/png")),
        ],
        data={"image_roles_json": '["front_label","supplement_facts"]'},
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    body = response.json()
    assert body["previews"][0]["image_role"] == "front_label"
    assert body["previews"][1]["image_role"] == "supplement_facts"
    assert body["merged_preview"]["image_role"] == "mixed"


def test_analyze_supplement_label_multi_rejects_role_count_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify multi-image role metadata must align one-to-one with uploads."""
    fake_session = _FakeSupplementSession()
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    app.dependency_overrides[supplements.get_supplement_image_analysis_adapters] = (
        _empty_analysis_adapters
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze-multi",
        files=[
            ("images", ("front.png", _png_bytes(), "image/png")),
            ("images", ("facts.png", _png_bytes(), "image/png")),
        ],
        data={"image_roles": ["front_label"]},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"]["code"] == "image_role_count_mismatch"
    assert fake_session.added_analyses == []


def test_create_supplement_analysis_session_returns_upload_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify session create returns a safe group id before any image is uploaded."""
    fake_session = _FakeSupplementSession()
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post("/api/v1/supplements/analysis-sessions")

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["analysis_group_id"].startswith("multi-")
    assert body["status"] == "created"
    assert body["image_count"] == 0
    assert body["max_images"] == 6
    assert body["missing_required_sections"] == [
        "product_name",
        "supplement_facts",
        "intake_method",
        "precautions",
    ]
    assert body["action_required"] == "additional_label_image_required"
    assert len(fake_session.added_audits) == 1


def test_upload_supplement_analysis_session_image_returns_current_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a session image upload stores role metadata and returns the group preview."""
    fake_session = _FakeSupplementSession()
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    app.dependency_overrides[supplements.get_supplement_image_analysis_adapters] = (
        _empty_analysis_adapters
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analysis-sessions/multi-test/images",
        files={"image": ("facts.png", _png_bytes(), "image/png")},
        data={
            "image_role": "supplement_facts",
            "client_request_id": "image-1",
            "ocr_provider": "configured",
        },
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert len(fake_session.added_analyses) == 1
    stored = fake_session.added_analyses[0]
    assert stored.client_request_id is not None
    assert stored.client_request_id.endswith(":multi-test:image-1")
    assert stored.parsed_snapshot["multi_image_group_id"] == "multi-test"
    assert stored.parsed_snapshot["image_role"] == "supplement_facts"
    body = response.json()
    assert body["analysis_group_id"] == "multi-test"
    assert body["image_count"] == 1
    assert body["previews"][0]["image_role"] == "supplement_facts"
    assert body["previews"][0]["pipeline_metadata"]["image_count"] == 1
    assert body["merged_preview"]["multi_image_group_id"] == "multi-test"
    assert "ocr_text" not in body["previews"][0]


def test_finalize_supplement_analysis_session_returns_merged_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a persisted multi-image batch can be finalized into one safe preview."""
    group_id = "multi-test"
    front = _multi_image_run(
        group_id=group_id,
        image_role="front_label",
        image_sha256="a" * 64,
        parsed_snapshot={
            "parsed_product": {"product_name": "테스트 비타민"},
            "label_sections": [
                {
                    "section_id": "front",
                    "section_type": "unknown",
                    "heading_text": "front",
                    "text_bundle": "제품명 확인",
                    "confidence": 0.8,
                    "evidence_refs": ["front-name"],
                }
            ],
            "evidence_spans": [
                {
                    "span_id": "front-name",
                    "source_type": "ocr_layout",
                    "section_type": "unknown",
                    "text_excerpt": "제품명 확인",
                    "confidence": 0.8,
                }
            ],
        },
    )
    facts = _multi_image_run(
        group_id=group_id,
        image_role="supplement_facts",
        image_sha256="b" * 64,
        parsed_snapshot={
            "ingredient_candidates": [
                {
                    "display_name": "비타민 C",
                    "amount": 500,
                    "unit": "mg",
                    "confidence": 0.86,
                    "source": "ocr_layout",
                }
            ],
            "label_sections": [
                {
                    "section_id": "facts",
                    "section_type": "supplement_facts",
                    "heading_text": "Supplement Facts",
                    "text_bundle": "성분표 확인",
                    "confidence": 0.86,
                    "evidence_refs": ["facts-vitamin-c"],
                },
                {
                    "section_id": "intake",
                    "section_type": "intake_method",
                    "heading_text": "섭취 방법",
                    "text_bundle": "섭취 방법 확인",
                    "confidence": 0.82,
                    "evidence_refs": ["facts-intake"],
                },
                {
                    "section_id": "precautions",
                    "section_type": "precautions",
                    "heading_text": "주의사항",
                    "text_bundle": "주의사항 확인",
                    "confidence": 0.8,
                    "evidence_refs": ["facts-precaution"],
                },
            ],
            "intake_method": {
                "text": "섭취 방법 확인",
                "confidence": 0.82,
                "evidence_refs": ["facts-intake"],
            },
            "precautions": [
                {
                    "text": "주의사항 확인",
                    "category": "unknown",
                    "severity": "warning",
                    "confidence": 0.8,
                    "evidence_refs": ["facts-precaution"],
                }
            ],
            "evidence_spans": [
                {
                    "span_id": "facts-vitamin-c",
                    "source_type": "ocr_layout",
                    "section_type": "supplement_facts",
                    "text_excerpt": "성분표 확인",
                    "confidence": 0.86,
                },
                {
                    "span_id": "facts-intake",
                    "source_type": "ocr_layout",
                    "section_type": "intake_method",
                    "text_excerpt": "섭취 방법 확인",
                    "confidence": 0.82,
                },
                {
                    "span_id": "facts-precaution",
                    "source_type": "ocr_layout",
                    "section_type": "precautions",
                    "text_excerpt": "주의사항 확인",
                    "confidence": 0.8,
                },
            ],
        },
    )
    fake_session = _FakeSupplementSession(finalize_runs=[front, facts])
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post(f"/api/v1/supplements/analysis-sessions/{group_id}/finalize")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["analysis_group_id"] == group_id
    assert body["image_count"] == 2
    assert body["missing_required_sections"] == []
    assert body["action_required"] == "review_required"
    assert body["pipeline_metadata"]["image_count"] == 2
    assert body["pipeline_metadata"]["image_role"] == "mixed"
    assert body["merged_preview"]["multi_image_group_id"] == group_id
    assert body["merged_preview"]["image_role"] == "mixed"
    assert body["merged_preview"]["parsed_product"]["product_name"] == "테스트 비타민"
    assert body["merged_preview"]["ingredient_candidates"][0]["display_name"] == "비타민 C"
    assert body["merged_preview"]["intake_method"]["text"] == "섭취 방법 확인"
    assert "ocr_text" not in body["merged_preview"]


def test_finalize_supplement_analysis_session_returns_404_for_missing_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify finalize fails closed when the current user has no such group."""
    fake_session = _FakeSupplementSession(finalize_runs=[])
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post("/api/v1/supplements/analysis-sessions/missing/finalize")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"]["code"] == "analysis_session_not_found"


def test_analyze_supplement_label_requires_ocr_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify supplement image intake fails closed without OCR consent."""
    fake_session = _FakeSupplementSession()
    settings = _settings()
    monkeypatch.setattr(supplements, "require_user_consent", _deny_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", _png_bytes(), "image/png")},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["code"] == "consent_required"
    assert response.json()["detail"]["required_consents"] == ["ocr_image_processing"]


def test_analyze_supplement_label_rejects_media_type_spoofing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify content-type and image bytes must agree."""
    fake_session = _FakeSupplementSession()
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.jpg", _png_bytes(), "image/jpeg")},
    )

    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert response.json()["detail"]["code"] == "unsupported_media_type"
    assert fake_session.added_analysis is None


def test_analyze_supplement_label_rejects_oversized_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify supplement image byte limits are enforced through settings."""
    fake_session = _FakeSupplementSession()
    settings = _settings(supplement_image_max_bytes=1024)
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", b"x" * 1025, "image/png")},
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert response.json()["detail"]["code"] == "payload_too_large"
    assert fake_session.added_analysis is None


def test_analyze_supplement_label_rejects_idempotency_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a client idempotency key cannot be reused for another image."""
    fake_session = _FakeSupplementSession(existing=_existing_run(image_sha256="b" * 64))
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    monkeypatch.setattr(supplements, "record_sensitive_audit_event", _record_noop_audit)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/supplements/analyze",
        files={"image": ("label.png", _png_bytes(), "image/png")},
        data={"client_request_id": "client-1"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"]["code"] == "idempotency_conflict"
    assert fake_session.added_analysis is None
