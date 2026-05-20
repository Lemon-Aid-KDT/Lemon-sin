"""Tests for cross-cutting governance gate helpers."""

from __future__ import annotations

from pydantic import SecretStr
from src.config import Settings
from src.models.schemas.governance import (
    ArtifactProvenance,
    ConsentRetentionPolicySnapshot,
    RedactedEvaluationReport,
)
from src.models.schemas.privacy import ConsentType
from src.services.governance import (
    build_consent_retention_policy_snapshot,
    build_governance_readiness_component,
    evaluate_policy_snapshot,
    evaluate_promotion_decision,
    evaluate_release_governance_manifest,
)


def _artifact(**overrides: object) -> ArtifactProvenance:
    """Build a valid approved artifact provenance record.

    Args:
        overrides: Field overrides.

    Returns:
        Artifact provenance.
    """
    payload: dict[str, object] = {
        "artifact_id": "artifact-001",
        "artifact_type": "model",
        "artifact_version": "v1",
        "artifact_checksum": "artifact-checksum",
        "dataset_checksum": "dataset-checksum",
        "config_checksum": "config-checksum",
        "model_checksum": "model-checksum",
        "code_commit": "abcdef123456",
        "source_doc_urls": ["https://www.nist.gov/itl/ai-risk-management-framework"],
        "metrics_summary": {"numeric_exact_rate": 0.9},
        "approval_status": "approved",
        "approved_by": "ml-review-board",
        "rollback_to": "artifact-000",
    }
    payload.update(overrides)
    return ArtifactProvenance.model_validate(payload)


def _report(**overrides: object) -> RedactedEvaluationReport:
    """Build a valid redacted governance evaluation report.

    Args:
        overrides: Field overrides.

    Returns:
        Redacted evaluation report.
    """
    payload: dict[str, object] = {
        "report_id": "report-001",
        "pipeline": "paddleocr_finetuning",
        "frozen_fixture_version": "supplement-fixtures-v1",
        "split_version": "split-v1",
        "aggregate_case_count": 12,
        "baseline_metrics": {
            "downstream_field_exact_rate": 0.80,
            "numeric_exact_rate": 0.70,
            "unit_exact_rate": 0.75,
            "parser_success_rate": 0.85,
        },
        "candidate_metrics": {
            "downstream_field_exact_rate": 0.82,
            "numeric_exact_rate": 0.70,
            "unit_exact_rate": 0.75,
            "parser_success_rate": 0.85,
        },
        "safety_metrics": {
            "fabricated_field_count": 0,
            "false_correction_count": 0,
            "raw_text_leak_count": 0,
            "raw_data_leak_count": 0,
        },
        "artifact_provenance": [_artifact()],
        "source_doc_urls": ["https://www.nist.gov/privacy-framework"],
    }
    payload.update(overrides)
    return RedactedEvaluationReport.model_validate(payload)


def test_build_consent_policy_snapshot_reports_missing_learning_consent() -> None:
    """Verify image-learning export cannot pass without required consent."""
    settings = Settings(
        enable_image_learning_pipeline=True,
        enable_pgvector_storage=True,
        image_retention_days=30,
        learning_object_storage_provider="local",
    )

    snapshot = build_consent_retention_policy_snapshot(
        settings=settings,
        granted_consents=[ConsentType.OCR_IMAGE_PROCESSING],
        require_image_learning=True,
    )

    assert snapshot.missing_consent_scopes == [
        "data_retention",
        "image_learning_dataset",
    ]
    status = evaluate_policy_snapshot(snapshot, gate_mode="block_release")
    assert status.release_blocked is True
    assert "missing_consent:data_retention" in status.reasons


def test_missing_policy_snapshot_fails_release_readiness_gate() -> None:
    """Verify governance evaluation fails when consent/retention snapshot is absent."""
    status = evaluate_policy_snapshot(None, gate_mode="report_only")

    assert status.status == "warning"
    assert status.release_blocked is False
    assert status.reasons == ["consent_retention_policy_snapshot_missing"]


def test_promotion_decision_requires_artifact_checksums_and_code_commit() -> None:
    """Verify non-reproducible artifacts cannot be promotion candidates."""
    report = _report(
        artifact_provenance=[
            _artifact(
                artifact_checksum=None,
                dataset_checksum=None,
                config_checksum=None,
                code_commit=None,
            )
        ]
    )

    decision = evaluate_promotion_decision(report, gate_mode="block_release")

    assert decision.promotable is False
    assert decision.release_blocked is True
    assert "artifact_checksum_missing:artifact-001" in decision.reasons
    assert "dataset_checksum_missing:artifact-001" in decision.reasons
    assert "config_checksum_missing:artifact-001" in decision.reasons
    assert "code_commit_missing:artifact-001" in decision.reasons


def test_promotion_decision_rejects_safety_metric_regression() -> None:
    """Verify any non-zero safety metric blocks promotion."""
    report = _report(
        safety_metrics={
            "fabricated_field_count": 1,
            "false_correction_count": 0,
            "raw_text_leak_count": 0,
            "raw_data_leak_count": 0,
        }
    )

    decision = evaluate_promotion_decision(report, gate_mode="block_release")

    assert decision.promotable is False
    assert decision.release_blocked is True
    assert "safety_metric_nonzero:fabricated_field_count" in decision.reasons


def test_promotion_decision_rejects_primary_metric_regression() -> None:
    """Verify a candidate cannot regress any primary metric."""
    report = _report(
        candidate_metrics={
            "downstream_field_exact_rate": 0.82,
            "numeric_exact_rate": 0.69,
            "unit_exact_rate": 0.75,
            "parser_success_rate": 0.85,
        }
    )

    decision = evaluate_promotion_decision(report, gate_mode="block_release")

    assert decision.promotable is False
    assert "primary_metric_regressed:numeric_exact_rate" in decision.reasons


def test_report_only_mode_does_not_block_release_on_failed_candidate() -> None:
    """Verify report-only mode records failure without blocking deployment."""
    report = _report(artifact_provenance=[_artifact(rollback_to=None)])

    decision = evaluate_promotion_decision(report, gate_mode="report_only")

    assert decision.promotable is False
    assert decision.release_blocked is False
    assert "rollback_target_missing:artifact-001" in decision.reasons


def test_block_release_mode_accepts_approved_non_regressing_report() -> None:
    """Verify a complete report can become a promotion candidate."""
    decision = evaluate_promotion_decision(_report(), gate_mode="block_release")

    assert decision.promotable is True
    assert decision.release_blocked is False
    assert decision.reasons == ["promotion_candidate"]


def test_supplement_ocr_gate_allows_equal_no_regression_without_artifact() -> None:
    """Verify OCR gate reports pass on no-regression metrics without model artifacts."""
    report = _report(
        pipeline="supplement_ocr_gate",
        primary_metric_names=[
            "text_non_empty_rate",
            "parser_success_rate",
            "ingredient_name_exact_rate",
        ],
        baseline_metrics={
            "text_non_empty_rate": 1.0,
            "parser_success_rate": 0.9,
            "ingredient_name_exact_rate": 0.8,
        },
        candidate_metrics={
            "text_non_empty_rate": 1.0,
            "parser_success_rate": 0.9,
            "ingredient_name_exact_rate": 0.8,
        },
        required_safety_metric_names=["provider_not_run_count", "raw_text_leak_count"],
        safety_metrics={"provider_not_run_count": 0, "raw_text_leak_count": 0},
        artifact_provenance=[],
    )

    decision = evaluate_promotion_decision(report, gate_mode="block_release")

    assert decision.promotable is True
    assert decision.release_blocked is False
    assert decision.reasons == ["promotion_candidate"]


def test_release_governance_manifest_combines_policy_and_pipeline_reports() -> None:
    """Verify manifest evaluation produces a shared cross-pipeline report."""
    snapshot = ConsentRetentionPolicySnapshot(
        required_consent_scopes=[],
        granted_consent_scopes=[],
        missing_consent_scopes=[],
    )
    report = evaluate_release_governance_manifest(
        {
            "target_environment": "staging",
            "release_target": "public_staging",
            "gate_mode": "block_release",
            "policy_snapshot": snapshot.model_dump(mode="json"),
            "evaluation_reports": [_report().model_dump(mode="json")],
        }
    )

    assert report.overall_status == "passed"
    assert {status.pipeline for status in report.pipeline_statuses} == {
        "release_readiness",
        "paddleocr_finetuning",
    }


def test_governance_readiness_component_does_not_expose_secrets() -> None:
    """Verify readiness governance summary is configuration-only and sanitized."""
    component = build_governance_readiness_component(
        Settings(
            google_cloud_api_key=SecretStr("secret-google-key"),
            clova_ocr_secret=SecretStr("secret-clova-key"),
        )
    )
    dumped = component.model_dump(mode="json")

    assert dumped["name"] == "governance"
    assert dumped["details"]["gate_mode"] == "report_only"
    assert "secret-google-key" not in str(dumped)
    assert "secret-clova-key" not in str(dumped)
