"""Tests for OCR 3-tier fixture evaluation report generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import evaluate_ocr_three_tier as evaluate


def _write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    """Write a JSONL manifest.

    Args:
        path: Destination path.
        rows: Manifest rows.
    """
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_evaluate_manifest_returns_redacted_provider_metrics(tmp_path: Path) -> None:
    """Verify provider observations are aggregated without raw artifacts."""
    manifest_path = tmp_path / "manifest.jsonl"
    _write_manifest(
        manifest_path,
        [
            {
                "fixture_id": "fixture-1",
                "image_path": "images/missing.png",
                "expected": {"ingredients": [{"name": "vitamin c"}]},
                "observations": [
                    {
                        "provider": "google_vision_document",
                        "latency_ms": 100,
                        "text_non_empty": True,
                        "parser_success": True,
                        "parsed_ingredients": [{"name": "vitamin c"}],
                    }
                ],
            }
        ],
    )

    summary = evaluate.evaluate_manifest(manifest_path)

    providers = summary["providers"]
    assert isinstance(providers, dict)
    google_metrics = providers["google_vision_document"]
    assert isinstance(google_metrics, dict)
    assert google_metrics["calls"] == 1
    assert google_metrics["text_non_empty_rate"] == 1.0
    assert google_metrics["ingredient_name_exact_rate"] == 1.0
    assert summary["missing_image_count"] == 1
    assert summary["raw_artifacts_stored"] is False
    assert summary["raw_ocr_text_stored"] is False


def test_evaluate_manifest_rejects_raw_ocr_text(tmp_path: Path) -> None:
    """Verify raw OCR text cannot enter report manifests."""
    manifest_path = tmp_path / "manifest.jsonl"
    _write_manifest(
        manifest_path,
        [
            {
                "fixture_id": "fixture-1",
                "observations": [{"provider": "google_vision_document", "raw_ocr_text": "secret"}],
            }
        ],
    )

    with pytest.raises(ValueError, match="raw_ocr_text"):
        evaluate.evaluate_manifest(manifest_path)
