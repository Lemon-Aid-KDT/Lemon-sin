"""Tests for redacted supplement OCR observation collection helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from src.models.schemas.supplement_parser import SupplementStructuredParseResult

from scripts import collect_supplement_ocr_observations as collector


class _SuccessfulParser:
    """Fake local parser returning a schema-valid structured result."""

    async def parse_supplement_ocr_text(self, _ocr_text: str) -> SupplementStructuredParseResult:
        """Return a parser result using the current schema shape."""
        return SupplementStructuredParseResult.model_validate(
            {
                "parsed_product": {
                    "product_name": "테스트 비타민",
                    "serving_size": "1정",
                },
                "ingredient_candidates": [
                    {
                        "display_name": "비타민 D",
                        "amount": 1000,
                        "unit": "IU",
                        "confidence": 0.91,
                    }
                ],
            }
        )


@pytest.mark.asyncio
async def test_attach_llm_parse_records_schema_v2_candidates() -> None:
    """Verify LLM parse observations follow SupplementStructuredParseResult."""
    row: dict[str, object] = {}

    await collector._attach_llm_parse(
        row=row,
        ocr_result=collector.OCRResult(text="synthetic OCR text", provider="paddleocr_local"),
        llm_parser=_SuccessfulParser(),  # type: ignore[arg-type]
    )

    assert row["llm_parse_status"] == "completed"
    assert row["llm_parsed_ingredient_count"] == 1
    assert row["llm_parsed_ingredients"] == [
        {
            "display_name": "비타민 D",
            "nutrient_code": None,
            "amount": 1000.0,
            "unit": "IU",
            "confidence": 0.91,
            "source": "ollama_structured",
        }
    ]
    assert row["llm_parsed_product_name_present"] is True
    assert row["llm_parsed_serving_size_text_present"] is True

    serialized = json.dumps(row, ensure_ascii=False).lower()
    assert "raw_ocr_text" not in serialized
    assert "raw_model_response" not in serialized


def _write_manifest_with_image(
    tmp_path: Path,
    *,
    contains_personal_data: object,
) -> Path:
    """Write a minimal local OCR manifest and matching image bytes."""
    image_path = tmp_path / "review.jpg"
    image_path.write_bytes(b"not-real-image-but-sha-valid")
    manifest_path = tmp_path / "manifest.jsonl"
    row = {
        "fixture_id": "review-1",
        "image_path": str(image_path),
        "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
        "license_status": "team_approved",
        "consent_status": "team_approved",
        "section": "review",
        "contains_personal_data": contains_personal_data,
        "pii_screening_status": "pending_local_screening",
        "external_transfer_allowed": False,
        "local_processing_allowed": True,
        "expected": {},
    }
    manifest_path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest_path


def test_read_fixture_manifest_allows_review_local_pii_screening(tmp_path: Path) -> None:
    """Verify review rows pending PII screening are local PaddleOCR only."""
    manifest_path = _write_manifest_with_image(tmp_path, contains_personal_data=None)

    fixtures = collector._read_fixture_manifest(
        manifest_path,
        providers=("paddleocr_local",),
    )

    assert len(fixtures) == 1
    assert collector._requires_local_pii_screening(fixtures[0]) is True


def test_read_fixture_manifest_blocks_review_pii_for_external_provider(tmp_path: Path) -> None:
    """Verify pending review PII rows cannot be sent to external OCR providers."""
    manifest_path = _write_manifest_with_image(tmp_path, contains_personal_data=None)

    with pytest.raises(ValueError, match="local PII-screening only"):
        collector._read_fixture_manifest(
            manifest_path,
            providers=("clova_ocr",),
        )


def test_pii_candidate_flags_are_bounded_tokens() -> None:
    """Verify local PII screening records flag names, not matched text."""
    flags = collector._pii_candidate_flags(
        "주문번호 1234567890 / 010-1234-5678 / user@example.com / 서울로 12"
    )

    assert flags == [
        "email_candidate",
        "phone_candidate",
        "order_number_candidate",
        "address_candidate",
    ]
    serialized = json.dumps(flags, ensure_ascii=False)
    assert "010-1234-5678" not in serialized
    assert "user@example.com" not in serialized


def test_safe_error_code_preserves_google_status_without_details() -> None:
    """Verify provider error status is useful but bounded."""
    error = collector.OCRError("Google Vision OCR provider error: PERMISSION_DENIED")

    assert collector._safe_error_code(error) == "ocr_provider_error_permission_denied"


def test_safe_error_code_sanitizes_http_status() -> None:
    """Verify HTTP status is preserved without provider payload text."""
    error = collector.OCRError("Google Vision OCR request failed: status 403.")

    assert collector._safe_error_code(error) == "ocr_http_status_403"
