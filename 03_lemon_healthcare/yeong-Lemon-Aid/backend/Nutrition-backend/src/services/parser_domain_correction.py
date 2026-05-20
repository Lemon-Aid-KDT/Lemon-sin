"""Deterministic parser/domain correction learning helpers."""

from __future__ import annotations

import json
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import cast
from uuid import UUID

from src.config import Settings
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.parser_domain_correction import (
    FORBIDDEN_CORRECTION_KEYS,
    CorrectionScalar,
    DomainCorrectionAction,
    DomainCorrectionArtifactManifest,
    DomainCorrectionCandidate,
    DomainCorrectionCandidateStatus,
    DomainCorrectionRule,
    ParserCorrectionEvent,
    ParserCorrectionType,
)
from src.models.schemas.supplement import UserSupplementCreate
from src.models.schemas.supplement_parser import SupplementStructuredParseResultV2
from src.models.schemas.supplement_snapshot import (
    SupplementParsedSnapshotV3,
    SupplementSnapshotDomainCorrectionAudit,
    parse_supplement_snapshot,
)
from src.services.nutrient_code_matcher import NutrientAliasEntry

PARSER_DOMAIN_CORRECTION_WARNING_PREFIX = "parser_domain_correction"
PRIMARY_DOMAIN_CORRECTION_METRICS = (
    "ingredient_field_exact_rate",
    "numeric_exact_rate",
    "unit_exact_rate",
    "nutrient_code_candidate_hit_rate",
    "parser_success_rate",
)
SAFETY_DOMAIN_CORRECTION_METRICS = (
    "fabricated_field_count",
    "false_correction_count",
    "raw_text_leak_count",
)


class ParserDomainCorrectionError(ValueError):
    """Raised when parser/domain correction data is unsafe or invalid."""


@dataclass(frozen=True)
class DomainCorrectionApplication:
    """Runtime parser/domain correction decision.

    Attributes:
        alias_catalog_by_ingredient_index: Approved alias entries to use for
            nutrient-code candidate matching, keyed by ingredient index.
        unit_overrides_by_ingredient_index: Approved unit replacements keyed by ingredient index.
        audit_entries: Redacted rule application/reporting audit metadata.
        warnings: Safe preview warnings for UI review.
    """

    alias_catalog_by_ingredient_index: dict[int, tuple[NutrientAliasEntry, ...]]
    unit_overrides_by_ingredient_index: dict[int, str]
    audit_entries: tuple[SupplementSnapshotDomainCorrectionAudit, ...]
    warnings: tuple[str, ...]


def empty_domain_correction_application() -> DomainCorrectionApplication:
    """Return an empty runtime correction decision.

    Returns:
        Empty correction application result.
    """
    return DomainCorrectionApplication(
        alias_catalog_by_ingredient_index={},
        unit_overrides_by_ingredient_index={},
        audit_entries=(),
        warnings=(),
    )


def normalize_domain_text(value: str) -> str:
    """Normalize text for deterministic parser/domain correction matching.

    Args:
        value: Candidate label text or rule text.

    Returns:
        Unicode-normalized, case-folded, whitespace-collapsed text.
    """
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return " ".join(normalized.split())


def correction_value_hash(value: object) -> str:
    """Hash a preview value without storing the value itself.

    Args:
        value: Preview value to hash.

    Returns:
        Stable SHA-256 hash.
    """
    payload = json.dumps(
        _json_safe_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def build_parser_correction_events(
    *,
    preview: SupplementAnalysisRun | None,
    request: UserSupplementCreate,
    consent_scope: Sequence[str] = ("parser_domain_correction",),
    created_at: datetime | None = None,
) -> tuple[ParserCorrectionEvent, ...]:
    """Build field-level correction events from a confirmed supplement request.

    Args:
        preview: Source supplement analysis preview row.
        request: User-confirmed supplement creation request.
        consent_scope: Consent bucket names for downstream learning export.
        created_at: Optional timestamp for deterministic tests.

    Returns:
        Correction events. Empty when no safe OCR hash or no actual diff exists.
    """
    if preview is None or not preview.ocr_text_hash:
        return ()
    try:
        snapshot = parse_supplement_snapshot(preview.parsed_snapshot or {})
    except ValueError:
        return ()

    events: list[ParserCorrectionEvent] = []
    events.extend(
        _ingredient_correction_events(
            snapshot=snapshot,
            preview=preview,
            request=request,
            consent_scope=consent_scope,
            created_at=created_at,
        )
    )
    return tuple(events)


def mine_domain_correction_candidates(
    events: Sequence[ParserCorrectionEvent],
) -> tuple[DomainCorrectionCandidate, ...]:
    """Aggregate correction events into reviewable candidates.

    Args:
        events: User-confirmed correction events.

    Returns:
        Reviewable correction candidates.
    """
    grouped: dict[
        tuple[str, str, str],
        Counter[tuple[str, CorrectionScalar]],
    ] = defaultdict(Counter)
    event_ids: dict[
        tuple[str, str, str, tuple[str, CorrectionScalar]],
        list[UUID],
    ] = defaultdict(list)
    for event in events:
        key: tuple[str, str, str] = (
            event.correction_type,
            event.field_path,
            event.before_value_hash,
        )
        value_key = (_value_key(event.confirmed_value), event.confirmed_value)
        grouped[key][value_key] += 1
        event_ids[(*key, value_key)].append(event.event_id)

    candidates: list[DomainCorrectionCandidate] = []
    for key, counts in grouped.items():
        correction_type, field_path, before_value_hash = key
        conflict_count = max(0, len(counts) - 1)
        for value_key, support_count in counts.most_common():
            _, proposed_value = value_key
            status: DomainCorrectionCandidateStatus = (
                "needs_review" if conflict_count else "pending"
            )
            candidates.append(
                DomainCorrectionCandidate(
                    candidate_id=_candidate_id(key=key, value_key=value_key),
                    correction_type=cast(ParserCorrectionType, correction_type),
                    field_path=field_path,
                    before_value_hash=before_value_hash,
                    proposed_value=proposed_value,
                    support_count=support_count,
                    conflict_count=conflict_count,
                    status=status,
                    source_event_ids=event_ids[(*key, value_key)],
                )
            )
    return tuple(candidates)


def apply_parser_domain_corrections(
    parse_result: SupplementStructuredParseResultV2,
    settings: Settings,
) -> DomainCorrectionApplication:
    """Build runtime correction metadata for a validated parser result.

    Args:
        parse_result: Validated parser output.
        settings: Runtime settings controlling parser/domain correction.

    Returns:
        Correction application decision. Empty when disabled or no artifact exists.
    """
    if not settings.enable_parser_domain_correction:
        return empty_domain_correction_application()
    artifact = load_domain_correction_artifact(settings.parser_domain_correction_artifact_path)
    if artifact is None:
        return empty_domain_correction_application()

    apply_reviewed = settings.parser_domain_correction_mode == "apply_reviewed"
    alias_entries: dict[int, list[NutrientAliasEntry]] = defaultdict(list)
    unit_overrides: dict[int, str] = {}
    audit_entries: list[SupplementSnapshotDomainCorrectionAudit] = []
    warnings: list[str] = []

    for ingredient_index, ingredient in enumerate(parse_result.ingredients):
        for rule in approved_domain_correction_rules(artifact):
            action: DomainCorrectionAction = "applied" if apply_reviewed else "reported"
            if _ingredient_alias_rule_matches(rule, ingredient.display_name):
                audit_entries.append(
                    _audit_entry(rule=rule, action=action, ingredient_index=ingredient_index)
                )
                warnings.append(_warning(rule, action))
                if apply_reviewed and rule.nutrient_code:
                    alias_entries[ingredient_index].append(
                        NutrientAliasEntry(
                            nutrient_code=rule.nutrient_code,
                            display_name=rule.canonical_display_name or rule.replacement_value,
                            aliases=(rule.match_value, rule.replacement_value),
                            source_catalog=rule.source_catalog,
                        )
                    )
            if ingredient.unit and _unit_rule_matches(rule, ingredient.unit):
                audit_entries.append(
                    _audit_entry(rule=rule, action=action, ingredient_index=ingredient_index)
                )
                warnings.append(_warning(rule, action))
                if apply_reviewed:
                    unit_overrides[ingredient_index] = rule.replacement_value

    return DomainCorrectionApplication(
        alias_catalog_by_ingredient_index={
            index: tuple(entries) for index, entries in alias_entries.items()
        },
        unit_overrides_by_ingredient_index=unit_overrides,
        audit_entries=tuple(_dedupe_audit_entries(audit_entries)),
        warnings=tuple(_dedupe_strings(warnings)),
    )


def load_domain_correction_artifact(
    artifact_path: str | Path | None,
) -> DomainCorrectionArtifactManifest | None:
    """Load and validate a parser/domain correction artifact.

    Args:
        artifact_path: JSON artifact path. Missing paths are treated as no artifact.

    Returns:
        Validated artifact or None.

    Raises:
        ParserDomainCorrectionError: If the artifact contains unsafe fields or bad checksum.
    """
    if artifact_path is None:
        return None
    path = Path(artifact_path)
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    reject_forbidden_correction_fields(raw)
    artifact = DomainCorrectionArtifactManifest.model_validate(raw)
    validate_domain_correction_artifact_checksum(artifact)
    return artifact


def approved_domain_correction_rules(
    artifact: DomainCorrectionArtifactManifest,
) -> tuple[DomainCorrectionRule, ...]:
    """Return approved rules from an artifact.

    Args:
        artifact: Parser/domain correction artifact.

    Returns:
        Approved correction rules.
    """
    return tuple(rule for rule in artifact.rules if rule.rule_status == "approved")


def domain_correction_artifact_checksum(artifact: DomainCorrectionArtifactManifest) -> str:
    """Calculate a stable artifact checksum excluding its checksum field.

    Args:
        artifact: Parser/domain correction artifact.

    Returns:
        SHA-256 checksum.
    """
    payload = json.dumps(
        artifact.model_dump(mode="json", exclude={"checksum"}, exclude_none=True),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def with_domain_correction_artifact_checksum(
    artifact: DomainCorrectionArtifactManifest,
) -> DomainCorrectionArtifactManifest:
    """Return an artifact copy with a calculated checksum.

    Args:
        artifact: Parser/domain correction artifact.

    Returns:
        Artifact with checksum populated.
    """
    return artifact.model_copy(update={"checksum": domain_correction_artifact_checksum(artifact)})


def validate_domain_correction_artifact_checksum(
    artifact: DomainCorrectionArtifactManifest,
) -> None:
    """Validate an artifact checksum when one is present.

    Args:
        artifact: Parser/domain correction artifact.

    Raises:
        ParserDomainCorrectionError: If the checksum does not match.
    """
    if artifact.checksum is None:
        return
    expected = domain_correction_artifact_checksum(artifact)
    if artifact.checksum != expected:
        raise ParserDomainCorrectionError("Domain correction artifact checksum mismatch.")


def reject_forbidden_correction_fields(value: object) -> None:
    """Reject raw OCR/image/provider/user fields in correction artifacts.

    Args:
        value: Candidate nested object.

    Raises:
        ParserDomainCorrectionError: If forbidden raw-data keys are present.
    """
    if isinstance(value, Mapping):
        forbidden = FORBIDDEN_CORRECTION_KEYS.intersection(str(key).lower() for key in value)
        if forbidden:
            raise ParserDomainCorrectionError(
                f"Correction artifact contains forbidden raw field(s): {sorted(forbidden)}"
            )
        for nested_value in value.values():
            reject_forbidden_correction_fields(nested_value)
    elif isinstance(value, list):
        for item in value:
            reject_forbidden_correction_fields(item)


def evaluate_domain_correction_promotion_gate(
    *,
    baseline: Mapping[str, object],
    candidate: Mapping[str, object],
) -> dict[str, object]:
    """Evaluate whether a correction artifact can be promoted.

    Args:
        baseline: Baseline parser metrics from a frozen fixture set.
        candidate: Candidate parser/domain correction metrics from the same fixture set.

    Returns:
        Redacted promotion decision with aggregate metrics only.
    """
    errors: list[str] = []
    improved = False
    for metric in PRIMARY_DOMAIN_CORRECTION_METRICS:
        baseline_value = _metric_float(baseline.get(metric))
        candidate_value = _metric_float(candidate.get(metric))
        if candidate_value < baseline_value:
            errors.append(f"primary_metric_regressed:{metric}")
        if candidate_value > baseline_value:
            improved = True
    if not improved:
        errors.append("no_primary_metric_improved")
    for metric in SAFETY_DOMAIN_CORRECTION_METRICS:
        if _metric_float(candidate.get(metric)) > 0:
            errors.append(f"safety_metric_failed:{metric}")
    return {
        "promotable": not errors,
        "errors": errors,
        "primary_metrics": list(PRIMARY_DOMAIN_CORRECTION_METRICS),
        "safety_metrics": list(SAFETY_DOMAIN_CORRECTION_METRICS),
    }


def _ingredient_correction_events(
    *,
    snapshot: SupplementParsedSnapshotV3,
    preview: SupplementAnalysisRun,
    request: UserSupplementCreate,
    consent_scope: Sequence[str],
    created_at: datetime | None,
) -> tuple[ParserCorrectionEvent, ...]:
    """Build ingredient-level correction events.

    Args:
        snapshot: Parsed preview snapshot.
        preview: Source analysis run.
        request: User-confirmed payload.
        consent_scope: Consent bucket names.
        created_at: Optional fixed timestamp.

    Returns:
        Ingredient correction events.
    """
    events: list[ParserCorrectionEvent] = []
    if preview.ocr_text_hash is None:
        return ()
    event_created_at = created_at or datetime.now(UTC)
    for index, confirmed in enumerate(request.ingredients):
        if index >= len(snapshot.ingredients):
            continue
        preview_ingredient = snapshot.ingredients[index]
        if confirmed.display_name != preview_ingredient.display_name:
            events.append(
                ParserCorrectionEvent(
                    analysis_id=preview.id,
                    ocr_text_hash=preview.ocr_text_hash,
                    parser_algorithm_version=preview.algorithm_version,
                    field_path=f"ingredients[{index}].display_name",
                    correction_type="ingredient_alias",
                    before_value_hash=correction_value_hash(preview_ingredient.display_name),
                    confirmed_value=confirmed.display_name,
                    evidence_refs=preview_ingredient.evidence_refs,
                    consent_scope=list(consent_scope),
                    created_at=event_created_at,
                )
            )
        if confirmed.unit is not None and confirmed.unit != preview_ingredient.unit:
            events.append(
                ParserCorrectionEvent(
                    analysis_id=preview.id,
                    ocr_text_hash=preview.ocr_text_hash,
                    parser_algorithm_version=preview.algorithm_version,
                    field_path=f"ingredients[{index}].unit",
                    correction_type="unit_normalization",
                    before_value_hash=correction_value_hash(preview_ingredient.unit),
                    confirmed_value=confirmed.unit,
                    evidence_refs=preview_ingredient.evidence_refs,
                    consent_scope=list(consent_scope),
                    created_at=event_created_at,
                )
            )
        if confirmed.amount is not None and confirmed.amount != preview_ingredient.amount:
            events.append(
                ParserCorrectionEvent(
                    analysis_id=preview.id,
                    ocr_text_hash=preview.ocr_text_hash,
                    parser_algorithm_version=preview.algorithm_version,
                    field_path=f"ingredients[{index}].amount",
                    correction_type="amount_parse",
                    before_value_hash=correction_value_hash(preview_ingredient.amount),
                    confirmed_value=confirmed.amount,
                    evidence_refs=preview_ingredient.evidence_refs,
                    consent_scope=list(consent_scope),
                    created_at=event_created_at,
                )
            )
        if confirmed.nutrient_code and confirmed.nutrient_code not in {
            candidate.nutrient_code for candidate in preview_ingredient.nutrient_code_candidates
        }:
            events.append(
                ParserCorrectionEvent(
                    analysis_id=preview.id,
                    ocr_text_hash=preview.ocr_text_hash,
                    parser_algorithm_version=preview.algorithm_version,
                    field_path=f"ingredients[{index}].nutrient_code",
                    correction_type="nutrient_code_selection",
                    before_value_hash=correction_value_hash(
                        [
                            candidate.nutrient_code
                            for candidate in preview_ingredient.nutrient_code_candidates
                        ]
                    ),
                    confirmed_value=confirmed.nutrient_code,
                    evidence_refs=preview_ingredient.evidence_refs,
                    consent_scope=list(consent_scope),
                    created_at=event_created_at,
                )
            )
    return tuple(events)


def _ingredient_alias_rule_matches(rule: DomainCorrectionRule, display_name: str) -> bool:
    """Return whether an ingredient alias rule matches a display name.

    Args:
        rule: Correction rule.
        display_name: Ingredient display name.

    Returns:
        True when the approved alias rule matches exactly after normalization.
    """
    return (
        rule.correction_type == "ingredient_alias"
        and rule.field_path.endswith(".display_name")
        and normalize_domain_text(display_name) == normalize_domain_text(rule.match_value)
    )


def _unit_rule_matches(rule: DomainCorrectionRule, unit: str) -> bool:
    """Return whether a unit normalization rule matches a unit.

    Args:
        rule: Correction rule.
        unit: Ingredient unit.

    Returns:
        True when the approved unit rule matches exactly after normalization.
    """
    return (
        rule.correction_type == "unit_normalization"
        and rule.field_path.endswith(".unit")
        and normalize_domain_text(unit) == normalize_domain_text(rule.match_value)
    )


def _audit_entry(
    *,
    rule: DomainCorrectionRule,
    action: DomainCorrectionAction,
    ingredient_index: int,
) -> SupplementSnapshotDomainCorrectionAudit:
    """Build redacted snapshot audit metadata for one rule decision.

    Args:
        rule: Correction rule.
        action: Whether the rule was reported or applied.
        ingredient_index: Ingredient index affected by the rule.

    Returns:
        Snapshot audit entry.
    """
    return SupplementSnapshotDomainCorrectionAudit(
        rule_id=rule.rule_id,
        correction_type=rule.correction_type,
        field_path=rule.field_path,
        action=action,
        ingredient_index=ingredient_index,
    )


def _warning(rule: DomainCorrectionRule, action: DomainCorrectionAction) -> str:
    """Build a safe parser/domain correction warning.

    Args:
        rule: Correction rule.
        action: Rule decision.

    Returns:
        Safe warning string containing only rule metadata.
    """
    return f"{PARSER_DOMAIN_CORRECTION_WARNING_PREFIX}:{action}:{rule.rule_id}"


def _candidate_id(
    *,
    key: tuple[str, str, str],
    value_key: tuple[str, CorrectionScalar],
) -> str:
    """Build a deterministic correction candidate id.

    Args:
        key: Candidate grouping key.
        value_key: Proposed value key.

    Returns:
        Candidate identifier.
    """
    payload = json.dumps([*key, value_key[0]], sort_keys=True, separators=(",", ":"))
    return f"pdc-{sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def _value_key(value: CorrectionScalar) -> str:
    """Build a normalized value key for aggregation.

    Args:
        value: Candidate scalar value.

    Returns:
        Normalized key.
    """
    if isinstance(value, str):
        return normalize_domain_text(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _json_safe_value(value: object) -> object:
    """Convert values into JSON-stable primitives.

    Args:
        value: Candidate value.

    Returns:
        JSON-stable value.
    """
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, tuple):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe_value(nested_value) for key, nested_value in value.items()}
    return value


def _metric_float(value: object) -> float:
    """Return a numeric metric value or zero.

    Args:
        value: Candidate metric value.

    Returns:
        Float metric value.
    """
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _dedupe_strings(values: Iterable[str]) -> list[str]:
    """Deduplicate strings while preserving first-seen order.

    Args:
        values: Candidate strings.

    Returns:
        Deduplicated strings.
    """
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _dedupe_audit_entries(
    entries: Iterable[SupplementSnapshotDomainCorrectionAudit],
) -> list[SupplementSnapshotDomainCorrectionAudit]:
    """Deduplicate audit entries while preserving order.

    Args:
        entries: Candidate audit entries.

    Returns:
        Deduplicated audit entries.
    """
    seen: set[tuple[str, str, str, str, int | None]] = set()
    deduped: list[SupplementSnapshotDomainCorrectionAudit] = []
    for entry in entries:
        key = (
            entry.rule_id,
            entry.correction_type,
            entry.field_path,
            entry.action,
            entry.ingredient_index,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


__all__ = [
    "PARSER_DOMAIN_CORRECTION_WARNING_PREFIX",
    "PRIMARY_DOMAIN_CORRECTION_METRICS",
    "SAFETY_DOMAIN_CORRECTION_METRICS",
    "DomainCorrectionApplication",
    "ParserDomainCorrectionError",
    "apply_parser_domain_corrections",
    "approved_domain_correction_rules",
    "build_parser_correction_events",
    "correction_value_hash",
    "domain_correction_artifact_checksum",
    "empty_domain_correction_application",
    "evaluate_domain_correction_promotion_gate",
    "load_domain_correction_artifact",
    "mine_domain_correction_candidates",
    "normalize_domain_text",
    "reject_forbidden_correction_fields",
    "validate_domain_correction_artifact_checksum",
    "with_domain_correction_artifact_checksum",
]
