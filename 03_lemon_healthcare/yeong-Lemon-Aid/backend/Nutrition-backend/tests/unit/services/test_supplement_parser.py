"""Supplement OCR parser service tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import Settings
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.parser_domain_correction import (
    DomainCorrectionArtifactManifest,
    DomainCorrectionRule,
)
from src.models.schemas.supplement import SupplementAnalysisStatus
from src.models.schemas.supplement_layout_context import (
    SupplementLayoutCellEvidenceV1,
    SupplementLayoutContextSectionV1,
    SupplementLayoutContextV1,
)
from src.models.schemas.supplement_parser import (
    StructuredParseResultLike,
    SupplementStructuredParseResultV2,
)
from src.security.auth import AuthenticatedUser
from src.services.parser_domain_correction import with_domain_correction_artifact_checksum
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

    def __init__(self, result: StructuredParseResultLike) -> None:
        self.result = result
        self.received_text: str | None = None

    async def parse_supplement_ocr_text(
        self,
        ocr_text: str,
    ) -> StructuredParseResultLike:
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


def _parse_result() -> SupplementStructuredParseResultV2:
    """Return a valid structured parser result.

    Returns:
        Structured supplement parse result fixture.
    """
    return SupplementStructuredParseResultV2.model_validate(
        {
            "schema_version": "supplement-parser-output-v2",
            "product": {
                "product_name": "비타민 D 1000",
            },
            "serving": {
                "serving_size_text": "1 tablet",
                "daily_servings": 1,
            },
            "ingredients": [
                {
                    "display_name": "비타민 D",
                    "amount": 25,
                    "unit": "ug",
                    "confidence": 0.91,
                    "evidence_refs": ["span:ingredient:0"],
                }
            ],
            "evidence_spans": [
                {
                    "span_id": "span:ingredient:0",
                    "source_type": "ocr_text",
                    "section_type": "nutrition_info",
                    "text_excerpt": "비타민 D 25 ug",
                }
            ],
            "low_confidence_fields": ["manufacturer"],
            "warnings": ["제조사명은 확인이 필요합니다."],
        }
    )


def _layout_context() -> SupplementLayoutContextV1:
    """Return a valid layout context fixture.

    Returns:
        Layout context fixture with request-local parser input.
    """
    return SupplementLayoutContextV1(
        provider="google_vision_document",
        layout_available=True,
        parser_input_text=(
            "[section:nutrition_info section_id=sec-000 source=nutrition_function_info "
            "confidence=0.9000]\n"
            "row=0 | col=0 cell=sec-000:r000:c000: 영양·기능정보"
        ),
        sections=[
            SupplementLayoutContextSectionV1(
                section_id="sec-000",
                section_type="nutrition_info",
                source_section_type="nutrition_function_info",
                heading_text="영양·기능정보",
                text_bundle="row=0 | col=0 cell=sec-000:r000:c000: 영양·기능정보",
                confidence=0.9,
                requires_review=False,
                evidence_refs=["layout:sec-000:r000:c000"],
                row_count=1,
                cell_count=1,
            )
        ],
        evidence_spans=[
            SupplementLayoutCellEvidenceV1(
                span_id="layout:sec-000:r000:c000",
                section_id="sec-000",
                section_type="nutrition_info",
                page_index=0,
                row_index=0,
                column_index=0,
                cell_ref="sec-000:r000:c000",
                text_excerpt="영양·기능정보",
                confidence=0.9,
            )
        ],
        low_confidence_sections=[],
        low_confidence_fields=[],
        warnings=["layout_warning_fixture"],
        fallback_reason=None,
    )


def _domain_correction_artifact_path(tmp_path: Path) -> Path:
    """Write a reviewed parser/domain correction artifact.

    Args:
        tmp_path: Pytest temporary directory.

    Returns:
        Artifact path.
    """
    artifact = with_domain_correction_artifact_checksum(
        DomainCorrectionArtifactManifest(
            domain_dictionary_version="domain-dict-v1",
            confusion_map_version="confusion-map-v1",
            created_from_manifest_checksum="manifest-checksum",
            rules=[
                DomainCorrectionRule(
                    rule_id="rule-vitd-alias",
                    rule_status="approved",
                    correction_type="ingredient_alias",
                    field_path="ingredients.display_name",
                    match_value="Vitarnin D",
                    replacement_value="Vitamin D",
                    canonical_display_name="Vitamin D",
                    nutrient_code="vitamin_d_ug",
                ),
                DomainCorrectionRule(
                    rule_id="rule-microgram-unit",
                    rule_status="approved",
                    correction_type="unit_normalization",
                    field_path="ingredients.unit",
                    match_value="㎍",
                    replacement_value="ug",
                ),
            ],
        )
    )
    path = tmp_path / "domain-correction.json"
    path.write_text(
        json.dumps(artifact.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    return path


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
    assert result.parse_result.product.product_name == "비타민 D 1000"
    assert fake_parser.received_text == "비타민 D 1000\n1 tablet당 비타민 D 25 ug"
    assert fake_session.committed is True
    assert fake_session.refreshed is record
    assert record.ocr_provider == "manual-test"
    assert record.ocr_confidence == Decimal("0.91")
    assert record.ocr_text_hash is not None
    assert record.ocr_text_hash != "비타민 D 1000\n1 tablet당 비타민 D 25 ug"
    assert len(record.ocr_text_hash) == 64
    assert record.algorithm_version == "supplement-ollama-parser-v1.0.0"
    assert record.parsed_snapshot["schema_version"] == "supplement-parsed-snapshot-v3"
    assert record.parsed_snapshot["product"]["product_name"] == "비타민 D 1000"
    assert record.parsed_snapshot["serving"]["serving_size_text"] == "1 tablet"
    assert record.parsed_snapshot["ingredients"][0]["source"] == "ocr_llm_preview"
    assert (
        record.parsed_snapshot["ingredients"][0]["nutrient_code_candidates"][0]["nutrient_code"]
        == "VITD"
    )
    assert record.parsed_snapshot["source"]["ocr_provider"] == "manual"
    assert record.parsed_snapshot["source"]["raw_ocr_text_stored"] is False
    assert record.parsed_snapshot["source"]["raw_model_response_stored"] is False
    assert "ocr_text" not in record.parsed_snapshot
    assert "intake" not in record.parsed_snapshot
    assert record.warnings[0].startswith("Structured OCR parsing is a preview")


@pytest.mark.asyncio
async def test_parse_supplement_analysis_ocr_text_applies_reviewed_domain_correction(
    tmp_path: Path,
) -> None:
    """Verify reviewed parser/domain rules improve candidates without raw text storage."""
    record = _analysis_run()
    fake_session = _FakeParserSession(record)
    fake_parser = _FakeParser(
        SupplementStructuredParseResultV2.model_validate(
            {
                "schema_version": "supplement-parser-output-v2",
                "serving": {"daily_servings": 1},
                "ingredients": [
                    {
                        "display_name": "Vitarnin D",
                        "amount": 25,
                        "unit": "㎍",
                        "confidence": 0.6,
                        "evidence_refs": ["span:ingredient:0"],
                    }
                ],
                "evidence_spans": [
                    {
                        "span_id": "span:ingredient:0",
                        "source_type": "ocr_text",
                        "section_type": "nutrition_info",
                        "text_excerpt": "Vitarnin D 25 ㎍",
                    }
                ],
            }
        )
    )
    settings = Settings(
        _env_file=None,
        privacy_hash_secret=SecretStr("test-privacy-secret"),
        enable_parser_domain_correction=True,
        parser_domain_correction_mode="apply_reviewed",
        parser_domain_correction_artifact_path=_domain_correction_artifact_path(tmp_path),
    )

    await parse_supplement_analysis_ocr_text(
        cast(AsyncSession, fake_session),
        _user(),
        record.id,
        "Vitarnin D 25 ㎍",
        "manual-test",
        0.8,
        settings,
        parser=fake_parser,
    )

    ingredient = record.parsed_snapshot["ingredients"][0]
    assert ingredient["display_name"] == "Vitarnin D"
    assert ingredient["unit"] == "ug"
    assert ingredient["daily_unit"] == "ug"
    assert ingredient["nutrient_code_candidates"][0]["nutrient_code"] == "vitamin_d_ug"
    assert record.parsed_snapshot["domain_correction_audit"][0]["action"] == "applied"
    assert "raw_ocr_text" not in record.parsed_snapshot


@pytest.mark.asyncio
async def test_parse_supplement_analysis_ocr_text_uses_layout_parser_input() -> None:
    """Verify sectioned layout input is sent to parser without storing it raw."""
    record = _analysis_run()
    fake_session = _FakeParserSession(record)
    fake_parser = _FakeParser(_parse_result())
    layout_context = _layout_context()

    await parse_supplement_analysis_ocr_text(
        cast(AsyncSession, fake_session),
        _user(),
        record.id,
        "원본 OCR 텍스트",
        "google_vision_document",
        0.91,
        _settings(),
        parser=fake_parser,
        parser_input_text=layout_context.parser_input_text,
        layout_context=layout_context,
    )

    assert fake_parser.received_text is not None
    assert fake_parser.received_text.startswith("[section:nutrition_info")
    assert record.ocr_text_hash == hash_ocr_text("원본 OCR 텍스트", _settings().privacy_hash_secret)
    assert record.parsed_snapshot["source"]["layout_available"] is True
    assert record.parsed_snapshot["layout_context"]["layout_available"] is True
    assert "parser_input_text" not in record.parsed_snapshot["layout_context"]
    assert record.parsed_snapshot["label_sections"][0]["section_type"] == "nutrition_info"
    assert record.parsed_snapshot["evidence_spans"][1]["source_type"] == "label_layout"
    assert "layout_warning_fixture" in record.parsed_snapshot["warnings"]
    assert "layout_warning_fixture" in record.warnings


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
async def test_parse_supplement_analysis_ocr_text_uses_configured_confidence_threshold() -> None:
    """Verify OCR review fields follow the runtime confidence threshold."""
    record = _analysis_run()
    fake_session = _FakeParserSession(record)
    settings = Settings(
        privacy_hash_secret=SecretStr("test-privacy-secret"),
        ocr_confidence_threshold=0.70,
    )

    await parse_supplement_analysis_ocr_text(
        cast(AsyncSession, fake_session),
        _user(),
        record.id,
        "비타민 D 1000",
        "manual-test",
        0.80,
        settings,
        parser=_FakeParser(_parse_result()),
    )

    assert record.ocr_confidence == Decimal("0.8")
    assert record.parsed_snapshot["low_confidence_fields"] == ["manufacturer"]


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
    assert record.parsed_snapshot["source"]["ocr_provider"] == "ollama_vision_assist"
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
