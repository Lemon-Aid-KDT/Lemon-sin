"""Cross-cutting governance gates for OCR, learning, and parser artifacts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import cast

from src.config import Settings
from src.learning.consent_gate import IMAGE_LEARNING_REQUIRED_CONSENTS, evaluate_image_learning_gate
from src.models.schemas.governance import (
    DEFAULT_SAFETY_GOVERNANCE_METRICS,
    ConsentRetentionPolicySnapshot,
    GovernanceGateMode,
    GovernanceGateReport,
    GovernanceStatus,
    PipelineGovernanceState,
    PipelineGovernanceStatus,
    PromotionDecision,
    RedactedEvaluationReport,
    reject_governance_raw_fields,
)
from src.models.schemas.privacy import ConsentType
from src.models.schemas.readiness import ReadinessComponent

NO_REGRESSION_GOVERNANCE_PIPELINES = frozenset({"supplement_ocr_gate"})


class GovernanceGateError(ValueError):
    """Raised when a governance report payload is unsafe or malformed."""


def build_consent_retention_policy_snapshot(
    *,
    settings: Settings,
    granted_consents: Iterable[ConsentType | str],
    require_image_learning: bool = False,
    require_external_ocr: bool = False,
    require_prescription_ocr: bool = False,
    require_lab_result_ocr: bool = False,
    consent_withdrawal_exclusion_list_required: bool = False,
    withdrawal_exclusion_list_present: bool = False,
) -> ConsentRetentionPolicySnapshot:
    """Build a redacted consent and retention snapshot for governance reports.

    Args:
        settings: Runtime settings.
        granted_consents: Consent buckets granted for the export/evaluation context.
        require_image_learning: Whether image-learning consents and retention are required.
        require_external_ocr: Whether external OCR consent is required.
        require_prescription_ocr: Whether prescription OCR consent is required.
        require_lab_result_ocr: Whether lab-result OCR consent is required.
        consent_withdrawal_exclusion_list_required: Whether revoked consent requires an exclusion
            list or dataset regeneration proof.
        withdrawal_exclusion_list_present: Whether that exclusion proof is present.

    Returns:
        Redacted policy snapshot.
    """
    granted = _consent_scope_values(granted_consents)
    required: list[str] = []
    policy_issues: list[str] = []

    if require_image_learning:
        required.extend(consent.value for consent in IMAGE_LEARNING_REQUIRED_CONSENTS)
        image_gate = evaluate_image_learning_gate(
            settings,
            _consent_types_from_values(granted),
        )
        if not image_gate.allowed:
            policy_issues.append(_safe_policy_issue(image_gate.reason))
        if settings.learning_object_storage_provider == "disabled":
            policy_issues.append("learning_object_storage_disabled")
    if require_external_ocr:
        required.append(ConsentType.EXTERNAL_OCR_PROCESSING.value)
        if not settings.allow_external_ocr:
            policy_issues.append("external_ocr_disabled")
    if require_prescription_ocr:
        required.append(ConsentType.PRESCRIPTION_OCR_INTAKE.value)
    if require_lab_result_ocr:
        required.append(ConsentType.LAB_RESULT_OCR_INTAKE.value)
    if consent_withdrawal_exclusion_list_required and not withdrawal_exclusion_list_present:
        policy_issues.append("withdrawal_exclusion_list_missing")

    required = _dedupe(required)
    missing = [scope for scope in required if scope not in granted]
    return ConsentRetentionPolicySnapshot(
        required_consent_scopes=required,
        granted_consent_scopes=granted,
        missing_consent_scopes=missing,
        policy_issues=policy_issues,
        image_retention_days=settings.image_retention_days,
        regulated_document_original_image_retention_seconds=(
            settings.sensitive_document_original_image_retention_seconds
        ),
        external_ocr_allowed=settings.allow_external_ocr,
        image_learning_pipeline_enabled=settings.enable_image_learning_pipeline,
        pgvector_storage_enabled=settings.enable_pgvector_storage,
        object_storage_provider=settings.learning_object_storage_provider,
        consent_withdrawal_exclusion_list_required=(consent_withdrawal_exclusion_list_required),
        withdrawal_exclusion_list_present=withdrawal_exclusion_list_present,
    )


def evaluate_policy_snapshot(
    snapshot: ConsentRetentionPolicySnapshot | None,
    *,
    gate_mode: GovernanceGateMode,
) -> PipelineGovernanceStatus:
    """Evaluate the consent and retention policy part of a release gate.

    Args:
        snapshot: Policy snapshot. Missing snapshots fail the gate.
        gate_mode: Report-only or blocking release mode.

    Returns:
        Pipeline governance status for release readiness.
    """
    if snapshot is None:
        return _status(
            reasons=("consent_retention_policy_snapshot_missing",),
            gate_mode=gate_mode,
        )

    reasons: list[str] = []
    reasons.extend(f"missing_consent:{scope}" for scope in snapshot.missing_consent_scopes)
    reasons.extend(snapshot.policy_issues)
    if (
        snapshot.image_learning_pipeline_enabled
        and snapshot.image_retention_days <= 0
        and "IMAGE_RETENTION_DAYS must be positive for learning reuse." not in reasons
    ):
        reasons.append("image_retention_days_not_positive")
    if (
        snapshot.consent_withdrawal_exclusion_list_required
        and not snapshot.withdrawal_exclusion_list_present
    ):
        reasons.append("withdrawal_exclusion_list_missing")
    return _status(reasons=tuple(reasons), gate_mode=gate_mode)


def evaluate_promotion_decision(
    report: RedactedEvaluationReport,
    *,
    gate_mode: GovernanceGateMode,
) -> PromotionDecision:
    """Evaluate a promotion decision from one redacted evaluation report.

    Args:
        report: Redacted aggregate evaluation report.
        gate_mode: Report-only or blocking release mode.

    Returns:
        Promotion decision with metric deltas and safe reason codes.
    """
    reasons = _artifact_provenance_reasons(report)
    metric_reasons, deltas, improved = _primary_metric_reasons(report)
    reasons.extend(metric_reasons)
    reasons.extend(_safety_metric_reasons(report))
    warnings = _safety_metric_warnings(report)
    if not improved and report.pipeline not in NO_REGRESSION_GOVERNANCE_PIPELINES:
        reasons.append("no_primary_metric_improved")

    promotable = not reasons
    if promotable:
        reasons.append("promotion_candidate")
    return PromotionDecision(
        promotable=promotable,
        gate_mode=gate_mode,
        release_blocked=(gate_mode == "block_release" and not promotable),
        reasons=reasons,
        warnings=warnings,
        primary_metric_deltas=deltas,
    )


def _artifact_provenance_reasons(report: RedactedEvaluationReport) -> list[str]:
    """Return promotion failure reasons related to artifact provenance.

    Args:
        report: Redacted evaluation report.

    Returns:
        Safe reason codes.
    """
    if not report.artifact_provenance and report.pipeline in NO_REGRESSION_GOVERNANCE_PIPELINES:
        return []
    if not report.artifact_provenance:
        return ["artifact_provenance_missing"]
    reasons: list[str] = []
    for artifact in report.artifact_provenance:
        missing_checks = (
            ("artifact_checksum_missing", artifact.artifact_checksum),
            ("dataset_checksum_missing", artifact.dataset_checksum),
            ("config_checksum_missing", artifact.config_checksum),
            ("code_commit_missing", artifact.code_commit),
            ("source_doc_urls_missing", artifact.source_doc_urls),
            ("artifact_approver_missing", artifact.approved_by),
            ("rollback_target_missing", artifact.rollback_to),
        )
        reasons.extend(
            f"{reason}:{artifact.artifact_id}" for reason, value in missing_checks if not value
        )
        if artifact.approval_status != "approved":
            reasons.append(f"artifact_not_approved:{artifact.artifact_id}")
    return reasons


def _primary_metric_reasons(
    report: RedactedEvaluationReport,
) -> tuple[list[str], dict[str, float], bool]:
    """Return primary metric failures, deltas, and improvement status.

    Args:
        report: Redacted evaluation report.

    Returns:
        Tuple of reason codes, metric deltas, and whether any metric improved.
    """
    reasons: list[str] = []
    deltas: dict[str, float] = {}
    improved = False
    for metric in report.primary_metric_names:
        baseline = report.baseline_metrics.get(metric)
        candidate = report.candidate_metrics.get(metric)
        if baseline is None or candidate is None:
            reasons.append(f"primary_metric_missing:{metric}")
            continue
        delta = candidate - baseline
        deltas[metric] = delta
        if delta < 0:
            reasons.append(f"primary_metric_regressed:{metric}")
        improved = improved or delta > 0
    return reasons, deltas, improved


def _safety_metric_reasons(report: RedactedEvaluationReport) -> list[str]:
    """Return safety metric promotion failures.

    Args:
        report: Redacted evaluation report.

    Returns:
        Safe reason codes.
    """
    reasons: list[str] = []
    for metric in report.required_safety_metric_names:
        value = report.safety_metrics.get(metric)
        if value is None:
            reasons.append(f"safety_metric_missing:{metric}")
        elif value != 0:
            reasons.append(f"safety_metric_nonzero:{metric}")
    return reasons


def _safety_metric_warnings(report: RedactedEvaluationReport) -> list[str]:
    """Return warnings for non-required safety metrics.

    Args:
        report: Redacted evaluation report.

    Returns:
        Safe warning codes.
    """
    return [
        f"extra_safety_metric_nonzero:{metric}"
        for metric in DEFAULT_SAFETY_GOVERNANCE_METRICS
        if report.safety_metrics.get(metric, 0) != 0
        and metric not in report.required_safety_metric_names
    ]


def build_pipeline_governance_status(
    report: RedactedEvaluationReport,
    *,
    gate_mode: GovernanceGateMode,
) -> PipelineGovernanceStatus:
    """Build one pipeline governance status from a redacted report.

    Args:
        report: Redacted evaluation report.
        gate_mode: Report-only or blocking release mode.

    Returns:
        Pipeline governance status.
    """
    decision = evaluate_promotion_decision(report, gate_mode=gate_mode)
    state: PipelineGovernanceState
    if decision.promotable:
        state = "passed"
    elif gate_mode == "block_release":
        state = "failed"
    else:
        state = "warning"
    return PipelineGovernanceStatus(
        pipeline=report.pipeline,
        status=state,
        gate_mode=gate_mode,
        release_blocked=decision.release_blocked,
        reasons=decision.reasons,
        warnings=decision.warnings,
        promotion=decision,
    )


def build_governance_gate_report(
    *,
    target_environment: str,
    release_target: str,
    gate_mode: GovernanceGateMode,
    policy_snapshot: ConsentRetentionPolicySnapshot | None,
    evaluation_reports: Sequence[RedactedEvaluationReport],
) -> GovernanceGateReport:
    """Build a cross-pipeline governance gate report.

    Args:
        target_environment: Target runtime environment.
        release_target: Target release channel.
        gate_mode: Report-only or blocking release mode.
        policy_snapshot: Consent and retention snapshot.
        evaluation_reports: Redacted aggregate evaluation reports.

    Returns:
        Governance gate report.
    """
    statuses = [evaluate_policy_snapshot(policy_snapshot, gate_mode=gate_mode)]
    statuses.extend(
        build_pipeline_governance_status(report, gate_mode=gate_mode)
        for report in evaluation_reports
    )
    return GovernanceGateReport(
        target_environment=target_environment,
        release_target=release_target,
        gate_mode=gate_mode,
        overall_status=_overall_status(statuses),
        policy_snapshot=policy_snapshot,
        pipeline_statuses=statuses,
        evaluation_reports=list(evaluation_reports),
    )


def evaluate_release_governance_manifest(manifest: Mapping[str, object]) -> GovernanceGateReport:
    """Evaluate a redacted release-governance manifest.

    Args:
        manifest: Parsed JSON object containing policy and evaluation reports.

    Returns:
        Governance gate report.

    Raises:
        GovernanceGateError: If the manifest is unsafe or malformed.
    """
    try:
        reject_governance_raw_fields(manifest)
    except ValueError as exc:
        raise GovernanceGateError(str(exc)) from exc

    gate_mode = _gate_mode(str(manifest.get("gate_mode", "report_only")))
    target_environment = str(manifest.get("target_environment", "development"))
    release_target = str(manifest.get("release_target", "local"))
    policy_snapshot = _policy_snapshot(manifest.get("policy_snapshot"))
    reports = _evaluation_reports(manifest.get("evaluation_reports", manifest.get("reports", [])))
    return build_governance_gate_report(
        target_environment=target_environment,
        release_target=release_target,
        gate_mode=gate_mode,
        policy_snapshot=policy_snapshot,
        evaluation_reports=reports,
    )


def build_governance_readiness_component(settings: Settings) -> ReadinessComponent:
    """Build a configuration-only governance component for ``/ready``.

    Args:
        settings: Runtime settings.

    Returns:
        Sanitized readiness component. This function does not read artifacts or call providers.
    """
    public_runtime = settings.environment == "production" or (
        settings.environment == "staging" and settings.deployment_exposure == "public"
    )
    if public_runtime and settings.governance_gate_mode != "block_release":
        return ReadinessComponent(
            name="governance",
            status="not_ready",
            message_code="blocking_release_governance_required",
            details={
                "gate_mode": settings.governance_gate_mode,
                "runtime_check": "configuration_only",
            },
        )
    return ReadinessComponent(
        name="governance",
        status="ready" if settings.governance_gate_mode == "block_release" else "not_configured",
        message_code=(
            "release_governance_blocking"
            if settings.governance_gate_mode == "block_release"
            else "release_governance_report_only"
        ),
        details={
            "gate_mode": settings.governance_gate_mode,
            "runtime_check": "configuration_only",
        },
    )


def _status(
    *,
    reasons: Sequence[str],
    gate_mode: GovernanceGateMode,
) -> PipelineGovernanceStatus:
    """Build a release-readiness status from reason codes.

    Args:
        reasons: Failure or warning reasons.
        gate_mode: Report-only or blocking release mode.

    Returns:
        Pipeline governance status.
    """
    has_reasons = bool(reasons)
    state: PipelineGovernanceState
    if not has_reasons:
        state = "passed"
    elif gate_mode == "block_release":
        state = "failed"
    else:
        state = "warning"
    return PipelineGovernanceStatus(
        pipeline="release_readiness",
        status=state,
        gate_mode=gate_mode,
        release_blocked=gate_mode == "block_release" and has_reasons,
        reasons=list(reasons) if has_reasons else ["policy_gate_passed"],
    )


def _overall_status(
    statuses: Sequence[PipelineGovernanceStatus],
) -> GovernanceStatus:
    """Resolve the aggregate governance status.

    Args:
        statuses: Per-pipeline statuses.
    Returns:
        Aggregate status string.
    """
    if any(status.release_blocked for status in statuses):
        return "blocked"
    if any(status.status == "failed" for status in statuses):
        return "failed"
    if any(status.status == "warning" for status in statuses):
        return "warning"
    return "passed"


def _gate_mode(value: str) -> GovernanceGateMode:
    """Parse a governance gate mode.

    Args:
        value: Candidate gate mode.

    Returns:
        Gate mode.

    Raises:
        GovernanceGateError: If the value is unsupported.
    """
    if value in {"report_only", "block_release"}:
        return cast(GovernanceGateMode, value)
    raise GovernanceGateError("gate_mode must be report_only or block_release.")


def _policy_snapshot(value: object) -> ConsentRetentionPolicySnapshot | None:
    """Parse an optional policy snapshot.

    Args:
        value: Candidate policy snapshot.

    Returns:
        Parsed policy snapshot, or None when missing.

    Raises:
        GovernanceGateError: If the snapshot is invalid.
    """
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise GovernanceGateError("policy_snapshot must be an object.")
    try:
        return ConsentRetentionPolicySnapshot.model_validate(value)
    except ValueError as exc:
        raise GovernanceGateError(str(exc)) from exc


def _evaluation_reports(value: object) -> list[RedactedEvaluationReport]:
    """Parse redacted evaluation reports.

    Args:
        value: Candidate report list.

    Returns:
        Parsed reports.

    Raises:
        GovernanceGateError: If the reports are invalid.
    """
    if not isinstance(value, list):
        raise GovernanceGateError("evaluation_reports must be a list.")
    reports: list[RedactedEvaluationReport] = []
    for item in value:
        try:
            reports.append(RedactedEvaluationReport.model_validate(item))
        except ValueError as exc:
            raise GovernanceGateError(str(exc)) from exc
    return reports


def _consent_scope_values(consents: Iterable[ConsentType | str]) -> list[str]:
    """Return sorted consent scope strings.

    Args:
        consents: Consent enum values or strings.

    Returns:
        Deduplicated consent scope strings.
    """
    return _dedupe(
        consent.value if isinstance(consent, ConsentType) else str(consent) for consent in consents
    )


def _consent_types_from_values(values: Iterable[str]) -> tuple[ConsentType, ...]:
    """Convert known consent strings into ``ConsentType`` values.

    Args:
        values: Consent scope strings.

    Returns:
        Known consent enum values.
    """
    converted: list[ConsentType] = []
    for value in values:
        try:
            converted.append(ConsentType(value))
        except ValueError:
            continue
    return tuple(converted)


def _safe_policy_issue(reason: str) -> str:
    """Convert gate reasons into stable, non-sensitive issue codes.

    Args:
        reason: Gate reason string.

    Returns:
        Safe issue code.
    """
    if reason.startswith("ENABLE_"):
        return reason.split("=", maxsplit=1)[0].lower()
    if "IMAGE_RETENTION_DAYS" in reason:
        return "image_retention_days_not_positive"
    if "consent" in reason.lower():
        return "required_image_learning_consent_missing"
    return "image_learning_gate_failed"


def _dedupe(values: Iterable[str]) -> list[str]:
    """Deduplicate strings while preserving order.

    Args:
        values: Candidate strings.

    Returns:
        Deduplicated non-empty strings.
    """
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = value.strip()
        if not stripped or stripped in seen:
            continue
        normalized.append(stripped)
        seen.add(stripped)
    return normalized


__all__ = [
    "GovernanceGateError",
    "build_consent_retention_policy_snapshot",
    "build_governance_gate_report",
    "build_governance_readiness_component",
    "build_pipeline_governance_status",
    "evaluate_policy_snapshot",
    "evaluate_promotion_decision",
    "evaluate_release_governance_manifest",
    "reject_governance_raw_fields",
]
