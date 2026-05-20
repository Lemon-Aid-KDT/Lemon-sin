"""Tests for the supplement OCR validation gate evaluator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest

from scripts import evaluate_supplement_ocr_gate as evaluate

PROVIDERS = ("google_vision_document", "paddleocr_local", "clova_ocr")


def _summary(value: object) -> dict[str, Any]:
    """Cast evaluator summaries to JSON-like dictionaries for assertions.

    Args:
        value: Evaluator return value.

    Returns:
        Summary dictionary.
    """
    return cast(dict[str, Any], value)


def _write_manifest(path: Path, *, count: int = 12, bad_sha: bool = False) -> list[str]:
    """Write a safe OCR gate manifest.

    Args:
        path: Destination manifest path.
        count: Fixture row count.
        bad_sha: Whether to intentionally write the wrong checksum.

    Returns:
        Fixture ids.
    """
    image_bytes = b"public-consented-fixture-image"
    image_path = path.parent / "label.png"
    image_path.write_bytes(image_bytes)
    checksum = hashlib.sha256(b"wrong" if bad_sha else image_bytes).hexdigest()
    fixture_ids: list[str] = []
    cases: list[dict[str, object]] = []
    for index in range(count):
        fixture_id = f"fixture-{index:03d}"
        fixture_ids.append(fixture_id)
        cases.append(
            {
                "fixture_id": fixture_id,
                "image_path": "label.png",
                "image_sha256": checksum,
                "license_status": "synthetic",
                "consent_status": "not_required",
                "contains_personal_data": False,
                "labels": ["synthetic", "ko_en"],
                "expected": {
                    "expected_source": "human_verified_fixture",
                    "verification_status": "human_verified",
                    "ingredients": [{"name": "vitamin c", "amount": 500, "unit": "mg"}],
                },
            }
        )
    path.write_text(
        json.dumps({"version": "fixtures-v1", "cases": cases}, ensure_ascii=False),
        encoding="utf-8",
    )
    return fixture_ids


def _write_observations(
    path: Path,
    fixture_ids: list[str],
    *,
    providers: tuple[str, ...] = PROVIDERS,
    evidence_grounded: bool = True,
) -> None:
    """Write completed redacted observations.

    Args:
        path: Destination JSONL path.
        fixture_ids: Fixture ids.
        providers: Providers to include.
        evidence_grounded: Observation evidence-grounding flag.
    """
    rows: list[dict[str, object]] = []
    for fixture_id in fixture_ids:
        for provider in providers:
            rows.append(
                {
                    "fixture_id": fixture_id,
                    "provider": provider,
                    "status": "completed",
                    "latency_ms": 100,
                    "text_non_empty": True,
                    "text_hash": hashlib.sha256(fixture_id.encode()).hexdigest(),
                    "char_count": 32,
                    "layout_available": True,
                    "parser_success": True,
                    "parsed_ingredients": [{"name": "vitamin c", "amount": 500, "unit": "mg"}],
                    "evidence_grounded": evidence_grounded,
                    "warning_codes": [],
                }
            )
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_evaluate_gate_passes_report_only_with_three_provider_observations(
    tmp_path: Path,
) -> None:
    """Verify complete redacted observations produce passing fixture metrics."""
    manifest_path = tmp_path / "manifest.json"
    observation_path = tmp_path / "observations.jsonl"
    fixture_ids = _write_manifest(manifest_path)
    _write_observations(observation_path, fixture_ids)

    summary = _summary(
        evaluate.evaluate_gate(
            manifest_path=manifest_path,
            observations_path=observation_path,
            gate_mode="report_only",
        )
    )

    assert summary["gate_status"] == "passed"
    assert summary["release_blocked"] is False
    assert summary["candidate_metrics"]["text_non_empty_rate"] == 1.0
    assert summary["candidate_metrics"]["ingredient_name_exact_rate"] == 1.0
    assert summary["governance_report"]["pipeline"] == "supplement_ocr_gate"


def test_evaluate_gate_rejects_raw_ocr_text(tmp_path: Path) -> None:
    """Verify raw OCR text cannot enter observation artifacts."""
    manifest_path = tmp_path / "manifest.json"
    observation_path = tmp_path / "observations.jsonl"
    fixture_ids = _write_manifest(manifest_path)
    observation_path.write_text(
        json.dumps(
            {
                "fixture_id": fixture_ids[0],
                "provider": "google_vision_document",
                "status": "completed",
                "raw_ocr_text": "secret label text",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="raw_ocr_text"):
        evaluate.evaluate_gate(
            manifest_path=manifest_path,
            observations_path=observation_path,
            gate_mode="report_only",
        )


def test_evaluate_gate_rejects_image_checksum_mismatch(tmp_path: Path) -> None:
    """Verify committed fixture image checksums are enforced."""
    manifest_path = tmp_path / "manifest.json"
    observation_path = tmp_path / "observations.jsonl"
    fixture_ids = _write_manifest(manifest_path, bad_sha=True)
    _write_observations(observation_path, fixture_ids)

    with pytest.raises(ValueError, match="image_sha256 mismatch"):
        evaluate.evaluate_gate(
            manifest_path=manifest_path,
            observations_path=observation_path,
            gate_mode="report_only",
        )


def test_evaluate_gate_blocks_when_required_provider_missing(tmp_path: Path) -> None:
    """Verify block_release fails when a required provider was not observed."""
    manifest_path = tmp_path / "manifest.json"
    observation_path = tmp_path / "observations.jsonl"
    fixture_ids = _write_manifest(manifest_path)
    _write_observations(observation_path, fixture_ids, providers=("google_vision_document",))
    baseline_path = tmp_path / "baseline.json"
    baseline_summary = _summary(
        evaluate.evaluate_gate(
            manifest_path=manifest_path,
            observations_path=observation_path,
            gate_mode="report_only",
        )
    )
    baseline_path.write_text(json.dumps(baseline_summary), encoding="utf-8")

    summary = _summary(
        evaluate.evaluate_gate(
            manifest_path=manifest_path,
            observations_path=observation_path,
            gate_mode="block_release",
            baseline_report_path=baseline_path,
        )
    )

    assert summary["release_blocked"] is True
    assert "provider_observation_missing:paddleocr_local" in summary["reasons"]
    assert "safety_metric_nonzero:provider_not_run_count" in summary["reasons"]


def test_evaluate_gate_allows_no_regression_block_release(tmp_path: Path) -> None:
    """Verify equal baseline/candidate metrics pass the no-regression gate."""
    manifest_path = tmp_path / "manifest.json"
    observation_path = tmp_path / "observations.jsonl"
    baseline_path = tmp_path / "baseline.json"
    fixture_ids = _write_manifest(manifest_path)
    _write_observations(observation_path, fixture_ids)
    baseline_summary = _summary(
        evaluate.evaluate_gate(
            manifest_path=manifest_path,
            observations_path=observation_path,
            gate_mode="report_only",
        )
    )
    baseline_path.write_text(json.dumps(baseline_summary), encoding="utf-8")

    summary = _summary(
        evaluate.evaluate_gate(
            manifest_path=manifest_path,
            observations_path=observation_path,
            gate_mode="block_release",
            baseline_report_path=baseline_path,
        )
    )

    assert summary["gate_status"] == "passed"
    assert summary["release_blocked"] is False
    assert summary["reasons"] == []


def test_evaluate_gate_excludes_google_self_seeded_exact_metrics(tmp_path: Path) -> None:
    """Verify Google Vision auto seeds are treated as agreement baselines."""
    manifest_path = tmp_path / "manifest.json"
    observation_path = tmp_path / "observations.jsonl"
    fixture_ids = _write_manifest(manifest_path)
    parsed = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    for row in parsed["cases"]:
        row["expected"] = {
            "expected_source": "google_vision_auto_seed",
            "verification_status": "provisional",
            "seed_provider": "google_vision_document",
            "ingredients": [{"name": "vitamin c", "amount": 500, "unit": "mg"}],
        }
    manifest_path.write_text(json.dumps(parsed), encoding="utf-8")
    _write_observations(
        observation_path,
        fixture_ids,
        providers=("google_vision_document", "paddleocr_local"),
    )

    summary = _summary(
        evaluate.evaluate_gate(
            manifest_path=manifest_path,
            observations_path=observation_path,
            gate_mode="report_only",
            required_providers=("google_vision_document", "paddleocr_local"),
        )
    )

    google_metrics = summary["provider_metrics"]["google_vision_document"]
    paddle_metrics = summary["provider_metrics"]["paddleocr_local"]
    assert google_metrics["ingredient_name_exact_rate"] is None
    assert google_metrics["self_seeded_expected_excluded_count"] == 12
    assert paddle_metrics["ingredient_name_exact_rate"] == 1.0
    assert summary["candidate_metrics"]["ingredient_name_exact_rate"] == 1.0
    assert summary["provisional_expected_count"] == 12
    assert "agreement baselines" in summary["interpretation"]


def test_evaluate_gate_blocks_provisional_expected_in_block_release(tmp_path: Path) -> None:
    """Verify auto-seeded expected snapshots cannot become a release gate."""
    manifest_path = tmp_path / "manifest.json"
    observation_path = tmp_path / "observations.jsonl"
    baseline_path = tmp_path / "baseline.json"
    fixture_ids = _write_manifest(manifest_path)
    parsed = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    for row in parsed["cases"]:
        row["expected"]["expected_source"] = "google_vision_auto_seed"
        row["expected"]["verification_status"] = "provisional"
        row["expected"]["seed_provider"] = "google_vision_document"
    manifest_path.write_text(json.dumps(parsed), encoding="utf-8")
    _write_observations(observation_path, fixture_ids)
    baseline_summary = _summary(
        evaluate.evaluate_gate(
            manifest_path=manifest_path,
            observations_path=observation_path,
            gate_mode="report_only",
        )
    )
    baseline_path.write_text(json.dumps(baseline_summary), encoding="utf-8")

    summary = _summary(
        evaluate.evaluate_gate(
            manifest_path=manifest_path,
            observations_path=observation_path,
            gate_mode="block_release",
            baseline_report_path=baseline_path,
        )
    )

    assert summary["release_blocked"] is True
    assert "human_verified_expected_required" in summary["reasons"]
