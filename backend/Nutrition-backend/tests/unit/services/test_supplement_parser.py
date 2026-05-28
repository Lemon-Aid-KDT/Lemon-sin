"""Supplement OCR parser service tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import Settings
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.label_layout import LabelLayout
from src.models.schemas.supplement import SupplementAnalysisStatus
from src.models.schemas.supplement_parser import SupplementStructuredParseResult
from src.security.auth import AuthenticatedUser
from src.services.supplement_intake import supplement_analysis_run_to_preview
from src.services.supplement_parser import (
    SupplementAnalysisExpiredError,
    SupplementAnalysisNotFoundError,
    SupplementParserConflictError,
    SupplementParserInputError,
    hash_ocr_text,
    normalize_ocr_text,
    parse_supplement_analysis_ocr_text,
)


class _FakeParser:
    """Fake parser adapter for service tests."""

    def __init__(self, result: SupplementStructuredParseResult) -> None:
        self.result = result
        self.received_text: str | None = None

    async def parse_supplement_ocr_text(
        self,
        ocr_text: str,
    ) -> SupplementStructuredParseResult:
        """Capture OCR text and return a configured structured result.

        Args:
            ocr_text: OCR text passed by the service.

        Returns:
            Configured structured parse result.
        """
        self.received_text = ocr_text
        return self.result


class _FakeParserSession:
    """Fake async session for parser service tests."""

    def __init__(self, record: SupplementAnalysisRun | None) -> None:
        self.record = record
        self.committed = False
        self.refreshed: SupplementAnalysisRun | None = None

    async def scalar(self, _statement: object) -> SupplementAnalysisRun | None:
        """Return the configured analysis row.

        Args:
            _statement: SQLAlchemy select statement.

        Returns:
            Configured supplement analysis row or None.
        """
        return self.record

    async def commit(self) -> None:
        """Record a fake commit.

        Returns:
            None.
        """
        self.committed = True

    async def refresh(self, record: object) -> None:
        """Record the refreshed analysis row.

        Args:
            record: ORM object being refreshed.

        Returns:
            None.
        """
        self.refreshed = cast(SupplementAnalysisRun, record)


def _settings() -> Settings:
    """Return parser service test settings.

    Returns:
        Settings object.
    """
    return Settings(privacy_hash_secret=SecretStr("test-privacy-secret"))


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


def _analysis_run(
    *,
    analysis_id: UUID | None = None,
    expires_at: datetime | None = None,
    ocr_text_hash: str | None = None,
) -> SupplementAnalysisRun:
    """Return an owned supplement analysis row fixture.

    Args:
        analysis_id: Optional analysis row identifier.
        expires_at: Optional expiration time.
        ocr_text_hash: Optional stored OCR text hash.

    Returns:
        Supplement analysis run fixture.
    """
    now = datetime.now(UTC)
    return SupplementAnalysisRun(
        id=analysis_id or uuid4(),
        owner_subject="https://auth.example.com/::user_123",
        client_request_id="client-1",
        status=SupplementAnalysisStatus.REQUIRES_CONFIRMATION.value,
        image_sha256="a" * 64,
        image_mime_type="image/png",
        image_size_bytes=128,
        ocr_provider="intake-only",
        ocr_text_hash=ocr_text_hash,
        parsed_snapshot={
            "parsed_product": {},
            "ingredient_candidates": [],
            "low_confidence_fields": ["label_text"],
            "intake": {"mime_type": "image/png", "size_bytes": 128},
        },
        match_snapshot={"matched_product_candidates": []},
        warnings=[],
        algorithm_version="supplement-intake-v1.0.0",
        expires_at=expires_at or now + timedelta(minutes=30),
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
            "label_sections": [
                {
                    "section_id": "section-1",
                    "section_type": "supplement_facts",
                    "heading_text": "Supplement Facts",
                    "text_bundle": "Vitamin D 25 ug",
                    "confidence": 0.9,
                    "requires_review": False,
                    "evidence_refs": ["span-1"],
                }
            ],
            "intake_method": {
                "text": "1일 1정 섭취",
                "structured": {
                    "frequency": "daily",
                    "times_per_day": 1,
                    "amount_per_time": 1,
                    "amount_unit": "tablet",
                    "time_of_day": [],
                    "with_food": "unknown",
                },
                "confidence": 0.82,
                "requires_review": True,
                "evidence_refs": ["span-2"],
            },
            "precautions": [
                {
                    "text": "임산부는 전문가와 상담",
                    "category": "pregnancy",
                    "severity": "caution",
                    "confidence": 0.8,
                    "requires_review": True,
                    "evidence_refs": ["span-3"],
                }
            ],
            "functional_claims": [
                {
                    "text": "뼈 건강에 도움",
                    "claim_type": "label_claim",
                    "confidence": 0.77,
                    "requires_review": True,
                    "evidence_refs": ["span-4"],
                }
            ],
            "evidence_spans": [
                {
                    "span_id": "span-1",
                    "source_type": "ocr",
                    "section_type": "supplement_facts",
                    "text_excerpt": "Vitamin D 25 ug",
                    "confidence": 0.9,
                },
                {
                    "span_id": "span-2",
                    "source_type": "ocr",
                    "section_type": "intake_method",
                    "text_excerpt": "1일 1정 섭취",
                    "confidence": 0.82,
                },
            ],
            "missing_required_sections": ["precautions"],
            "low_confidence_fields": ["manufacturer"],
            "warnings": ["제조사명은 확인이 필요합니다."],
        }
    )


def _minimal_parse_result() -> SupplementStructuredParseResult:
    """Return parser output with no parser-provided layout sections."""
    return SupplementStructuredParseResult.model_validate(
        {
            "parsed_product": {"product_name": "비타민 D 1000"},
            "ingredient_candidates": [
                {
                    "display_name": "비타민 D",
                    "amount": 25,
                    "unit": "ug",
                    "confidence": 0.91,
                }
            ],
            "missing_required_sections": ["supplement_facts", "intake_method"],
            "low_confidence_fields": [],
            "warnings": [],
        }
    )


def _label_layout() -> LabelLayout:
    """Return deterministic OCR layout with facts and intake sections."""
    return LabelLayout.model_validate(
        {
            "provider": "fake-ocr",
            "page_count": 1,
            "sections": [
                {
                    "section_type": "nutrition_function_info",
                    "anchor_text": "Supplement Facts",
                    "anchor_box": {
                        "page_index": 0,
                        "left": 10,
                        "top": 10,
                        "right": 200,
                        "bottom": 40,
                    },
                    "rows": [
                        [
                            {
                                "row_index": 0,
                                "column_index": 0,
                                "text": "Supplement Facts",
                                "bounding_box": {
                                    "page_index": 0,
                                    "left": 10,
                                    "top": 10,
                                    "right": 200,
                                    "bottom": 40,
                                },
                                "confidence": 0.9,
                                "word_count": 1,
                            }
                        ],
                        [
                            {
                                "row_index": 1,
                                "column_index": 0,
                                "text": "Vitamin D",
                                "bounding_box": {
                                    "page_index": 0,
                                    "left": 10,
                                    "top": 50,
                                    "right": 140,
                                    "bottom": 80,
                                },
                                "confidence": 0.92,
                                "word_count": 1,
                            },
                            {
                                "row_index": 1,
                                "column_index": 1,
                                "text": "25 ug",
                                "bounding_box": {
                                    "page_index": 0,
                                    "left": 170,
                                    "top": 50,
                                    "right": 230,
                                    "bottom": 80,
                                },
                                "confidence": 0.9,
                                "word_count": 1,
                            },
                        ],
                    ],
                },
                {
                    "section_type": "intake_method",
                    "anchor_text": "섭취방법",
                    "anchor_box": {
                        "page_index": 0,
                        "left": 10,
                        "top": 100,
                        "right": 110,
                        "bottom": 130,
                    },
                    "rows": [
                        [
                            {
                                "row_index": 0,
                                "column_index": 0,
                                "text": "섭취방법 1일 1정",
                                "bounding_box": {
                                    "page_index": 0,
                                    "left": 10,
                                    "top": 100,
                                    "right": 220,
                                    "bottom": 130,
                                },
                                "confidence": 0.86,
                                "word_count": 1,
                            }
                        ]
                    ],
                },
            ],
            "warnings": [],
        }
    )


@pytest.mark.asyncio
async def test_parse_supplement_analysis_ocr_text_updates_preview_without_raw_text() -> None:
    """Verify parser output is stored as a sanitized preview snapshot."""
    record = _analysis_run()
    fake_session = _FakeParserSession(record)
    fake_parser = _FakeParser(_parse_result())
    settings = _settings()

    result = await parse_supplement_analysis_ocr_text(
        cast(AsyncSession, fake_session),
        _user(),
        record.id,
        " 비타민 D 1000\r\n1 tablet당 비타민 D 25 ug ",
        " manual-test ",
        0.91,
        settings,
        parser=fake_parser,
    )

    assert result.record is record
    assert result.parse_result.parsed_product.product_name == "비타민 D 1000"
    assert fake_parser.received_text == "비타민 D 1000\n1 tablet당 비타민 D 25 ug"
    assert fake_session.committed is True
    assert fake_session.refreshed is record
    assert record.ocr_provider == "manual-test"
    assert record.ocr_confidence == Decimal("0.91")
    assert record.ocr_text_hash is not None
    assert record.ocr_text_hash != "비타민 D 1000\n1 tablet당 비타민 D 25 ug"
    assert len(record.ocr_text_hash) == 64
    assert record.algorithm_version == "supplement-ollama-parser-v1.0.0"
    assert record.parsed_snapshot["parsed_product"]["product_name"] == "비타민 D 1000"
    assert record.parsed_snapshot["ingredient_candidates"][0]["source"] == "ollama_structured"
    assert record.parsed_snapshot["layout_available"] is True
    assert record.parsed_snapshot["label_sections"][0]["section_type"] == "supplement_facts"
    assert record.parsed_snapshot["intake_method"]["text"] == "1일 1정 섭취"
    assert record.parsed_snapshot["precautions"][0]["category"] == "pregnancy"
    assert record.parsed_snapshot["functional_claims"][0]["claim_type"] == "label_claim"
    assert record.parsed_snapshot["evidence_spans"][0]["text_excerpt"] == "Vitamin D 25 ug"
    assert record.parsed_snapshot["missing_required_sections"] == ["precautions"]
    assert record.parsed_snapshot["parser_metadata"]["raw_ocr_text_stored"] is False
    assert record.parsed_snapshot["parser_metadata"]["raw_model_response_stored"] is False
    assert record.parsed_snapshot["parser_metadata"]["input_provider"] == "manual-test"
    assert "ocr_text" not in record.parsed_snapshot
    assert record.parsed_snapshot["intake"] == {"mime_type": "image/png", "size_bytes": 128}
    assert record.warnings[0].startswith("Structured OCR parsing is a preview")
    preview = supplement_analysis_run_to_preview(record)
    assert preview.layout_available is True
    assert preview.label_sections[0].section_type == "supplement_facts"
    assert preview.intake_method.text == "1일 1정 섭취"
    assert preview.precautions[0].category == "pregnancy"
    assert preview.functional_claims[0].text == "뼈 건강에 도움"
    assert preview.evidence_spans[0].span_id == "span-1"
    assert preview.missing_required_sections == ["precautions"]


@pytest.mark.asyncio
async def test_parse_supplement_analysis_ocr_text_flags_low_ocr_confidence() -> None:
    """Verify low OCR confidence is surfaced as a user-review field."""
    record = _analysis_run()
    fake_session = _FakeParserSession(record)

    await parse_supplement_analysis_ocr_text(
        cast(AsyncSession, fake_session),
        _user(),
        record.id,
        "비타민 D 1000",
        "manual-test",
        0.79,
        _settings(),
        parser=_FakeParser(_parse_result()),
    )

    assert record.ocr_confidence == Decimal("0.79")
    assert record.parsed_snapshot["low_confidence_fields"] == ["manufacturer", "ocr_text"]


@pytest.mark.asyncio
async def test_parse_supplement_analysis_ocr_text_merges_deterministic_layout() -> None:
    """Verify provider layout becomes bounded section evidence without raw OCR storage."""
    record = _analysis_run()
    fake_session = _FakeParserSession(record)

    await parse_supplement_analysis_ocr_text(
        cast(AsyncSession, fake_session),
        _user(),
        record.id,
        "비타민 D 1000\nVitamin D 25 ug\n섭취방법 1일 1정",
        "fake-ocr",
        0.91,
        _settings(),
        ocr_layout=_label_layout(),
        parser=_FakeParser(_minimal_parse_result()),
    )

    assert record.parsed_snapshot["layout_available"] is True
    assert record.parsed_snapshot["parser_metadata"]["layout_provider"] == "fake-ocr"
    assert record.parsed_snapshot["parser_metadata"]["layout_page_count"] == 1
    assert [section["section_type"] for section in record.parsed_snapshot["label_sections"]] == [
        "supplement_facts",
        "intake_method",
    ]
    assert record.parsed_snapshot["label_sections"][0]["evidence_refs"] == ["layout-span-1"]
    assert record.parsed_snapshot["evidence_spans"][-1]["source_type"] == "ocr_layout"
    assert record.parsed_snapshot["evidence_spans"][-1]["cell_ref"] == "layout-section-2"
    assert record.parsed_snapshot["missing_required_sections"] == []
    assert "ocr_text" not in record.parsed_snapshot


@pytest.mark.asyncio
async def test_parse_supplement_analysis_ocr_text_marks_vision_assist_input() -> None:
    """Verify vision-assist candidates stay identifiable as fallback preview input."""
    record = _analysis_run()
    fake_session = _FakeParserSession(record)

    await parse_supplement_analysis_ocr_text(
        cast(AsyncSession, fake_session),
        _user(),
        record.id,
        "비타민 D 1000",
        "ollama_vision_assist",
        None,
        _settings(),
        parser=_FakeParser(_parse_result()),
    )

    assert record.ocr_provider == "ollama_vision_assist"
    assert record.parsed_snapshot["parser_metadata"]["input_provider"] == "ollama_vision_assist"
    assert any("Image-assisted text extraction" in warning for warning in record.warnings)


@pytest.mark.asyncio
async def test_parse_supplement_analysis_ocr_text_rejects_missing_owned_preview() -> None:
    """Verify parsing fails closed when the analysis row is not owner-visible."""
    fake_session = _FakeParserSession(None)

    with pytest.raises(SupplementAnalysisNotFoundError):
        await parse_supplement_analysis_ocr_text(
            cast(AsyncSession, fake_session),
            _user(),
            uuid4(),
            "비타민 D",
            "manual-test",
            None,
            _settings(),
            parser=_FakeParser(_parse_result()),
        )

    assert fake_session.committed is False


@pytest.mark.asyncio
async def test_parse_supplement_analysis_ocr_text_rejects_expired_preview() -> None:
    """Verify expired previews are not sent to the LLM parser."""
    record = _analysis_run(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    fake_parser = _FakeParser(_parse_result())

    with pytest.raises(SupplementAnalysisExpiredError):
        await parse_supplement_analysis_ocr_text(
            cast(AsyncSession, _FakeParserSession(record)),
            _user(),
            record.id,
            "비타민 D",
            "manual-test",
            None,
            _settings(),
            parser=fake_parser,
        )

    assert fake_parser.received_text is None


@pytest.mark.asyncio
async def test_parse_supplement_analysis_ocr_text_rejects_hash_conflict() -> None:
    """Verify a preview cannot be rebound to different OCR text."""
    record = _analysis_run(ocr_text_hash="b" * 64)
    fake_parser = _FakeParser(_parse_result())

    with pytest.raises(SupplementParserConflictError):
        await parse_supplement_analysis_ocr_text(
            cast(AsyncSession, _FakeParserSession(record)),
            _user(),
            record.id,
            "비타민 D",
            "manual-test",
            None,
            _settings(),
            parser=fake_parser,
        )

    assert fake_parser.received_text is None


def test_normalize_ocr_text_rejects_blank_or_oversized_text() -> None:
    """Verify OCR text input is bounded before the LLM adapter is invoked."""
    with pytest.raises(SupplementParserInputError):
        normalize_ocr_text(" \r\n ", 100)

    with pytest.raises(SupplementParserInputError):
        normalize_ocr_text("x" * 101, 100)


def test_hash_ocr_text_depends_on_privacy_secret() -> None:
    """Verify OCR fingerprints are keyed HMACs rather than raw hashes."""
    first = hash_ocr_text("비타민 D", SecretStr("first-secret"))
    second = hash_ocr_text("비타민 D", SecretStr("second-secret"))

    assert first != second
    assert len(first) == 64
    assert len(second) == 64
