"""Tests for barcode identity fixture evaluation report generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import evaluate_barcode_identity as evaluate


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
    """Verify barcode provider observations are aggregated without raw payloads."""
    manifest_path = tmp_path / "barcode_identity_cases.jsonl"
    _write_manifest(
        manifest_path,
        [
            {
                "fixture_id": "barcode-case-001",
                "source_rights": "public_or_team_consent",
                "barcode_text": "08801007325224",
                "observations": [
                    {
                        "provider": "foodqr",
                        "status": "matched",
                        "expected_status": "matched",
                        "item_count": 1,
                    },
                    {
                        "provider": "mfds_c003",
                        "status": "not_found",
                        "expected_status": "not_found",
                        "item_count": 0,
                    },
                ],
            }
        ],
    )

    summary = evaluate.evaluate_manifest(manifest_path)

    providers = summary["providers"]
    assert isinstance(providers, dict)
    foodqr_metrics = providers["foodqr"]
    assert isinstance(foodqr_metrics, dict)
    assert foodqr_metrics["calls"] == 1
    assert foodqr_metrics["matched_rate"] == 1.0
    assert foodqr_metrics["single_item_observation_count"] == 1
    assert foodqr_metrics["multi_item_observation_count"] == 0
    assert foodqr_metrics["max_item_count"] == 1
    assert foodqr_metrics["expected_status_match_rate"] == 1.0
    assert summary["fixture_count"] == 1
    assert summary["observation_count"] == 2
    assert summary["raw_provider_payload_stored"] is False
    assert summary["credentials_stored"] is False
    assert "not barcode accuracy" in str(summary["interpretation"])


def test_evaluate_manifest_rejects_raw_provider_payload(tmp_path: Path) -> None:
    """Verify raw provider payloads cannot enter report manifests."""
    manifest_path = tmp_path / "barcode_identity_cases.jsonl"
    _write_manifest(
        manifest_path,
        [
            {
                "fixture_id": "barcode-case-001",
                "observations": [{"provider": "foodqr", "raw_payload": {"secret": "value"}}],
            }
        ],
    )

    with pytest.raises(ValueError, match="raw_payload"):
        evaluate.evaluate_manifest(manifest_path)


def test_evaluate_manifest_rejects_credentials(tmp_path: Path) -> None:
    """Verify credentials cannot enter report manifests."""
    manifest_path = tmp_path / "barcode_identity_cases.jsonl"
    _write_manifest(
        manifest_path,
        [
            {
                "fixture_id": "barcode-case-001",
                "observations": [{"provider": "mfds_c003", "keyId": "secret"}],
            }
        ],
    )

    with pytest.raises(ValueError, match="keyId"):
        evaluate.evaluate_manifest(manifest_path)
