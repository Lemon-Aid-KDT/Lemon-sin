"""Tests for the redacted parser/domain correction evaluator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from scripts import evaluate_domain_correction_rules as evaluate


def test_evaluate_manifest_reports_promotion_decision(tmp_path: Path) -> None:
    """Verify parser/domain correction reports promotion and metric deltas."""
    manifest_path = tmp_path / "domain-correction-metrics.json"
    manifest_path.write_text(
        json.dumps(
            {
                "baseline": {
                    "ingredient_field_exact_rate": 0.7,
                    "numeric_exact_rate": 0.7,
                    "unit_exact_rate": 0.7,
                    "nutrient_code_candidate_hit_rate": 0.7,
                    "parser_success_rate": 0.7,
                },
                "candidate": {
                    "ingredient_field_exact_rate": 0.8,
                    "numeric_exact_rate": 0.7,
                    "unit_exact_rate": 0.7,
                    "nutrient_code_candidate_hit_rate": 0.7,
                    "parser_success_rate": 0.7,
                    "fabricated_field_count": 0,
                    "false_correction_count": 0,
                    "raw_text_leak_count": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    summary = cast(dict[str, Any], evaluate.evaluate_manifest(manifest_path))

    assert summary["promotion"]["promotable"] is True
    assert summary["metric_delta"]["ingredient_field_exact_rate"] == pytest.approx(0.1)
    assert summary["safety_metrics"]["fabricated_field_count"] == 0.0


def test_evaluate_manifest_rejects_raw_ocr_text(tmp_path: Path) -> None:
    """Verify raw OCR text cannot enter parser/domain correction reports."""
    manifest_path = tmp_path / "domain-correction-metrics.json"
    manifest_path.write_text(
        json.dumps(
            {
                "baseline": {},
                "candidate": {},
                "raw_ocr_text": "Vitamin D 25 ug",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="raw_ocr_text"):
        evaluate.evaluate_manifest(manifest_path)
