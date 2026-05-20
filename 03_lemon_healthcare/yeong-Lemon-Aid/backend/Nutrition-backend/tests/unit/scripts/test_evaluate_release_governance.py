"""Tests for the release governance evaluation script."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from src.services.governance import GovernanceGateError

from scripts import evaluate_release_governance as evaluate


def _manifest(*, rollback_to: str | None = "artifact-000") -> dict[str, Any]:
    """Build a redacted release-governance script manifest.

    Args:
        rollback_to: Optional rollback target artifact id.

    Returns:
        Manifest dictionary.
    """
    return {
        "target_environment": "staging",
        "release_target": "public_staging",
        "gate_mode": "block_release",
        "policy_snapshot": {
            "required_consent_scopes": [],
            "granted_consent_scopes": [],
            "missing_consent_scopes": [],
        },
        "evaluation_reports": [
            {
                "report_id": "report-001",
                "pipeline": "parser_domain_correction",
                "frozen_fixture_version": "fixtures-v1",
                "split_version": "split-v1",
                "aggregate_case_count": 5,
                "baseline_metrics": {
                    "downstream_field_exact_rate": 0.8,
                    "numeric_exact_rate": 0.7,
                    "unit_exact_rate": 0.75,
                    "parser_success_rate": 0.85,
                },
                "candidate_metrics": {
                    "downstream_field_exact_rate": 0.82,
                    "numeric_exact_rate": 0.7,
                    "unit_exact_rate": 0.75,
                    "parser_success_rate": 0.85,
                },
                "safety_metrics": {
                    "fabricated_field_count": 0,
                    "false_correction_count": 0,
                    "raw_text_leak_count": 0,
                    "raw_data_leak_count": 0,
                },
                "artifact_provenance": [
                    {
                        "artifact_id": "artifact-001",
                        "artifact_type": "rule",
                        "artifact_version": "v1",
                        "artifact_checksum": "artifact-checksum",
                        "dataset_checksum": "dataset-checksum",
                        "config_checksum": "config-checksum",
                        "code_commit": "abcdef123456",
                        "source_doc_urls": [
                            "https://docs.pydantic.dev/latest/concepts/validators/"
                        ],
                        "metrics_summary": {"downstream_field_exact_rate": 0.82},
                        "approval_status": "approved",
                        "approved_by": "ml-review-board",
                        "rollback_to": rollback_to,
                    }
                ],
                "source_doc_urls": ["https://www.nist.gov/itl/ai-risk-management-framework"],
            }
        ],
    }


def test_evaluate_manifest_reports_passed_governance(tmp_path: Path) -> None:
    """Verify a valid release governance manifest passes."""
    manifest_path = tmp_path / "governance.json"
    manifest_path.write_text(
        json.dumps(_manifest(), ensure_ascii=False),
        encoding="utf-8",
    )

    summary = cast(dict[str, Any], evaluate.evaluate_manifest(manifest_path))

    assert summary["overall_status"] == "passed"
    assert summary["pipeline_statuses"][1]["promotion"]["promotable"] is True


def test_evaluate_manifest_rejects_raw_ocr_text(tmp_path: Path) -> None:
    """Verify script input cannot contain raw OCR text."""
    payload = _manifest()
    payload["raw_ocr_text"] = "Vitamin D 25 ug"
    manifest_path = tmp_path / "governance.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(GovernanceGateError, match="raw_ocr_text"):
        evaluate.evaluate_manifest(manifest_path)


def test_evaluate_manifest_blocks_missing_rollback_target(tmp_path: Path) -> None:
    """Verify missing rollback target prevents promotion in block-release mode."""
    manifest_path = tmp_path / "governance.json"
    manifest_path.write_text(
        json.dumps(_manifest(rollback_to=None), ensure_ascii=False),
        encoding="utf-8",
    )

    summary = cast(dict[str, Any], evaluate.evaluate_manifest(manifest_path))

    assert summary["overall_status"] == "blocked"
    assert "rollback_target_missing:artifact-001" in summary["pipeline_statuses"][1]["reasons"]


def test_render_markdown_omits_raw_artifacts() -> None:
    """Verify rendered Markdown states the privacy posture without raw payloads."""
    markdown = evaluate._render_markdown(
        {
            "generated_at": "2026-05-17T00:00:00+00:00",
            "target_environment": "staging",
            "release_target": "public_staging",
            "gate_mode": "report_only",
            "overall_status": "warning",
            "pipeline_statuses": [],
        }
    )

    assert "Raw OCR text stored: `false`" in markdown
    assert "raw_ocr_text" not in markdown
