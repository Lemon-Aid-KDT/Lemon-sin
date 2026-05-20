"""Tests for Phase 0 supplement OCR baseline evaluation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import evaluate_supplement_ocr_baseline as evaluate

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "supplement_labels"


def test_evaluate_committed_manifest_validates_snapshots_and_storage_invariants() -> None:
    """Verify the committed Phase 0 manifest is valid and redacted."""
    summary = evaluate.evaluate_manifest(FIXTURE_ROOT / "manifest.json")

    assert summary["fixture_count"] == 6
    assert summary["image_fixture_count"] == 4
    assert summary["missing_image_count"] == 0
    assert summary["expected_snapshot_count"] == 6
    assert summary["expected_snapshot_valid_count"] == 6
    assert summary["expected_snapshot_v3_count"] == 6
    assert summary["expected_snapshot_v3_valid_count"] == 6
    assert summary["evidence_refs_dangling"] is False
    assert summary["missing_ocr_text_count"] == 0
    assert summary["raw_image_stored"] is False
    assert summary["raw_ocr_text_stored"] is False
    assert summary["raw_provider_payload_stored"] is False
    assert summary["raw_model_response_stored"] is False
    assert summary["confirmation_required_rate"] == 1.0


def test_evaluate_manifest_rejects_raw_ocr_text(tmp_path: Path) -> None:
    """Verify manifests cannot contain raw OCR text fields."""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": "test",
                "cases": [
                    {
                        "case_id": "bad",
                        "expected_snapshot_path": "expected.json",
                        "raw_ocr_text": "secret label text",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="raw_ocr_text"):
        evaluate.evaluate_manifest(manifest_path)


def test_evaluate_manifest_reports_field_exact_match_rate(tmp_path: Path) -> None:
    """Verify actual snapshots can be compared against expected snapshots."""
    expected = {
        "schema_version": "supplement-parsed-snapshot-v2",
        "requires_user_confirmation": True,
        "source": {
            "ocr_provider": "manual",
            "ocr_confidence": None,
            "layout_available": False,
            "raw_image_stored": False,
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
        },
        "product": {"product_name": "A"},
    }
    actual = {
        **expected,
        "product": {"product_name": "A"},
    }
    expected_v3 = {
        "schema_version": "supplement-parsed-snapshot-v3",
        "requires_user_confirmation": True,
        "source": {
            "ocr_provider": "manual",
            "ocr_confidence": None,
            "layout_available": False,
            "raw_image_stored": False,
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "raw_model_response_stored": False,
        },
        "product": {"product_name": "A"},
    }
    (tmp_path / "expected.json").write_text(
        json.dumps(expected, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "actual.json").write_text(
        json.dumps(actual, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "expected_v3.json").write_text(
        json.dumps(expected_v3, ensure_ascii=False),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": "test",
                "cases": [
                    {
                        "case_id": "case-1",
                        "image_path": None,
                        "image_required": False,
                        "expected_snapshot_path": "expected.json",
                        "expected_snapshot_v3_path": "expected_v3.json",
                        "actual_snapshot_path": "actual.json",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = evaluate.evaluate_manifest(manifest_path)

    assert summary["actual_snapshot_count"] == 1
    assert summary["field_exact_match_rate"] == 1.0
