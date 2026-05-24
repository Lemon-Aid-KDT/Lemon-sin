"""Tests for exporting approved Tampermonkey review rows to DB import candidates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import export_naver_tampermonkey_approved_db_import as approved_export


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    """Write JSONL test rows."""
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _review_row(**overrides: object) -> dict[str, object]:
    """Return a minimal review ingest row."""
    row: dict[str, object] = {
        "schema_version": "naver-tampermonkey-review-ingest-v1",
        "review_task_id": "d" * 64,
        "fixture_id": "naver-tm-detail-000001",
        "source": "naver_tampermonkey",
        "section": "detail",
        "image": {
            "root_token": "$NAVER_TAMPERMONKEY_SOURCE_ROOT",
            "image_ref_hash": "b" * 64,
            "image_sha256": "a" * 64,
        },
        "product": {
            "product_id": "1234567890",
            "product_dir_hash": "c" * 64,
        },
        "category_key": "omega_3",
        "category_display": {"ko": "오메가3", "en": "Omega-3"},
        "language_targets": ["ko", "en"],
        "chronic_fixture_tags": ["cardiovascular"],
        "caution_tags": ["anticoagulant_review"],
        "contains_personal_data": False,
        "pii_screening_status": "not_required_detail_page",
        "external_transfer_allowed": True,
        "local_processing_allowed": True,
        "requires_human_review": True,
        "is_clinical_recommendation": False,
        "clinical_recommendation_forbidden": True,
        "ocr_observation_count": 1,
        "ingredient_candidate_count": 1,
        "ingredient_candidates": [
            {
                "display_name": "오메가3",
                "nutrient_code": "omega_3",
                "amount": 1000.0,
                "unit": "mg",
                "confidence": 0.92,
                "source": "ollama_structured",
                "provider": "paddleocr_local",
            }
        ],
        "review_task": {
            "status": "needs_human_review",
            "priority": "normal",
            "reasons": ["llm_ingredient_candidates_available"],
            "db_import_ready": False,
            "blocked_reasons": ["human_review_required"],
        },
    }
    row.update(overrides)
    return row


def _decision(**overrides: object) -> dict[str, object]:
    """Return an approved human review decision."""
    row: dict[str, object] = {
        "status": "approved",
        "reviewer_id": "operator_1",
        "reviewed_at": "2026-05-24T14:30:00+09:00",
        "display_name": "Omega-3 1000",
        "manufacturer": "Reviewed Nutrition",
        "category_key": "omega_3",
        "attest_pii_screening_completed": True,
        "attest_no_raw_ocr_text": True,
        "attest_not_clinical_recommendation": True,
        "ingredients": [
            {
                "display_name": "Omega-3",
                "nutrient_code": "omega_3",
                "amount": 1000,
                "unit": "mg",
                "source": "human_reviewed",
            }
        ],
    }
    row.update(overrides)
    return row


def test_export_approved_review_rows_to_db_import_candidates(tmp_path: Path) -> None:
    """Verify only human-approved review rows become DB import candidates."""
    input_path = tmp_path / "review-ingest.jsonl"
    _write_jsonl(input_path, [_review_row(review_decision=_decision())])

    rows, summary = approved_export.export_approved_db_import_rows(input_path=input_path)

    assert summary["approved_row_count"] == 1
    assert summary["skipped_unapproved_count"] == 0
    assert rows[0]["schema_version"] == approved_export.SCHEMA_VERSION
    assert rows[0]["source_provider"] == "naver_tampermonkey_review"
    assert rows[0]["product_name"] == "Omega-3 1000"
    assert rows[0]["normalized_product_name"] == "omega-3 1000"
    assert rows[0]["category"] == "omega_3"
    assert rows[0]["is_clinical_recommendation"] is False
    assert rows[0]["clinical_recommendation_forbidden"] is True
    assert rows[0]["ingredients"] == [
        {
            "standard_name": "Omega-3",
            "nutrient_code": "omega_3",
            "amount": 1000.0,
            "unit": "mg",
            "source": "human_reviewed",
            "sort_order": 0,
            "source_payload": {
                "reviewer_id": "operator_1",
                "reviewed_at": "2026-05-24T14:30:00+09:00",
                "source_review_task_id": "d" * 64,
            },
        }
    ]
    assert rows[0]["import_gate"] == {
        "ready_for_db_import": True,
        "human_review_approved": True,
        "pii_screening_completed": True,
    }
    serialized = json.dumps(rows, ensure_ascii=False).lower()
    assert "raw_ocr_text" not in serialized
    assert "provider_payload" not in serialized
    assert "/volumes/" not in serialized


def test_export_skips_unapproved_rows_by_default(tmp_path: Path) -> None:
    """Verify unreviewed tasks do not become import candidates."""
    input_path = tmp_path / "review-ingest.jsonl"
    _write_jsonl(input_path, [_review_row()])

    rows, summary = approved_export.export_approved_db_import_rows(input_path=input_path)

    assert rows == []
    assert summary["input_row_count"] == 1
    assert summary["approved_row_count"] == 0
    assert summary["skipped_unapproved_count"] == 1


def test_export_can_require_all_rows_approved(tmp_path: Path) -> None:
    """Verify strict mode fails when review rows remain unapproved."""
    input_path = tmp_path / "review-ingest.jsonl"
    _write_jsonl(input_path, [_review_row()])

    with pytest.raises(ValueError, match="All review ingest rows"):
        approved_export.export_approved_db_import_rows(
            input_path=input_path,
            require_all_approved=True,
        )


def test_export_rejects_approved_rows_without_attestation(tmp_path: Path) -> None:
    """Verify approval cannot omit raw-text and PII safety attestations."""
    input_path = tmp_path / "review-ingest.jsonl"
    decision = _decision(attest_no_raw_ocr_text=False)
    _write_jsonl(input_path, [_review_row(review_decision=decision)])

    with pytest.raises(ValueError, match="attest_no_raw_ocr_text"):
        approved_export.export_approved_db_import_rows(input_path=input_path)


def test_export_rejects_uncleared_pii_rows_even_when_approved(tmp_path: Path) -> None:
    """Verify approved DB import still requires PII clearance."""
    input_path = tmp_path / "review-ingest.jsonl"
    _write_jsonl(
        input_path,
        [
            _review_row(
                section="review",
                contains_personal_data=None,
                pii_screening_status="pending_local_screening",
                review_decision=_decision(),
            )
        ],
    )

    with pytest.raises(ValueError, match="PII clearance"):
        approved_export.export_approved_db_import_rows(input_path=input_path)


def test_export_rejects_raw_and_local_path_literals(tmp_path: Path) -> None:
    """Verify unsafe payload fields cannot enter approved import rows."""
    input_path = tmp_path / "review-ingest.jsonl"
    _write_jsonl(
        input_path,
        [
            _review_row(
                review_decision=_decision(),
                raw_provider_payload={"text": "do not persist"},
            )
        ],
    )

    with pytest.raises(ValueError, match="raw_provider_payload"):
        approved_export.export_approved_db_import_rows(input_path=input_path)

    input_path_2 = tmp_path / "review-ingest-local-path.jsonl"
    _write_jsonl(
        input_path_2,
        [
            _review_row(
                review_decision=_decision(display_name="/Volumes/Corsair EX400U Media/a.jpg")
            )
        ],
    )

    with pytest.raises(ValueError, match="local path literal"):
        approved_export.export_approved_db_import_rows(input_path=input_path_2)
