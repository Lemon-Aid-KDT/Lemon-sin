"""Cross-cutting governance schemas for OCR and parser release gates."""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GOVERNANCE_REPORT_SCHEMA_VERSION: Literal["governance-gate-report-v1"] = "governance-gate-report-v1"
REDACTED_EVALUATION_SCHEMA_VERSION: Literal["redacted-evaluation-report-v1"] = (
    "redacted-evaluation-report-v1"
)
CONSENT_RETENTION_POLICY_SCHEMA_VERSION: Literal["consent-retention-policy-v1"] = (
    "consent-retention-policy-v1"
)
DEFAULT_PRIMARY_GOVERNANCE_METRICS = (
    "downstream_field_exact_rate",
    "numeric_exact_rate",
    "unit_exact_rate",
    "parser_success_rate",
)
DEFAULT_SAFETY_GOVERNANCE_METRICS = (
    "fabricated_field_count",
    "false_correction_count",
    "raw_text_leak_count",
    "raw_data_leak_count",
)
GOVERNANCE_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "direct_identifier",
        "direct_identifiers",
        "email",
        "exif",
        "file_name",
        "filename",
        "gps",
        "image_bytes",
        "ocr_text",
        "ocr_text_hash",
        "patient_id",
        "phone",
        "phone_number",
        "provider_payload",
        "raw_image",
        "raw_ocr_text",
        "raw_provider_payload",
        "request_headers",
        "service_key",
        "transcript",
        "transcript_hash",
        "user_id",
        "verified_transcript",
    }
)

GovernancePipeline = Literal[
    "paddleocr_local",
    "roi_quality",
    "paddleocr_finetuning",
    "parser_domain_correction",
    "external_ocr_provider",
    "supplement_ocr_gate",
    "release_readiness",
]
GovernanceGateMode = Literal["report_only", "block_release"]
GovernanceStatus = Literal["passed", "warning", "failed", "blocked"]
PipelineGovernanceState = Literal["passed", "warning", "failed", "skipped"]
ArtifactType = Literal["model", "dataset", "rule", "benchmark", "config", "report"]
ArtifactApprovalStatus = Literal["pending", "approved", "rejected", "disabled"]


def reject_governance_raw_fields(value: object) -> None:
    """Reject raw data, provider payload, credential, and direct identifier keys.

    Args:
        value: Candidate governance payload.

    Raises:
        ValueError: If a forbidden key appears anywhere in the payload.
    """
    if isinstance(value, Mapping):
        forbidden = GOVERNANCE_FORBIDDEN_KEYS.intersection(str(key).lower() for key in value)
        if forbidden:
            raise ValueError(f"Governance payload contains forbidden field(s): {sorted(forbidden)}")
        for nested_value in value.values():
            reject_governance_raw_fields(nested_value)
    elif isinstance(value, list):
        for item in value:
            reject_governance_raw_fields(item)


class GovernanceSafeModel(BaseModel):
    """Base schema that rejects raw data keys before model validation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def reject_raw_payload_fields(cls, data: object) -> object:
        """Reject raw payload fields before typed validation.

        Args:
            data: Candidate model input.

        Returns:
            The original input when it is safe.

        Raises:
            ValueError: If raw data or direct identifier keys are present.
        """
        reject_governance_raw_fields(data)
        return data


class ConsentRetentionPolicySnapshot(GovernanceSafeModel):
    """Redacted consent and retention state captured for a governance run.

    Attributes:
        schema_version: Fixed schema version.
        policy_version: Internal policy version.
        required_consent_scopes: Consent buckets required for this gate.
        granted_consent_scopes: Consent buckets granted for this gate.
        missing_consent_scopes: Required consent buckets that were not granted.
        policy_issues: Safe policy issue codes.
        image_retention_days: Configured supplement image retention days.
        regulated_document_original_image_retention_seconds: Raw regulated image retention seconds.
        external_ocr_allowed: Whether external OCR is globally allowed.
        image_learning_pipeline_enabled: Whether image learning export is enabled.
        pgvector_storage_enabled: Whether vector storage is enabled.
        object_storage_provider: Learning object storage provider setting.
        consent_withdrawal_exclusion_list_required: Whether withdrawal requires exclusion handling.
        withdrawal_exclusion_list_present: Whether an exclusion list/regeneration proof exists.
    """

    schema_version: Literal["consent-retention-policy-v1"] = CONSENT_RETENTION_POLICY_SCHEMA_VERSION
    policy_version: str = Field(default="governance-v1", min_length=1, max_length=80)
    required_consent_scopes: list[str] = Field(default_factory=list, max_length=40)
    granted_consent_scopes: list[str] = Field(default_factory=list, max_length=80)
    missing_consent_scopes: list[str] = Field(default_factory=list, max_length=40)
    policy_issues: list[str] = Field(default_factory=list, max_length=80)
    image_retention_days: int = Field(default=0, ge=0, le=730)
    regulated_document_original_image_retention_seconds: int = Field(default=0, ge=0, le=3600)
    external_ocr_allowed: bool = False
    image_learning_pipeline_enabled: bool = False
    pgvector_storage_enabled: bool = False
    object_storage_provider: str = Field(default="disabled", min_length=1, max_length=40)
    consent_withdrawal_exclusion_list_required: bool = False
    withdrawal_exclusion_list_present: bool = False

    @field_validator(
        "required_consent_scopes",
        "granted_consent_scopes",
        "missing_consent_scopes",
        "policy_issues",
    )
    @classmethod
    def normalize_string_list(cls, values: list[str]) -> list[str]:
        """Normalize bounded string lists while preserving order.

        Args:
            values: Candidate strings.

        Returns:
            Trimmed, deduplicated strings.
        """
        return _dedupe_strings(values)

    @model_validator(mode="after")
    def validate_missing_consent_consistency(self) -> Self:
        """Ensure missing consent scopes match required minus granted scopes.

        Returns:
            Validated policy snapshot.

        Raises:
            ValueError: If ``missing_consent_scopes`` is inconsistent.
        """
        granted = set(self.granted_consent_scopes)
        expected_missing = [scope for scope in self.required_consent_scopes if scope not in granted]
        if self.missing_consent_scopes != expected_missing:
            raise ValueError("missing_consent_scopes must match required minus granted scopes.")
        return self


class ArtifactProvenance(GovernanceSafeModel):
    """Redacted provenance for model, dataset, benchmark, or rule artifacts.

    Attributes:
        artifact_id: Stable artifact id.
        artifact_type: Artifact category.
        artifact_version: Human-readable artifact version.
        artifact_checksum: SHA-256 checksum of the artifact payload.
        dataset_checksum: SHA-256 checksum of the dataset or split manifest.
        config_checksum: SHA-256 checksum of the training/evaluation config.
        model_checksum: Optional model file checksum when the artifact is a model.
        code_commit: Source code commit used to produce the artifact.
        source_doc_urls: Official documentation or standard URLs used for the artifact.
        metrics_summary: Aggregate metric summary without raw examples.
        approval_status: Team review status.
        approved_by: Redacted approver handle or team id.
        rollback_to: Artifact id that can be used as a rollback target.
        created_at: Artifact creation timestamp.
    """

    artifact_id: str = Field(min_length=4, max_length=160)
    artifact_type: ArtifactType
    artifact_version: str = Field(min_length=1, max_length=120)
    artifact_checksum: str | None = Field(default=None, min_length=8, max_length=128)
    dataset_checksum: str | None = Field(default=None, min_length=8, max_length=128)
    config_checksum: str | None = Field(default=None, min_length=8, max_length=128)
    model_checksum: str | None = Field(default=None, min_length=8, max_length=128)
    code_commit: str | None = Field(default=None, min_length=7, max_length=80)
    source_doc_urls: list[str] = Field(default_factory=list, max_length=20)
    metrics_summary: dict[str, int | float | str | bool | None] = Field(default_factory=dict)
    approval_status: ArtifactApprovalStatus = "pending"
    approved_by: str | None = Field(default=None, min_length=2, max_length=120)
    rollback_to: str | None = Field(default=None, min_length=4, max_length=160)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("source_doc_urls")
    @classmethod
    def validate_source_doc_urls(cls, values: list[str]) -> list[str]:
        """Validate source documentation URLs are explicit web URLs.

        Args:
            values: Candidate source URLs.

        Returns:
            Validated URL list.

        Raises:
            ValueError: If a URL is not HTTP(S).
        """
        normalized = _dedupe_strings(values)
        for value in normalized:
            if not (value.startswith("https://") or value.startswith("http://")):
                raise ValueError("source_doc_urls must contain HTTP(S) URLs.")
        return normalized

    @field_validator("metrics_summary")
    @classmethod
    def validate_metrics_summary(
        cls,
        values: dict[str, int | float | str | bool | None],
    ) -> dict[str, int | float | str | bool | None]:
        """Validate aggregate metrics are finite when numeric.

        Args:
            values: Candidate metric summary.

        Returns:
            Validated metric summary.

        Raises:
            ValueError: If any numeric metric is NaN or infinite.
        """
        _validate_finite_mapping(values)
        return values


class RedactedEvaluationReport(GovernanceSafeModel):
    """Aggregate evaluation report without raw image, text, or provider payloads.

    Attributes:
        schema_version: Fixed schema version.
        report_id: Stable report id.
        pipeline: Pipeline represented by this report.
        frozen_fixture_version: Frozen fixture version used for baseline and candidate.
        split_version: Frozen train/validation/test split version.
        aggregate_case_count: Number of fixture cases summarized.
        primary_metric_names: Primary metric keys used for no-regression checks.
        required_safety_metric_names: Safety metric keys that must be zero.
        baseline_metrics: Aggregate baseline metrics.
        candidate_metrics: Aggregate candidate metrics.
        safety_metrics: Aggregate safety metrics for the candidate.
        artifact_provenance: Candidate artifact provenance records.
        source_doc_urls: Official documentation or standards referenced by the report.
        generated_at: Report creation timestamp.
        notes: Safe non-sensitive notes.
    """

    schema_version: Literal["redacted-evaluation-report-v1"] = REDACTED_EVALUATION_SCHEMA_VERSION
    report_id: str = Field(min_length=4, max_length=160)
    pipeline: GovernancePipeline
    frozen_fixture_version: str = Field(min_length=1, max_length=120)
    split_version: str = Field(min_length=1, max_length=120)
    aggregate_case_count: int = Field(ge=1, le=10_000_000)
    primary_metric_names: list[str] = Field(
        default_factory=lambda: list(DEFAULT_PRIMARY_GOVERNANCE_METRICS),
        min_length=1,
        max_length=20,
    )
    required_safety_metric_names: list[str] = Field(
        default_factory=lambda: list(DEFAULT_SAFETY_GOVERNANCE_METRICS),
        min_length=1,
        max_length=20,
    )
    baseline_metrics: dict[str, float] = Field(default_factory=dict)
    candidate_metrics: dict[str, float] = Field(default_factory=dict)
    safety_metrics: dict[str, float] = Field(default_factory=dict)
    artifact_provenance: list[ArtifactProvenance] = Field(default_factory=list, max_length=40)
    source_doc_urls: list[str] = Field(default_factory=list, max_length=20)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notes: list[str] = Field(default_factory=list, max_length=40)

    @field_validator("primary_metric_names", "required_safety_metric_names", "notes")
    @classmethod
    def normalize_string_fields(cls, values: list[str]) -> list[str]:
        """Normalize report string-list fields.

        Args:
            values: Candidate strings.

        Returns:
            Trimmed, deduplicated strings.
        """
        return _dedupe_strings(values)

    @field_validator("source_doc_urls")
    @classmethod
    def validate_source_doc_urls(cls, values: list[str]) -> list[str]:
        """Validate source documentation URLs are explicit web URLs.

        Args:
            values: Candidate source URLs.

        Returns:
            Validated URL list.
        """
        return ArtifactProvenance.validate_source_doc_urls(values)

    @field_validator("baseline_metrics", "candidate_metrics")
    @classmethod
    def validate_primary_metrics(cls, values: dict[str, float]) -> dict[str, float]:
        """Validate primary metric mappings contain finite rate values.

        Args:
            values: Candidate metric mapping.

        Returns:
            Validated metric mapping.

        Raises:
            ValueError: If a metric is outside the [0, 1] range.
        """
        _validate_finite_mapping(values)
        for key, value in values.items():
            if value < 0.0 or value > 1.0:
                raise ValueError(f"Primary metric must be a rate from 0 to 1: {key}")
        return values

    @field_validator("safety_metrics")
    @classmethod
    def validate_safety_metrics(cls, values: dict[str, float]) -> dict[str, float]:
        """Validate safety metrics are finite non-negative counts.

        Args:
            values: Candidate safety metric mapping.

        Returns:
            Validated safety metric mapping.
        """
        _validate_finite_mapping(values)
        for key, value in values.items():
            if value < 0.0:
                raise ValueError(f"Safety metric must be non-negative: {key}")
        return values


class PromotionDecision(GovernanceSafeModel):
    """Promotion decision for one pipeline evaluation.

    Attributes:
        promotable: Whether this report is a promotion candidate.
        gate_mode: Report-only or blocking release mode.
        release_blocked: Whether the decision blocks the target release.
        reasons: Stable safe reason codes.
        warnings: Stable safe warning codes.
        primary_metric_deltas: Candidate minus baseline primary metric deltas.
    """

    promotable: bool
    gate_mode: GovernanceGateMode
    release_blocked: bool
    reasons: list[str] = Field(default_factory=list, max_length=80)
    warnings: list[str] = Field(default_factory=list, max_length=80)
    primary_metric_deltas: dict[str, float] = Field(default_factory=dict)

    @field_validator("reasons", "warnings")
    @classmethod
    def normalize_reasons(cls, values: list[str]) -> list[str]:
        """Normalize decision reason lists.

        Args:
            values: Candidate reason strings.

        Returns:
            Trimmed, deduplicated reason strings.
        """
        return _dedupe_strings(values)


class PipelineGovernanceStatus(GovernanceSafeModel):
    """Governance status for one pipeline or release policy check.

    Attributes:
        pipeline: Pipeline represented by the status.
        status: Pipeline governance state.
        gate_mode: Report-only or blocking release mode.
        release_blocked: Whether this status blocks release.
        reasons: Stable safe reason codes.
        warnings: Stable safe warning codes.
        promotion: Optional promotion decision.
    """

    pipeline: GovernancePipeline
    status: PipelineGovernanceState
    gate_mode: GovernanceGateMode
    release_blocked: bool = False
    reasons: list[str] = Field(default_factory=list, max_length=80)
    warnings: list[str] = Field(default_factory=list, max_length=80)
    promotion: PromotionDecision | None = None

    @field_validator("reasons", "warnings")
    @classmethod
    def normalize_status_text(cls, values: list[str]) -> list[str]:
        """Normalize status reason and warning lists.

        Args:
            values: Candidate text list.

        Returns:
            Trimmed, deduplicated strings.
        """
        return _dedupe_strings(values)


class GovernanceGateReport(GovernanceSafeModel):
    """Cross-pipeline governance gate report.

    Attributes:
        schema_version: Fixed schema version.
        generated_at: Report creation timestamp.
        target_environment: Target runtime environment.
        release_target: Human-readable target release channel.
        gate_mode: Report-only or blocking release mode.
        overall_status: Aggregate governance status.
        policy_snapshot: Consent and retention policy snapshot.
        pipeline_statuses: Per-pipeline governance statuses.
        evaluation_reports: Redacted evaluation reports included in the gate.
    """

    schema_version: Literal["governance-gate-report-v1"] = GOVERNANCE_REPORT_SCHEMA_VERSION
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    target_environment: str = Field(min_length=1, max_length=40)
    release_target: str = Field(min_length=1, max_length=80)
    gate_mode: GovernanceGateMode = "report_only"
    overall_status: GovernanceStatus
    policy_snapshot: ConsentRetentionPolicySnapshot | None = None
    pipeline_statuses: list[PipelineGovernanceStatus] = Field(default_factory=list, max_length=80)
    evaluation_reports: list[RedactedEvaluationReport] = Field(default_factory=list, max_length=80)


def _dedupe_strings(values: list[str]) -> list[str]:
    """Trim and deduplicate strings while preserving first-seen order.

    Args:
        values: Candidate string values.

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


def _validate_finite_mapping(values: Mapping[str, object]) -> None:
    """Validate numeric mapping values are finite.

    Args:
        values: Candidate mapping.

    Raises:
        ValueError: If a numeric value is NaN or infinite.
    """
    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int | float):
            continue
        if not math.isfinite(float(value)):
            raise ValueError(f"Metric must be finite: {key}")


__all__ = [
    "CONSENT_RETENTION_POLICY_SCHEMA_VERSION",
    "DEFAULT_PRIMARY_GOVERNANCE_METRICS",
    "DEFAULT_SAFETY_GOVERNANCE_METRICS",
    "GOVERNANCE_FORBIDDEN_KEYS",
    "GOVERNANCE_REPORT_SCHEMA_VERSION",
    "REDACTED_EVALUATION_SCHEMA_VERSION",
    "ArtifactApprovalStatus",
    "ArtifactProvenance",
    "ArtifactType",
    "ConsentRetentionPolicySnapshot",
    "GovernanceGateMode",
    "GovernanceGateReport",
    "GovernancePipeline",
    "GovernanceStatus",
    "PipelineGovernanceState",
    "PipelineGovernanceStatus",
    "PromotionDecision",
    "RedactedEvaluationReport",
    "reject_governance_raw_fields",
]
