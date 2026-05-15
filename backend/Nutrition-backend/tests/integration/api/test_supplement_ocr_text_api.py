"""Supplement OCR text parsing API tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Self
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from src.api.v1 import supplements
from src.db.dependencies import get_async_session
from src.llm.ollama import OllamaClientError, OllamaStructuredOutputError
from src.main import create_app
from src.models.db.privacy import AuditLog
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.supplement import SupplementAnalysisStatus
from src.models.schemas.supplement_parser import SupplementStructuredParseResult
from src.services.privacy import ConsentRequiredError
from src.services.supplement_parser import (
    SupplementAnalysisExpiredError,
    SupplementAnalysisNotFoundError,
    SupplementParserInputError,
    SupplementParserStoreResult,
)


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


class _FakeSupplementOCRTextSession:
    """Fake async session for OCR text route tests."""

    def __init__(self) -> None:
        self.added_audits: list[AuditLog] = []
        self.committed = False

    def begin(self) -> _TransactionContext:
        """Return a fake transaction context.

        Returns:
            Fake async transaction context.
        """
        return _TransactionContext()

    def add(self, record: object) -> None:
        """Capture audit rows passed by route services.

        Args:
            record: ORM object passed by a service.

        Returns:
            None.
        """
        if isinstance(record, AuditLog):
            self.added_audits.append(record)

    async def commit(self) -> None:
        """Record that the fake session was committed.

        Returns:
            None.
        """
        self.committed = True


def _session_dependency(
    fake_session: _FakeSupplementOCRTextSession,
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


def _analysis_run(analysis_id: UUID) -> SupplementAnalysisRun:
    """Return a parsed supplement analysis preview.

    Args:
        analysis_id: Analysis identifier.

    Returns:
        Supplement analysis run fixture.
    """
    now = datetime.now(UTC)
    return SupplementAnalysisRun(
        id=analysis_id,
        owner_subject="local-development::local-dev-user",
        client_request_id="client-1",
        status=SupplementAnalysisStatus.REQUIRES_CONFIRMATION.value,
        image_sha256="a" * 64,
        image_mime_type="image/png",
        image_size_bytes=128,
        ocr_provider="manual",
        ocr_confidence=Decimal("0.91"),
        ocr_text_hash="b" * 64,
        parsed_snapshot={
            "parsed_product": {
                "product_name": "비타민 D 1000",
                "serving_size": "1 tablet",
                "daily_servings": 1,
            },
            "ingredient_candidates": [
                {
                    "display_name": "비타민 D",
                    "amount": 25,
                    "unit": "ug",
                    "confidence": 0.91,
                    "source": "ollama_structured",
                }
            ],
            "low_confidence_fields": ["manufacturer"],
            "parser_metadata": {
                "raw_ocr_text_stored": False,
                "raw_model_response_stored": False,
            },
            "intake": {"mime_type": "image/png", "size_bytes": 128},
        },
        match_snapshot={"matched_product_candidates": []},
        warnings=["Structured OCR parsing is a preview. Review every field."],
        algorithm_version="supplement-ollama-parser-v1.0.0",
        source_manifest_version=None,
        expires_at=now + timedelta(minutes=30),
        created_at=now,
        updated_at=now,
    )


def _parse_result() -> SupplementStructuredParseResult:
    """Return a valid structured parser result.

    Returns:
        Structured supplement parse result fixture.
    """
    return SupplementStructuredParseResult.model_validate(
        {
            "parsed_product": {
                "product_name": "비타민 D 1000",
                "serving_size": "1 tablet",
                "daily_servings": 1,
            },
            "ingredient_candidates": [
                {
                    "display_name": "비타민 D",
                    "amount": 25,
                    "unit": "ug",
                    "confidence": 0.91,
                }
            ],
            "low_confidence_fields": ["manufacturer"],
            "warnings": [],
        }
    )


def _client(
    fake_session: _FakeSupplementOCRTextSession,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    """Return a test client with shared route overrides.

    Args:
        fake_session: Fake async session.
        monkeypatch: Pytest monkeypatch helper.

    Returns:
        Configured FastAPI TestClient.
    """
    monkeypatch.setattr(supplements, "require_user_consent", _allow_consent)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    return TestClient(app)


def _payload() -> dict[str, object]:
    """Return a valid OCR text parse request payload.

    Returns:
        JSON payload.
    """
    return {
        "ocr_text": "비타민 D 1000\n1정당 비타민 D 25 ug",
        "ocr_provider": "manual",
        "ocr_confidence": 0.91,
    }


def test_parse_supplement_ocr_text_returns_confirmation_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify OCR text parsing returns a sanitized preview and audit metadata."""
    fake_session = _FakeSupplementOCRTextSession()
    analysis_id = uuid4()
    received: dict[str, Any] = {}

    async def fake_parse_supplement_analysis_ocr_text(**kwargs: Any) -> SupplementParserStoreResult:
        """Capture route arguments and return a parsed preview.

        Args:
            **kwargs: Route-provided parser service arguments.

        Returns:
            Parser store result.
        """
        received.update(kwargs)
        record = _analysis_run(kwargs["analysis_id"])
        return SupplementParserStoreResult(record=record, parse_result=_parse_result())

    monkeypatch.setattr(
        supplements,
        "parse_supplement_analysis_ocr_text",
        fake_parse_supplement_analysis_ocr_text,
    )
    client = _client(fake_session, monkeypatch)

    response = client.post(f"/api/v1/supplements/analyses/{analysis_id}/ocr-text", json=_payload())

    assert response.status_code == status.HTTP_200_OK
    assert received["analysis_id"] == analysis_id
    assert received["ocr_text"] == "비타민 D 1000\n1정당 비타민 D 25 ug"
    assert received["ocr_provider"] == "manual"
    body = response.json()
    assert body["analysis_id"] == str(analysis_id)
    assert body["status"] == "requires_confirmation"
    assert body["parsed_product"]["product_name"] == "비타민 D 1000"
    assert body["ingredient_candidates"][0]["display_name"] == "비타민 D"
    assert "ocr_text" not in str(body)
    assert len(fake_session.added_audits) == 1
    audit_metadata = fake_session.added_audits[0].event_metadata
    assert audit_metadata["raw_ocr_text_stored"] is False
    assert audit_metadata["raw_llm_response_stored"] is False
    assert audit_metadata["parser_provider"] == "ollama"
    assert audit_metadata["schema_valid"] is True
    assert "ocr_text" not in audit_metadata


def test_parse_supplement_ocr_text_requires_ocr_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify OCR text parsing fails closed without OCR image processing consent."""
    fake_session = _FakeSupplementOCRTextSession()
    monkeypatch.setattr(supplements, "require_user_consent", _deny_consent)
    app = create_app()
    app.dependency_overrides[get_async_session] = _session_dependency(fake_session)
    client = TestClient(app)

    response = client.post(f"/api/v1/supplements/analyses/{uuid4()}/ocr-text", json=_payload())

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["code"] == "consent_required"
    assert response.json()["detail"]["required_consents"] == ["ocr_image_processing"]
    assert len(fake_session.added_audits) == 1
    assert fake_session.added_audits[0].event_metadata["missing_consent"] == "ocr_image_processing"


@pytest.mark.parametrize(
    ("exception", "expected_status", "expected_code"),
    (
        (SupplementParserInputError("OCR text is empty."), 422, "invalid_ocr_text"),
        (
            SupplementAnalysisNotFoundError("Supplement analysis preview was not found."),
            404,
            "supplement_analysis_not_found",
        ),
        (
            SupplementAnalysisExpiredError("Supplement analysis preview has expired."),
            409,
            "supplement_analysis_not_parseable",
        ),
        (OllamaClientError("Local Ollama Chat API request failed."), 502, "parser_unavailable"),
        (
            OllamaStructuredOutputError(
                "Ollama structured supplement output failed schema validation."
            ),
            502,
            "parser_schema_invalid",
        ),
    ),
)
def test_parse_supplement_ocr_text_maps_service_errors(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    expected_status: int,
    expected_code: str,
) -> None:
    """Verify service exceptions map to stable API error codes."""
    fake_session = _FakeSupplementOCRTextSession()

    async def fake_parse_supplement_analysis_ocr_text(
        **_kwargs: Any,
    ) -> SupplementParserStoreResult:
        """Raise a configured parser service error.

        Args:
            **_kwargs: Ignored service call arguments.

        Raises:
            Exception: Configured route error.
        """
        raise exception

    monkeypatch.setattr(
        supplements,
        "parse_supplement_analysis_ocr_text",
        fake_parse_supplement_analysis_ocr_text,
    )
    client = _client(fake_session, monkeypatch)

    response = client.post(f"/api/v1/supplements/analyses/{uuid4()}/ocr-text", json=_payload())

    assert response.status_code == expected_status
    assert response.json()["detail"]["code"] == expected_code
    assert len(fake_session.added_audits) == 1
    assert fake_session.added_audits[0].event_metadata["raw_ocr_text_stored"] is False
    assert fake_session.added_audits[0].event_metadata["raw_llm_response_stored"] is False
    assert "ocr_text" not in fake_session.added_audits[0].event_metadata


def test_parse_supplement_ocr_text_rejects_invalid_request_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify request validation rejects invalid provider metadata before parsing."""
    fake_session = _FakeSupplementOCRTextSession()
    client = _client(fake_session, monkeypatch)

    response = client.post(
        f"/api/v1/supplements/analyses/{uuid4()}/ocr-text",
        json={
            "ocr_text": "비타민 D",
            "ocr_provider": "manual",
            "ocr_confidence": 1.5,
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert fake_session.added_audits == []
