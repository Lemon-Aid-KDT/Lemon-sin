"""Tests for cross-cutting governance schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.models.schemas.governance import (
    ArtifactProvenance,
    ConsentRetentionPolicySnapshot,
    RedactedEvaluationReport,
    reject_governance_raw_fields,
)


def test_governance_schema_rejects_nested_raw_ocr_text() -> None:
    """Verify governance payloads cannot contain raw OCR text."""
    with pytest.raises(ValueError, match="raw_ocr_text"):
        reject_governance_raw_fields({"reports": [{"raw_ocr_text": "Vitamin D 25 ug"}]})


def test_evaluation_report_rejects_user_identifier_key() -> None:
    """Verify direct identifier keys are rejected before report validation."""
    with pytest.raises(ValidationError, match="user_id"):
        RedactedEvaluationReport.model_validate(
            {
                "report_id": "report-001",
                "pipeline": "paddleocr_local",
                "frozen_fixture_version": "fixtures-v1",
                "split_version": "split-v1",
                "aggregate_case_count": 1,
                "baseline_metrics": {"numeric_exact_rate": 0.8},
                "candidate_metrics": {"numeric_exact_rate": 0.9},
                "safety_metrics": {"raw_text_leak_count": 0},
                "user_id": "not-allowed",
            }
        )


def test_policy_snapshot_validates_missing_consent_consistency() -> None:
    """Verify missing consent scopes must match required minus granted scopes."""
    with pytest.raises(ValidationError, match="missing_consent_scopes"):
        ConsentRetentionPolicySnapshot(
            required_consent_scopes=["ocr_image_processing", "data_retention"],
            granted_consent_scopes=["ocr_image_processing"],
            missing_consent_scopes=[],
        )


def test_artifact_provenance_rejects_non_http_source_doc_url() -> None:
    """Verify provenance documentation references must be explicit URLs."""
    with pytest.raises(ValidationError, match="source_doc_urls"):
        ArtifactProvenance(
            artifact_id="artifact-001",
            artifact_type="model",
            artifact_version="v1",
            source_doc_urls=["docs/local.md"],
        )


def test_evaluation_report_rejects_out_of_range_primary_metric() -> None:
    """Verify primary metrics are bounded rates."""
    with pytest.raises(ValidationError, match="Primary metric"):
        RedactedEvaluationReport(
            report_id="report-001",
            pipeline="paddleocr_local",
            frozen_fixture_version="fixtures-v1",
            split_version="split-v1",
            aggregate_case_count=1,
            baseline_metrics={"numeric_exact_rate": 0.8},
            candidate_metrics={"numeric_exact_rate": 1.2},
            safety_metrics={"raw_text_leak_count": 0},
        )
