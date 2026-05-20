"""Tests for the redacted ROI OCR impact evaluator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import evaluate_roi_ocr_impact as evaluate


def test_evaluate_manifest_reports_downstream_metric_deltas(tmp_path: Path) -> None:
    """Verify ROI impact evaluation compares downstream parser metrics."""
    manifest_path = tmp_path / "roi-impact.json"
    manifest_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "case-1",
                        "roi_available": True,
                        "original": {
                            "field_exact_match_rate": 0.5,
                            "numeric_exact_match_rate": 0.25,
                            "unit_exact_match_rate": 0.25,
                            "parser_success_rate": 0.0,
                        },
                        "roi_crop": {
                            "field_exact_match_rate": 0.75,
                            "numeric_exact_match_rate": 0.75,
                            "unit_exact_match_rate": 0.5,
                            "parser_success_rate": 1.0,
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = evaluate.evaluate_manifest(manifest_path)

    assert summary["case_count"] == 1
    assert summary["roi_available_cases"] == 1
    assert summary["average_metric_delta"] == {
        "field_exact_match_rate": 0.25,
        "numeric_exact_match_rate": 0.5,
        "unit_exact_match_rate": 0.25,
        "parser_success_rate": 1.0,
    }


def test_evaluate_manifest_rejects_raw_ocr_text(tmp_path: Path) -> None:
    """Verify raw OCR text cannot enter ROI impact reports."""
    manifest_path = tmp_path / "roi-impact.json"
    manifest_path.write_text(
        json.dumps({"cases": [{"case_id": "bad", "raw_ocr_text": "비타민 D"}]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="raw_ocr_text"):
        evaluate.evaluate_manifest(manifest_path)
