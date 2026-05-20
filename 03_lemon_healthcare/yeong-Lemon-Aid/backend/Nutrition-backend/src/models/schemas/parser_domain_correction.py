"""Schemas for parser/domain correction learning artifacts."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Literal, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PARSER_CORRECTION_EVENT_SCHEMA_VERSION: Literal["parser-correction-event-v1"] = (
    "parser-correction-event-v1"
)
DOMAIN_CORRECTION_ARTIFACT_SCHEMA_VERSION: Literal["domain-correction-artifact-v1"] = (
    "domain-correction-artifact-v1"
)

ParserCorrectionType = Literal[
    "ingredient_alias",
    "unit_normalization",
    "amount_parse",
    "ocr_confusion",
    "row_association",
    "section_anchor",
    "nutrient_code_selection",
]
DomainCorrectionCandidateStatus = Literal["pending", "needs_review", "approved", "rejected"]
DomainCorrectionRuleStatus = Literal["pending", "approved", "rejected", "disabled"]
DomainCorrectionAction = Literal["reported", "applied"]
CorrectionScalar = str | int | float | bool | None

CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
FORBIDDEN_CORRECTION_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "exif",
        "file_name",
        "filename",
        "gps",
        "image_bytes",
        "ocr_text",
        "provider_payload",
        "raw_image",
        "raw_ocr_text",
        "raw_provider_payload",
        "request_headers",
        "service_key",
        "user_id",
    }
)


class ParserCorrectionEvent(BaseModel):
    """One user-confirmed parser/domain correction diff.

    Attributes:
        schema_version: Fixed event schema version.
        event_id: Pseudonymous correction event identifier.
        analysis_id: Supplement analysis preview identifier.
        ocr_text_hash: HMAC/SHA hash of the OCR text without storing raw OCR text.
        parser_algorithm_version: Parser algorithm version that produced the preview.
        field_path: Structured field path that was corrected.
        correction_type: Category of correction represented by this event.
        before_value_hash: SHA-256 hash of the preview value.
        confirmed_value: User-confirmed value.
        evidence_refs: Snapshot evidence ids that supported the preview field.
        consent_scope: Consent bucket names captured at export time.
        created_at: Server-side event creation time.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["parser-correction-event-v1"] = PARSER_CORRECTION_EVENT_SCHEMA_VERSION
    event_id: UUID = Field(default_factory=uuid4)
    analysis_id: UUID
    ocr_text_hash: str = Field(min_length=64, max_length=128)
    parser_algorithm_version: str = Field(min_length=1, max_length=64)
    field_path: str = Field(min_length=1, max_length=180)
    correction_type: ParserCorrectionType
    before_value_hash: str = Field(min_length=64, max_length=64)
    confirmed_value: CorrectionScalar = None
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)
    consent_scope: list[str] = Field(min_length=1, max_length=20)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("field_path")
    @classmethod
    def validate_field_path(cls, value: str) -> str:
        """Validate field paths are bounded metadata, not raw text.

        Args:
            value: Candidate field path.

        Returns:
            Validated field path.

        Raises:
            ValueError: If the field path contains control characters.
        """
        return _validate_safe_text(value, field_name="field_path")

    @field_validator("confirmed_value")
    @classmethod
    def validate_confirmed_value(cls, value: CorrectionScalar) -> CorrectionScalar:
        """Validate confirmed scalar values do not contain unsafe text delimiters.

        Args:
            value: Candidate confirmed scalar.

        Returns:
            Validated scalar value.

        Raises:
            ValueError: If the value contains tab, newline, or control characters.
        """
        if isinstance(value, str):
            return _validate_safe_text(value, field_name="confirmed_value")
        return value

    @field_validator("evidence_refs", "consent_scope")
    @classmethod
    def normalize_string_lists(cls, values: list[str]) -> list[str]:
        """Normalize bounded string lists while preserving order.

        Args:
            values: Candidate string values.

        Returns:
            Trimmed unique strings.
        """
        return _normalize_unique_strings(values)

    @model_validator(mode="after")
    def validate_correction_scope(self) -> Self:
        """Validate correction type and field path compatibility.

        Returns:
            Validated correction event.

        Raises:
            ValueError: If amount corrections are attached to non-amount fields.
        """
        if self.correction_type == "amount_parse" and not (
            self.field_path.endswith(".amount") or self.field_path.endswith(".amount_text")
        ):
            raise ValueError("amount_parse corrections must target amount or amount_text fields.")
        return self


class DomainCorrectionCandidate(BaseModel):
    """Aggregated parser/domain correction candidate awaiting review.

    Attributes:
        candidate_id: Stable candidate identifier.
        correction_type: Correction category.
        field_path: Field path pattern for the candidate.
        before_value_hash: Hash of the preview value represented by this candidate.
        proposed_value: Proposed canonical or corrected value.
        support_count: Number of user-confirmed events supporting the value.
        conflict_count: Number of competing confirmed values.
        status: Candidate review status.
        source_event_ids: Source correction event ids.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    candidate_id: str = Field(min_length=8, max_length=160)
    correction_type: ParserCorrectionType
    field_path: str = Field(min_length=1, max_length=180)
    before_value_hash: str = Field(min_length=64, max_length=64)
    proposed_value: CorrectionScalar = None
    support_count: int = Field(ge=1, le=1_000_000)
    conflict_count: int = Field(default=0, ge=0, le=1_000_000)
    status: DomainCorrectionCandidateStatus = "pending"
    source_event_ids: list[UUID] = Field(default_factory=list, max_length=500)

    @field_validator("field_path")
    @classmethod
    def validate_field_path(cls, value: str) -> str:
        """Validate candidate field path text.

        Args:
            value: Candidate field path.

        Returns:
            Validated field path.
        """
        return _validate_safe_text(value, field_name="field_path")

    @field_validator("proposed_value")
    @classmethod
    def validate_proposed_value(cls, value: CorrectionScalar) -> CorrectionScalar:
        """Validate candidate proposed value text.

        Args:
            value: Candidate proposed value.

        Returns:
            Validated scalar value.
        """
        if isinstance(value, str):
            return _validate_safe_text(value, field_name="proposed_value")
        return value

    @model_validator(mode="after")
    def validate_status_matches_conflicts(self) -> Self:
        """Ensure conflicted candidates stay in review.

        Returns:
            Validated candidate.
        """
        if self.conflict_count > 0 and self.status == "pending":
            self.status = "needs_review"
        return self


class DomainCorrectionRule(BaseModel):
    """One reviewed parser/domain correction rule.

    Attributes:
        rule_id: Stable rule identifier.
        rule_status: Review status; only approved rules can run automatically.
        correction_type: Correction category.
        field_path: Field path pattern where the rule can apply.
        match_value: Value matched after domain normalization.
        replacement_value: Canonical value or normalized replacement.
        canonical_display_name: Optional display name for nutrient alias rules.
        nutrient_code: Optional internal nutrient code for alias candidates.
        source_catalog: Catalog label used in emitted nutrient-code candidates.
        confidence: Rule confidence assigned by review or evaluation.
        evidence_count: Number of confirmed events supporting the rule.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    rule_id: str = Field(min_length=4, max_length=160)
    rule_status: DomainCorrectionRuleStatus
    correction_type: ParserCorrectionType
    field_path: str = Field(min_length=1, max_length=180)
    match_value: str = Field(min_length=1, max_length=160)
    replacement_value: str = Field(min_length=1, max_length=160)
    canonical_display_name: str | None = Field(default=None, max_length=160)
    nutrient_code: str | None = Field(default=None, max_length=80)
    source_catalog: str = Field(default="domain_correction_artifact", max_length=80)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_count: int = Field(default=1, ge=1, le=1_000_000)

    @field_validator("field_path", "match_value", "replacement_value", "source_catalog")
    @classmethod
    def validate_rule_text(cls, value: str) -> str:
        """Validate required rule text fields.

        Args:
            value: Candidate text.

        Returns:
            Validated text.
        """
        return _validate_safe_text(value, field_name="rule_text")

    @field_validator("canonical_display_name", "nutrient_code")
    @classmethod
    def validate_optional_rule_text(cls, value: str | None) -> str | None:
        """Validate optional rule text fields.

        Args:
            value: Candidate optional text.

        Returns:
            Validated optional text.
        """
        if value is None:
            return None
        return _validate_safe_text(value, field_name="rule_text")

    @model_validator(mode="after")
    def validate_rule_payload(self) -> Self:
        """Validate correction-type-specific rule fields.

        Returns:
            Validated rule.

        Raises:
            ValueError: If an automatic rule would apply outside its safe field scope.
        """
        if self.correction_type == "amount_parse" and not (
            self.field_path.endswith(".amount") or self.field_path.endswith(".amount_text")
        ):
            raise ValueError("amount_parse rules must target amount or amount_text fields.")
        if self.correction_type == "ingredient_alias" and self.nutrient_code is None:
            raise ValueError("ingredient_alias rules require nutrient_code.")
        return self


class DomainCorrectionArtifactManifest(BaseModel):
    """Versioned reviewed parser/domain correction artifact.

    Attributes:
        schema_version: Fixed artifact schema version.
        domain_dictionary_version: Version label for domain dictionary rules.
        confusion_map_version: Version label for OCR confusion rules.
        created_from_manifest_checksum: Checksum of the source correction manifest.
        checksum: Optional checksum of this artifact, excluding the checksum field.
        rules: Reviewed correction rules.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["domain-correction-artifact-v1"] = (
        DOMAIN_CORRECTION_ARTIFACT_SCHEMA_VERSION
    )
    domain_dictionary_version: str = Field(min_length=1, max_length=80)
    confusion_map_version: str = Field(min_length=1, max_length=80)
    created_from_manifest_checksum: str = Field(min_length=8, max_length=128)
    checksum: str | None = Field(default=None, min_length=64, max_length=64)
    rules: list[DomainCorrectionRule] = Field(default_factory=list, max_length=10_000)


def _validate_safe_text(value: str, *, field_name: str) -> str:
    """Reject text delimiters and control characters in correction fields.

    Args:
        value: Candidate text.
        field_name: Field name for validation errors.

    Returns:
        Validated text.

    Raises:
        ValueError: If the text contains tab, newline, or control characters.
    """
    if "\t" in value or "\n" in value or "\r" in value or CONTROL_CHARACTER_PATTERN.search(value):
        raise ValueError(f"{field_name} must not contain tab, newline, or control characters.")
    return value


def _normalize_unique_strings(values: list[str]) -> list[str]:
    """Normalize a string list while preserving first-seen order.

    Args:
        values: Candidate string values.

    Returns:
        Trimmed non-empty strings with duplicates removed.
    """
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = _validate_safe_text(value.strip(), field_name="list value")
        if not stripped or stripped in seen:
            continue
        normalized.append(stripped)
        seen.add(stripped)
    return normalized


__all__ = [
    "DOMAIN_CORRECTION_ARTIFACT_SCHEMA_VERSION",
    "FORBIDDEN_CORRECTION_KEYS",
    "PARSER_CORRECTION_EVENT_SCHEMA_VERSION",
    "CorrectionScalar",
    "DomainCorrectionAction",
    "DomainCorrectionArtifactManifest",
    "DomainCorrectionCandidate",
    "DomainCorrectionCandidateStatus",
    "DomainCorrectionRule",
    "DomainCorrectionRuleStatus",
    "ParserCorrectionEvent",
    "ParserCorrectionType",
]
