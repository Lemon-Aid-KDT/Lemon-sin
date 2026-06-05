"""Tests for supplement learning pipeline readiness reporting."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[4]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

reporter = importlib.import_module("scripts.build_supplement_learning_pipeline_readiness_report")


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    """Write a JSON fixture.

    Args:
        path: Destination path.
        payload: Fixture payload.

    Returns:
        Written path.
    """
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    """Write a JSONL fixture.

    Args:
        path: Destination path.
        rows: Fixture rows.

    Returns:
        Written path.
    """
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _artifact_payloads() -> dict[str, dict[str, Any]]:
    """Return safe JSON object fixtures by artifact role.

    Returns:
        Role to payload mapping.
    """
    return {
        "taxonomy_audit": {
            "schema_version": "supplement-crawling-image-taxonomy-audit-v1",
            "category_count": 43,
        },
        "taxonomy_staging": {
            "schema_version": "supplement-taxonomy-db-staging-v1",
            "row_count": 431,
        },
        "brand_review_template": {
            "schema_version": "supplement-brand-review-template-v1",
            "pending_review_count": 388,
        },
        "brand_review_bundle": {
            "schema_version": "supplement-brand-review-bundle-v1",
            "reviewable_row_count": 388,
            "decision_template_row_count": 388,
        },
        "brand_review_decision_preflight": {
            "schema_version": "supplement-brand-review-decision-preflight-v1",
            "ready_for_requested_apply": False,
            "blank_decision_count": 388,
        },
        "category_only_import_dry_run": {
            "schema_version": "supplement-taxonomy-approved-db-import-v1",
            "ready_for_db_write": True,
            "preflight_only": True,
            "apply_requested": False,
            "category_seed_row_count": 43,
            "approved_product_import_row_count": 0,
            "planned_category_upsert_count": 43,
            "planned_product_upsert_count": 0,
            "planned_product_category_upsert_count": 0,
            "db_write_performed": False,
        },
        "category_seed_apply_gate": {
            "schema_version": "supplement-category-seed-db-apply-gate-v1",
            "status": "ready_for_category_seed_db_apply",
            "category_seed_db_apply_allowed": True,
            "product_db_apply_allowed": False,
            "product_category_db_apply_allowed": False,
            "category_seed_row_count": 43,
            "planned_category_upsert_count": 43,
            "planned_product_upsert_count": 0,
            "planned_product_category_upsert_count": 0,
            "database_connection_opened": False,
            "db_write_performed": False,
        },
        "category_seed_target_preflight": {
            "schema_version": "supplement-category-seed-db-target-preflight-v1",
            "status": "ready_for_local_category_seed_apply",
            "category_seed_db_apply_target_allowed": True,
            "runtime_environment": "development",
            "database_host_class": "local",
            "database_driver": "postgresql+asyncpg",
            "product_db_apply_allowed": False,
            "product_category_db_apply_allowed": False,
            "db_connection_opened": False,
            "db_write_performed": False,
        },
        "category_seed_db_verification": {
            "schema_version": "supplement-taxonomy-db-import-verification-v1",
            "db_import_verified": True,
            "expected_category_count": 43,
            "matched_category_count": 43,
            "missing_category_count": 0,
            "expected_product_count": 0,
            "matched_product_count": 0,
            "expected_product_category_count": 0,
            "matched_product_category_count": 0,
            "db_write_performed": False,
        },
        "taxonomy_db_verification": {
            "schema_version": "supplement-taxonomy-db-import-verification-v1",
            "db_import_verified": True,
            "expected_category_count": 43,
            "matched_category_count": 43,
            "missing_category_count": 0,
            "expected_product_count": 1,
            "matched_product_count": 1,
            "expected_product_category_count": 1,
            "matched_product_category_count": 1,
            "db_write_performed": False,
        },
        "learning_candidate_summary": {
            "schema_version": "supplement-learning-candidate-manifests-v1",
            "ocr_candidate_count": 215,
            "yolo_candidate_count": 205,
        },
        "private_image_tracking_check": {
            "schema_version": "private-image-tracking-check-v1",
            "passed": True,
            "tracked_private_image_count": 0,
            "protected_path_count": 2,
            "git_ls_files_checked": True,
        },
        "pii_screening_template": {
            "schema_version": "supplement-review-pii-screening-template-v1",
            "pending_review_count": 215,
        },
        "pii_screening_review_bundle": {
            "schema_version": "supplement-review-pii-screening-review-bundle-v1",
            "reviewable_row_count": 215,
            "decision_template_row_count": 215,
        },
        "pii_screening_decision_preflight": {
            "schema_version": "supplement-review-pii-screening-decision-preflight-v1",
            "ready_for_requested_apply": False,
            "blank_decision_count": 215,
        },
        "pii_screening_apply": {
            "schema_version": "supplement-review-pii-screening-apply-v1",
            "cleared_no_personal_data_count": 100,
        },
        "ocr_ground_truth_template": {
            "schema_version": "supplement-ocr-ground-truth-template-v1",
            "template_row_count": 100,
        },
        "ocr_ground_truth_review_bundle": {
            "schema_version": "supplement-ocr-ground-truth-review-bundle-v1",
            "reviewable_row_count": 100,
            "ground_truth_template_row_count": 100,
        },
        "ocr_benchmark_manifest": {
            "schema_version": "supplement-ocr-provider-benchmark-manifest-v1",
            "fixture_count": 88,
        },
        "ocr_three_tier_eval": {
            "schema_version": "ocr-kpi-gate-v1",
            "provider_count": 3,
        },
        "yolo_annotation_template": {
            "schema_version": "supplement-yolo-annotation-template-summary-v1",
            "pending_annotation_count": 205,
        },
        "yolo_annotation_review_bundle": {
            "schema_version": "supplement-yolo-annotation-review-bundle-v1",
            "reviewable_row_count": 205,
            "annotation_template_row_count": 205,
        },
        "yolo_annotation_decision_preflight": {
            "schema_version": "supplement-yolo-annotation-decision-preflight-v1",
            "ready_for_requested_promotion": False,
            "blank_box_row_count": 205,
        },
        "yolo_template_promotion": {
            "schema_version": "supplement-yolo-template-promotion-summary-v1",
            "accepted_row_count": 120,
        },
        "yolo_dataset": {
            "schema_version": "supplement-section-yolo-materialize-summary-v1",
            "status": "ok",
        },
        "paddleocr_improvement_candidates": {
            "schema_version": "supplement-paddleocr-improvement-manifest-v1",
            "candidate_count": 12,
        },
        "paddleocr_annotation_tasks": {
            "schema_version": "paddleocr-improvement-annotation-task-create-summary-v1",
            "status": "ok",
        },
        "paddleocr_dataset": {
            "schema_version": "paddleocr-dataset-materialize-summary-v1",
            "status": "ok",
        },
        "paddleocr_finetune_plan": {
            "schema_version": "paddleocr-finetune-run-plan-v1",
            "training_execution_performed": False,
        },
        "paddleocr_finetune_eval": {
            "schema_version": "paddleocr-finetune-eval-result-v1",
            "process_status": "metrics_verified",
        },
        "paddleocr_baseline_eval": {
            "schema_version": "paddleocr-baseline-eval-result-v1",
            "process_status": "metrics_verified",
        },
        "paddleocr_baseline_gate": {
            "schema_version": "paddleocr-baseline-comparison-gate-v1",
            "allowed": True,
        },
        "paddleocr_promotion_runbook": {
            "schema_version": "paddleocr-promotion-operator-runbook-v1",
            "ready_for_operator_review": True,
        },
        "operator_review_workpack": {
            "schema_version": "supplement-operator-review-workpack-v1",
            "status": "ok",
            "batch_count": 18,
            "workpack_file_count": 19,
            "next_batch_key": "brand_product_review:001",
        },
        "operator_review_batch_progress": {
            "schema_version": "supplement-operator-review-batch-progress-preflight-v1",
            "batch_count": 18,
            "complete_batch_count": 0,
            "pending_batch_count": 18,
            "invalid_batch_count": 0,
            "all_batches_complete": False,
            "next_incomplete_batch_key": "brand_product_review:001",
            "total_expected_row_count": 808,
            "total_valid_row_count": 0,
            "total_blank_row_count": 808,
            "total_pending_row_count": 0,
            "total_invalid_row_count": 0,
            "total_missing_row_count": 0,
        },
        "operator_post_completion_command_plan": {
            "schema_version": "supplement-operator-post-completion-command-plan-v1",
            "batch_key": "brand_product_review:001",
            "queue_key": "brand_product_review",
            "batch_status": "pending",
            "post_completion_execution_allowed": False,
            "blocked_reason_codes": ["batch_not_complete", "blank_rows_remaining"],
            "step_count": 10,
        },
    }


def _write_payloads(
    tmp_path: Path,
    roles: list[str],
    *,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Path]:
    """Write selected artifact fixtures.

    Args:
        tmp_path: Temporary directory.
        roles: Artifact roles to write.
        overrides: Optional payload overrides.

    Returns:
        Role to path mapping.
    """
    payloads = _artifact_payloads()
    if overrides:
        payloads.update(overrides)
    paths: dict[str, Path] = {}
    for role in roles:
        paths[role] = _write_json(tmp_path / f"{role}.json", payloads[role])
    return paths


def _stage(report: dict[str, Any], stage_key: str) -> dict[str, Any]:
    """Find one stage row.

    Args:
        report: Generated readiness report.
        stage_key: Stage key to find.

    Returns:
        Stage row.
    """
    return next(stage for stage in report["stages"] if stage["stage_key"] == stage_key)


def test_report_marks_human_review_stages_pending_without_decision_artifacts(
    tmp_path: Path,
) -> None:
    """Verify templates without decisions are reported as operator-review pending."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_audit",
            "taxonomy_staging",
            "brand_review_template",
            "learning_candidate_summary",
            "pii_screening_template",
            "ocr_ground_truth_template",
            "yolo_annotation_template",
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    dumped = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "in_progress_blocked_by_missing_or_invalid_artifacts"
    assert _stage(report, "brand_product_review")["status"] == "pending_operator_review"
    assert _stage(report, "review_pii_screening")["status"] == "pending_operator_review"
    assert _stage(report, "manual_ocr_ground_truth")["status"] == "pending_operator_review"
    assert _stage(report, "yolo_section_annotation")["status"] == "pending_operator_review"
    assert str(tmp_path) not in dumped
    assert "/Volumes/" not in dumped
    assert "sensitive OCR" not in dumped


def test_report_marks_pii_review_bundle_as_operator_pending(tmp_path: Path) -> None:
    """Verify a generated local review bundle is recognized as pending evidence."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_audit",
            "taxonomy_staging",
            "learning_candidate_summary",
            "pii_screening_review_bundle",
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    stage = _stage(report, "review_pii_screening")

    assert stage["status"] == "pending_operator_review"
    assert stage["present_pending_roles"] == ["pii_screening_review_bundle"]
    assert stage["missing_required_roles"] == ["pii_screening_apply"]


def test_report_verifies_private_image_tracking_check(tmp_path: Path) -> None:
    """Verify the private image tracking gate is a first-class readiness stage."""
    paths = _write_payloads(tmp_path, ["private_image_tracking_check"])

    report = reporter.build_readiness_report(artifact_paths=paths)
    stage = _stage(report, "private_image_tracking_check")
    artifact = next(
        item
        for item in report["artifact_summaries"]
        if item["role"] == "private_image_tracking_check"
    )

    assert stage["status"] == "verified"
    assert stage["missing_required_roles"] == []
    assert artifact["passed"] is True
    assert artifact["tracked_private_image_count"] == 0
    assert artifact["protected_path_count"] == 2


def test_report_blocks_tracked_private_images(tmp_path: Path) -> None:
    """Verify readiness blocks when private images are tracked by Git."""
    paths = _write_payloads(
        tmp_path,
        ["private_image_tracking_check"],
        overrides={
            "private_image_tracking_check": {
                "schema_version": "private-image-tracking-check-v1",
                "passed": False,
                "tracked_private_image_count": 1,
                "protected_path_count": 2,
                "git_ls_files_checked": True,
            },
        },
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    stage = _stage(report, "private_image_tracking_check")

    assert stage["status"] == "blocked_invalid_artifact"
    assert "private_image_tracking:not_passed" in stage["blocker_codes"]
    assert "private_image_tracking:tracked_image_count_not_zero" in stage["blocker_codes"]


def test_report_marks_pii_decision_preflight_as_operator_pending(tmp_path: Path) -> None:
    """Verify decision preflight is recognized as pending PII review evidence."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_audit",
            "taxonomy_staging",
            "learning_candidate_summary",
            "pii_screening_decision_preflight",
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    stage = _stage(report, "review_pii_screening")

    assert stage["status"] == "pending_operator_review"
    assert stage["present_pending_roles"] == ["pii_screening_decision_preflight"]
    assert stage["missing_required_roles"] == ["pii_screening_apply"]


def test_report_marks_brand_review_bundle_as_operator_pending(tmp_path: Path) -> None:
    """Verify generated brand review bundles are recognized as pending evidence."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_audit",
            "taxonomy_staging",
            "brand_review_bundle",
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    stage = _stage(report, "brand_product_review")

    assert stage["status"] == "pending_operator_review"
    assert stage["present_pending_roles"] == ["brand_review_bundle"]
    assert stage["missing_required_roles"] == ["approved_product_import"]


def test_report_marks_brand_decision_preflight_as_operator_pending(tmp_path: Path) -> None:
    """Verify brand decision preflight is recognized as pending evidence."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_audit",
            "taxonomy_staging",
            "brand_review_decision_preflight",
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    stage = _stage(report, "brand_product_review")

    assert stage["status"] == "pending_operator_review"
    assert stage["present_pending_roles"] == ["brand_review_decision_preflight"]
    assert stage["missing_required_roles"] == ["approved_product_import"]


def test_report_verifies_category_seed_db_without_brand_product_import(
    tmp_path: Path,
) -> None:
    """Verify category-only DB proof is separate from reviewed products."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_audit",
            "taxonomy_staging",
            "category_seed_db_verification",
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    category_stage = _stage(report, "category_seed_db_verification")
    product_stage = _stage(report, "taxonomy_db_import_verification")

    assert category_stage["status"] == "verified"
    assert category_stage["missing_required_roles"] == []
    assert product_stage["status"] == "blocked_missing_artifact"
    assert product_stage["missing_required_roles"] == [
        "approved_product_import",
        "taxonomy_db_verification",
    ]


def test_report_verifies_category_seed_apply_preflight_without_db_write(
    tmp_path: Path,
) -> None:
    """Verify category seed apply readiness is separate from DB verification."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_staging",
            "category_only_import_dry_run",
            "category_seed_apply_gate",
            "category_seed_target_preflight",
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    preflight_stage = _stage(report, "category_seed_db_apply_preflight")
    verification_stage = _stage(report, "category_seed_db_verification")

    assert preflight_stage["status"] == "verified"
    assert preflight_stage["missing_required_roles"] == []
    assert verification_stage["status"] == "pending_operator_review"
    assert verification_stage["present_pending_roles"] == [
        "category_seed_target_preflight",
        "taxonomy_staging",
    ]
    assert verification_stage["missing_required_roles"] == ["category_seed_db_verification"]


def test_report_blocks_category_seed_apply_preflight_when_product_writes_planned(
    tmp_path: Path,
) -> None:
    """Verify category-only preflight rejects accidental product write planning."""
    paths = _write_payloads(
        tmp_path,
        [
            "category_only_import_dry_run",
            "category_seed_apply_gate",
            "category_seed_target_preflight",
        ],
        overrides={
            "category_only_import_dry_run": {
                "schema_version": "supplement-taxonomy-approved-db-import-v1",
                "ready_for_db_write": True,
                "preflight_only": True,
                "apply_requested": False,
                "category_seed_row_count": 43,
                "approved_product_import_row_count": 1,
                "planned_category_upsert_count": 43,
                "planned_product_upsert_count": 1,
                "planned_product_category_upsert_count": 1,
                "db_write_performed": False,
            },
        },
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    stage = _stage(report, "category_seed_db_apply_preflight")

    assert stage["status"] == "blocked_invalid_artifact"
    assert (
        "category_seed_dry_run:approved_product_import_row_count_must_be_zero"
        in stage["blocker_codes"]
    )
    assert (
        "category_seed_dry_run:planned_product_upsert_count_must_be_zero"
        in stage["blocker_codes"]
    )
    assert (
        "category_seed_dry_run:planned_product_category_upsert_count_must_be_zero"
        in stage["blocker_codes"]
    )


def test_report_rejects_product_verification_as_category_seed_proof(
    tmp_path: Path,
) -> None:
    """Verify category seed proof cannot include reviewed product counts."""
    paths = _write_payloads(
        tmp_path,
        ["category_seed_db_verification"],
        overrides={
            "category_seed_db_verification": {
                "schema_version": "supplement-taxonomy-db-import-verification-v1",
                "db_import_verified": True,
                "expected_category_count": 43,
                "matched_category_count": 43,
                "missing_category_count": 0,
                "expected_product_count": 1,
                "expected_product_category_count": 1,
                "db_write_performed": False,
            },
        },
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    stage = _stage(report, "category_seed_db_verification")

    assert stage["status"] == "blocked_invalid_artifact"
    assert "category_seed:expected_product_count_not_zero" in stage["blocker_codes"]
    assert "category_seed:expected_product_category_count_not_zero" in stage["blocker_codes"]


def test_report_marks_yolo_review_bundle_as_operator_pending(tmp_path: Path) -> None:
    """Verify a generated YOLO annotation bundle is recognized as pending evidence."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_audit",
            "taxonomy_staging",
            "learning_candidate_summary",
            "yolo_annotation_review_bundle",
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    stage = _stage(report, "yolo_section_annotation")

    assert stage["status"] == "pending_operator_review"
    assert stage["present_pending_roles"] == ["yolo_annotation_review_bundle"]
    assert stage["missing_required_roles"] == ["yolo_template_promotion"]


def test_report_marks_yolo_decision_preflight_as_operator_pending(tmp_path: Path) -> None:
    """Verify YOLO annotation preflight is recognized as pending evidence."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_audit",
            "taxonomy_staging",
            "learning_candidate_summary",
            "yolo_annotation_decision_preflight",
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    stage = _stage(report, "yolo_section_annotation")

    assert stage["status"] == "pending_operator_review"
    assert stage["present_pending_roles"] == ["yolo_annotation_decision_preflight"]
    assert stage["missing_required_roles"] == ["yolo_template_promotion"]


def test_report_marks_operator_review_workpack_as_shared_pending_evidence(
    tmp_path: Path,
) -> None:
    """Verify batch workpacks are recognized for all covered human-review queues."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_audit",
            "taxonomy_staging",
            "learning_candidate_summary",
            "operator_review_workpack",
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    workpack = next(
        artifact
        for artifact in report["artifact_summaries"]
        if artifact["role"] == "operator_review_workpack"
    )

    assert _stage(report, "brand_product_review")["status"] == "pending_operator_review"
    assert _stage(report, "brand_product_review")["present_pending_roles"] == [
        "operator_review_workpack"
    ]
    assert _stage(report, "review_pii_screening")["status"] == "pending_operator_review"
    assert _stage(report, "review_pii_screening")["present_pending_roles"] == [
        "operator_review_workpack"
    ]
    assert _stage(report, "yolo_section_annotation")["status"] == "pending_operator_review"
    assert _stage(report, "yolo_section_annotation")["present_pending_roles"] == [
        "operator_review_workpack"
    ]
    assert workpack["status"] == "ok"
    assert workpack["batch_count"] == 18
    assert workpack["workpack_file_count"] == 19
    assert workpack["next_batch_key"] == "brand_product_review:001"


def test_report_marks_operator_review_batch_progress_as_shared_pending_evidence(
    tmp_path: Path,
) -> None:
    """Verify aggregate batch progress is recognized for covered review queues."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_audit",
            "taxonomy_staging",
            "learning_candidate_summary",
            "operator_review_batch_progress",
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    progress = next(
        artifact
        for artifact in report["artifact_summaries"]
        if artifact["role"] == "operator_review_batch_progress"
    )

    assert _stage(report, "brand_product_review")["status"] == "pending_operator_review"
    assert _stage(report, "brand_product_review")["present_pending_roles"] == [
        "operator_review_batch_progress"
    ]
    assert _stage(report, "review_pii_screening")["status"] == "pending_operator_review"
    assert _stage(report, "review_pii_screening")["present_pending_roles"] == [
        "operator_review_batch_progress"
    ]
    assert _stage(report, "yolo_section_annotation")["status"] == "pending_operator_review"
    assert _stage(report, "yolo_section_annotation")["present_pending_roles"] == [
        "operator_review_batch_progress"
    ]
    assert progress["batch_count"] == 18
    assert progress["pending_batch_count"] == 18
    assert progress["complete_batch_count"] == 0
    assert progress["total_blank_row_count"] == 808
    assert progress["next_incomplete_batch_key"] == "brand_product_review:001"


def test_report_marks_post_completion_plan_as_shared_pending_evidence(
    tmp_path: Path,
) -> None:
    """Verify post-completion command plans are recognized for review queues."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_audit",
            "taxonomy_staging",
            "learning_candidate_summary",
            "operator_post_completion_command_plan",
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    plan = next(
        artifact
        for artifact in report["artifact_summaries"]
        if artifact["role"] == "operator_post_completion_command_plan"
    )

    assert _stage(report, "brand_product_review")["status"] == "pending_operator_review"
    assert _stage(report, "brand_product_review")["present_pending_roles"] == [
        "operator_post_completion_command_plan"
    ]
    assert _stage(report, "review_pii_screening")["status"] == "pending_operator_review"
    assert _stage(report, "review_pii_screening")["present_pending_roles"] == [
        "operator_post_completion_command_plan"
    ]
    assert _stage(report, "yolo_section_annotation")["status"] == "pending_operator_review"
    assert _stage(report, "yolo_section_annotation")["present_pending_roles"] == [
        "operator_post_completion_command_plan"
    ]
    assert plan["schema_versions"] == [
        "supplement-operator-post-completion-command-plan-v1"
    ]


def test_report_marks_ocr_ground_truth_bundle_as_operator_pending(tmp_path: Path) -> None:
    """Verify generated OCR GT bundles are recognized as pending evidence."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_audit",
            "taxonomy_staging",
            "learning_candidate_summary",
            "pii_screening_apply",
            "ocr_ground_truth_review_bundle",
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    stage = _stage(report, "manual_ocr_ground_truth")

    assert stage["status"] == "pending_operator_review"
    assert stage["present_pending_roles"] == ["ocr_ground_truth_review_bundle"]
    assert stage["missing_required_roles"] == ["ocr_benchmark_manifest"]


def test_report_accepts_verified_chain_and_keeps_execution_flags_false(tmp_path: Path) -> None:
    """Verify a complete artifact chain produces a promotion-review checkpoint."""
    roles = list(_artifact_payloads())
    paths = _write_payloads(tmp_path, roles)
    paths["approved_product_import"] = _write_jsonl(
        tmp_path / "approved.jsonl",
        [
            {
                "schema_version": "supplement-product-import-manifest-row-v1",
                "source_provider": "reviewed_crawling_image",
                "source_product_id": "safe-hash-only",
            }
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)

    assert report["overall_status"] == "ready_for_operator_model_promotion_review"
    assert report["blocked_stage_count"] == 0
    assert report["pending_operator_review_stage_count"] == 0
    assert report["verified_stage_count"] == report["stage_count"]
    assert report["db_write_performed"] is False
    assert report["external_provider_call_performed"] is False
    assert report["llm_call_performed"] is False
    assert report["training_execution_performed_by_script"] is False
    assert report["source_image_read_performed"] is False


def test_report_accepts_jsonl_import_manifest_rows(tmp_path: Path) -> None:
    """Verify row-schema JSONL artifacts are summarized without row literals."""
    paths = _write_payloads(tmp_path, ["taxonomy_audit", "taxonomy_db_verification"])
    paths["taxonomy_staging"] = _write_jsonl(
        tmp_path / "staging.jsonl",
        [
            {
                "schema_version": "supplement-taxonomy-db-staging-v1",
                "row_type": "category_seed",
            },
            {
                "schema_version": "supplement-taxonomy-db-staging-v1",
                "row_type": "product_brand_candidate",
            },
        ],
    )
    paths["approved_product_import"] = _write_jsonl(
        tmp_path / "approved.jsonl",
        [
            {
                "schema_version": "supplement-product-import-manifest-row-v1",
                "source_provider": "reviewed_crawling_image",
                "source_product_id": "safe-hash-only",
            }
        ],
    )

    report = reporter.build_readiness_report(artifact_paths=paths)
    approved = next(
        artifact
        for artifact in report["artifact_summaries"]
        if artifact["role"] == "approved_product_import"
    )
    staging = next(
        artifact
        for artifact in report["artifact_summaries"]
        if artifact["role"] == "taxonomy_staging"
    )

    assert approved["record_count"] == 1
    assert approved["schema_versions"] == ["supplement-product-import-manifest-row-v1"]
    assert staging["record_count"] == 2
    assert staging["schema_versions"] == ["supplement-taxonomy-db-staging-v1"]
    assert _stage(report, "brand_product_review")["status"] == "verified"


def test_report_accepts_pretty_printed_json_artifact(tmp_path: Path) -> None:
    """Verify multi-line JSON objects are not mistaken for JSONL rows."""
    pretty_path = tmp_path / "audit.pretty.json"
    pretty_path.write_text(
        json.dumps(
            {
                "schema_version": "supplement-crawling-image-taxonomy-audit-v1",
                "category_count": 43,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report = reporter.build_readiness_report(artifact_paths={"taxonomy_audit": pretty_path})

    audit = next(
        artifact
        for artifact in report["artifact_summaries"]
        if artifact["role"] == "taxonomy_audit"
    )
    assert audit["record_count"] == 1
    assert _stage(report, "taxonomy_structure_audit")["status"] == "verified"


def test_missing_artifacts_emit_blocker_codes_without_path_leaks(tmp_path: Path) -> None:
    """Verify missing downstream artifacts are explicit and redacted."""
    paths = _write_payloads(tmp_path, ["taxonomy_audit"])

    report = reporter.build_readiness_report(artifact_paths=paths)
    dumped = json.dumps(report, ensure_ascii=False)

    assert _stage(report, "taxonomy_db_staging")["blocker_codes"] == [
        "missing_required:taxonomy_staging"
    ]
    assert _stage(report, "review_pii_screening")["status"] == "blocked_missing_artifact"
    assert _stage(report, "yolo_section_annotation")["status"] == "blocked_missing_artifact"
    assert _stage(report, "paddleocr_promotion_runbook")["status"] == "blocked_missing_artifact"
    assert str(tmp_path) not in dumped
    assert "/private/" not in dumped


def test_invalid_semantic_artifacts_block_relevant_stage(tmp_path: Path) -> None:
    """Verify non-passing metric and DB gates are not treated as verified."""
    paths = _write_payloads(
        tmp_path,
        [
            "taxonomy_db_verification",
            "paddleocr_finetune_eval",
            "paddleocr_baseline_eval",
            "paddleocr_baseline_gate",
        ],
        overrides={
            "taxonomy_db_verification": {
                "schema_version": "supplement-taxonomy-db-import-verification-v1",
                "db_import_verified": False,
            },
            "paddleocr_baseline_gate": {
                "schema_version": "paddleocr-baseline-comparison-gate-v1",
                "allowed": False,
            },
        },
    )

    report = reporter.build_readiness_report(artifact_paths=paths)

    assert _stage(report, "taxonomy_db_import_verification")["status"] == (
        "blocked_invalid_artifact"
    )
    assert _stage(report, "taxonomy_db_import_verification")["blocker_codes"] == [
        "db_import_not_verified"
    ]
    assert _stage(report, "paddleocr_metric_gate")["status"] == "blocked_invalid_artifact"
    assert "paddleocr_baseline_gate:not_allowed" in _stage(
        report, "paddleocr_metric_gate"
    )["blocker_codes"]


def test_cli_rejects_unsafe_payload_and_writes_redacted_error(
    tmp_path: Path,
    capsys: Any,
) -> None:
    """Verify unsafe artifacts fail closed without printing sensitive values."""
    unsafe_path = _write_json(
        tmp_path / "unsafe.json",
        {
            "schema_version": "supplement-crawling-image-taxonomy-audit-v1",
            "raw_ocr_text": "sensitive OCR",
            "note": "/Volumes/Corsair EX400U Media/private-source",
        },
    )
    output_path = tmp_path / "readiness.json"

    exit_code = reporter.run_cli(
        [
            "--artifact",
            f"taxonomy_audit={unsafe_path}",
            "--output",
            str(output_path),
        ]
    )

    stdout = capsys.readouterr().out
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert written["status"] == "error"
    assert "sensitive OCR" not in stdout
    assert "/Volumes/" not in stdout
    assert str(tmp_path) not in stdout
