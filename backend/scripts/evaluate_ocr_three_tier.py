"""Generate redacted OCR 3-tier fixture evaluation reports.

The script consumes JSONL fixture rows and optional provider observations. It
does not call real OCR providers; smoke tests for Google/CLOVA remain explicit
opt-in gates. This keeps report generation reproducible and prevents raw image
or raw OCR text from being written into artifacts.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

RAW_FORBIDDEN_KEYS = {"image_bytes", "raw_image", "raw_ocr_text", "ocr_text"}
BOUNDED_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$", re.IGNORECASE)
PENDING_REVIEW_WARNING = "ground_truth_pending_human_review"
PROVISIONAL_VERIFICATION_STATUS = "provisional"
AUTO_EXPECTED_WARNING = "auto_expected_requires_human_verification"
EXPECTED_WARNING_QUALITY_CODES = {
    "compound_expected_ingredient_name",
}
EXPECTED_NAME_SEPARATOR_PATTERN = re.compile(r"\s*(?:,|\uff0c|\u3001)\s*")
OCR_LLM_PREVIEW_SOURCE = "ocr_llm_preview"
MIN_SCOREABLE_OCR_LLM_EXPECTED_CONFIDENCE = 0.85
NON_INGREDIENT_HEADING_NAMES = {
    "ingredient",
    "ingredients",
    "nutrition facts",
    "other ingredients",
    "supplement facts",
}
MIN_EXPECTED_NAME_PART_CHARS = 2
MAX_EXPECTED_NAME_PART_CHARS = 80
IMAGE_INPUT_ERROR_CODES = {
    "image_decode_error",
    "image_missing",
    "image_read_error",
    "image_write_error",
    "invalid_image",
    "missing_image",
}
PROVIDER_SETUP_ERROR_CODES = {
    "local_ocr_disabled",
    "ocr_dependency_missing",
    "ocr_provider_initialization",
    "provider_configuration_error",
}
OCR_OUTPUT_ERROR_CODES = {
    "ocr_empty_text",
    "ocr_low_confidence",
}
PACKAGING_TOKEN_PATTERNS = (
    # Bad auto-seeds observed in 16 chronic fixtures: "g (", "g X30포(", "g(".
    r"^(?:g|mg|kg|ml|l)\s*(?:x\s*)?\d*\s*(?:포|정|캡슐|개입)?\s*\(?$",
    # Bad auto-seeds observed in 16 chronic fixtures: "정(", "정x 3개입(".
    r"^정\s*(?:x\s*)?\d*\s*(?:개입)?\s*\(?$",
    r"^\d+\s*(?:정|포|캡슐|개입)\s*\(?$",
)


@dataclass
class ProviderMetrics:
    """Aggregate metrics for one OCR provider observation set."""

    calls: int = 0
    non_empty_count: int = 0
    parser_success_count: int = 0
    total_latency_ms: float = 0.0
    ingredient_name_matches: int = 0
    ingredient_name_total: int = 0
    scoreable_ingredient_name_matches: int = 0
    scoreable_ingredient_name_total: int = 0
    errors: int = 0
    # LLM parser metrics (separate from OCR regex matching).
    llm_parse_attempt_count: int = 0
    llm_parse_success_count: int = 0
    llm_ingredient_name_matches: int = 0
    llm_ingredient_name_total: int = 0
    # Korean/English segmented edit-rate metrics (averaged across observations).
    cer_ko_sum: float = 0.0
    cer_ko_count: int = 0
    cer_en_sum: float = 0.0
    cer_en_count: int = 0
    wer_ko_sum: float = 0.0
    wer_ko_count: int = 0
    wer_en_sum: float = 0.0
    wer_en_count: int = 0
    # Chronic-disease (B-persona) grouped ingredient accuracy.
    ingredient_matches_by_condition: dict[str, int] = field(default_factory=dict)
    ingredient_total_by_condition: dict[str, int] = field(default_factory=dict)
    scoreable_ingredient_matches_by_condition: dict[str, int] = field(default_factory=dict)
    scoreable_ingredient_total_by_condition: dict[str, int] = field(default_factory=dict)
    # Bounded error diagnostics. These never include raw provider messages.
    error_codes: dict[str, int] = field(default_factory=dict)
    error_stages: dict[str, int] = field(default_factory=dict)
    error_fixture_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        """Return serializable metrics.

        Returns:
            Provider metrics as a dictionary.
        """
        return {
            "calls": self.calls,
            "text_non_empty_rate": _rate(self.non_empty_count, self.calls),
            "parser_success_rate": _rate(self.parser_success_count, self.calls),
            "average_latency_ms": (self.total_latency_ms / self.calls if self.calls else None),
            "ingredient_name_exact_rate": _rate(
                self.ingredient_name_matches,
                self.ingredient_name_total,
            ),
            "scoreable_ingredient_name_exact_rate": _rate(
                self.scoreable_ingredient_name_matches,
                self.scoreable_ingredient_name_total,
            ),
            "errors": self.errors,
            "llm_parse_attempt_count": self.llm_parse_attempt_count,
            "llm_parse_success_rate": _rate(
                self.llm_parse_success_count,
                self.llm_parse_attempt_count,
            ),
            "llm_ingredient_name_exact_rate": _rate(
                self.llm_ingredient_name_matches,
                self.llm_ingredient_name_total,
            ),
            "cer_ko_avg": _average(self.cer_ko_sum, self.cer_ko_count),
            "cer_en_avg": _average(self.cer_en_sum, self.cer_en_count),
            "wer_ko_avg": _average(self.wer_ko_sum, self.wer_ko_count),
            "wer_en_avg": _average(self.wer_en_sum, self.wer_en_count),
            "accuracy_by_condition": {
                condition: _rate(
                    self.ingredient_matches_by_condition.get(condition, 0),
                    total,
                )
                for condition, total in sorted(self.ingredient_total_by_condition.items())
            },
            "scoreable_accuracy_by_condition": {
                condition: _rate(
                    self.scoreable_ingredient_matches_by_condition.get(condition, 0),
                    total,
                )
                for condition, total in sorted(self.scoreable_ingredient_total_by_condition.items())
            },
            "error_codes": dict(sorted(self.error_codes.items())),
            "error_stages": dict(sorted(self.error_stages.items())),
            "error_fixture_ids": sorted(self.error_fixture_ids),
        }


@dataclass(frozen=True)
class ExpectedIngredientQuality:
    """Expected ingredient names and quality diagnostics for one fixture.

    Attributes:
        names: All normalized expected ingredient names for legacy metrics.
        scoreable_names: Normalized expected names after quality filtering.
        warnings: Bounded warning rows. Raw OCR text is never included.
        is_provisional: Whether the expected fixture still needs human review.
    """

    names: set[str]
    scoreable_names: set[str]
    warnings: list[dict[str, object]]
    is_provisional: bool


@dataclass
class EvaluationAccumulator:
    """Aggregate OCR fixture evaluation state."""

    fixture_count: int = 0
    missing_image_count: int = 0
    observation_count: int = 0
    scoreable_fixture_count: int = 0
    provisional_fixture_count: int = 0
    expected_quality_warnings: list[dict[str, object]] = field(default_factory=list)
    providers: dict[str, ProviderMetrics] = field(
        default_factory=lambda: defaultdict(ProviderMetrics)
    )


def main() -> None:
    """Run the report generator from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    summary = evaluate_manifest(args.manifest)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "ocr-three-tier-evaluation.json"
    markdown_path = args.output_dir / "ocr-three-tier-evaluation.md"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown(summary), encoding="utf-8")


def evaluate_manifest(manifest_path: Path) -> dict[str, object]:
    """Evaluate a JSONL manifest and return redacted aggregate metrics.

    Args:
        manifest_path: JSONL fixture manifest path.

    Returns:
        Aggregate report summary.

    Raises:
        ValueError: If manifest rows contain raw image or raw OCR text fields.
    """
    accumulator = EvaluationAccumulator()
    for row in _read_manifest_rows(manifest_path):
        _reject_raw_fields(row)
        accumulator.fixture_count += 1
        image_path = row.get("image_path")
        if isinstance(image_path, str) and not (manifest_path.parent / image_path).exists():
            accumulator.missing_image_count += 1

        expected_quality = _expected_ingredient_quality(row.get("expected"), row.get("fixture_id"))
        if expected_quality.scoreable_names:
            accumulator.scoreable_fixture_count += 1
        if expected_quality.is_provisional:
            accumulator.provisional_fixture_count += 1
        accumulator.expected_quality_warnings.extend(expected_quality.warnings)
        expected_conditions = _expected_chronic_conditions(row.get("expected"))
        observations = row.get("observations", [])
        if not isinstance(observations, list):
            continue
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            _reject_raw_fields(observation)
            _add_observation(
                accumulator,
                observation=observation,
                fixture_id=row.get("fixture_id"),
                expected_names=expected_quality.names,
                scoreable_expected_names=expected_quality.scoreable_names,
                expected_conditions=expected_conditions,
            )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest": str(manifest_path),
        "fixture_count": accumulator.fixture_count,
        "missing_image_count": accumulator.missing_image_count,
        "observation_count": accumulator.observation_count,
        "scoreable_fixture_count": accumulator.scoreable_fixture_count,
        "provisional_fixture_count": accumulator.provisional_fixture_count,
        "expected_quality_warnings": accumulator.expected_quality_warnings,
        "providers": {
            provider: metrics.as_dict()
            for provider, metrics in sorted(accumulator.providers.items())
        },
        "raw_artifacts_stored": False,
        "raw_ocr_text_stored": False,
    }


def _read_manifest_rows(manifest_path: Path) -> list[dict[str, object]]:
    """Read JSONL manifest rows.

    Args:
        manifest_path: JSONL manifest path.

    Returns:
        Manifest rows.
    """
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError(f"Manifest line {line_number} must be a JSON object.")
        rows.append(parsed)
    return rows


def _reject_raw_fields(value: object) -> None:
    """Reject raw image or raw OCR text fields recursively.

    Args:
        value: Candidate manifest value.

    Raises:
        ValueError: If a forbidden raw-data key is present.
    """
    if isinstance(value, dict):
        forbidden = RAW_FORBIDDEN_KEYS.intersection(value.keys())
        if forbidden:
            raise ValueError(f"Manifest contains forbidden raw field(s): {sorted(forbidden)}")
        for nested_value in value.values():
            _reject_raw_fields(nested_value)
    elif isinstance(value, list):
        for item in value:
            _reject_raw_fields(item)


def _expected_ingredient_quality(
    value: object,
    fixture_id: object,
) -> ExpectedIngredientQuality:
    """Extract expected ingredient names with quality diagnostics.

    Args:
        value: Expected fixture object.
        fixture_id: Fixture identifier used only in bounded warning metadata.

    Returns:
        Expected ingredient quality object.
    """
    if not isinstance(value, dict):
        return ExpectedIngredientQuality(
            names=set(),
            scoreable_names=set(),
            warnings=[],
            is_provisional=False,
        )

    warnings: list[dict[str, object]] = []
    is_provisional = _expected_is_provisional(value)
    if is_provisional:
        warnings.append(
            _expected_quality_warning(
                fixture_id=fixture_id,
                code="provisional_expected_fixture",
            )
        )
    expected_warnings = value.get("warnings")
    if isinstance(expected_warnings, list):
        for warning in expected_warnings:
            if warning in EXPECTED_WARNING_QUALITY_CODES:
                warnings.append(
                    _expected_quality_warning(
                        fixture_id=fixture_id,
                        code=warning,
                    )
                )

    ingredients = value.get("ingredients")
    if not isinstance(ingredients, list):
        return ExpectedIngredientQuality(
            names=set(),
            scoreable_names=set(),
            warnings=warnings,
            is_provisional=is_provisional,
        )
    names: set[str] = set()
    scoreable_names: set[str] = set()
    for index, ingredient in enumerate(ingredients):
        if not isinstance(ingredient, dict):
            continue
        names_for_ingredient = _expected_ingredient_display_names(ingredient)
        if len(names_for_ingredient) > 1:
            warnings.append(
                _expected_quality_warning(
                    fixture_id=fixture_id,
                    code="compound_expected_ingredient_name",
                    ingredient_index=index,
                )
            )
        for name in names_for_ingredient:
            normalized_name = _normalize_token(name)
            if not normalized_name:
                continue
            names.add(normalized_name)
            exclusion_code = _expected_scoreable_exclusion_code(name, ingredient)
            if exclusion_code is not None:
                warnings.append(
                    _expected_quality_warning(
                        fixture_id=fixture_id,
                        code=exclusion_code,
                        ingredient_index=index,
                    )
                )
                continue
            scoreable_names.add(normalized_name)
    return ExpectedIngredientQuality(
        names=names,
        scoreable_names=scoreable_names,
        warnings=warnings,
        is_provisional=is_provisional,
    )


def _expected_ingredient_display_names(ingredient: dict[str, object]) -> list[str]:
    """Return expected ingredient names from legacy or V3 shapes.

    Args:
        ingredient: Expected ingredient object.

    Returns:
        One or more ingredient display names.
    """
    for key in ("name", "display_name", "normalized_name"):
        value = ingredient.get(key)
        if isinstance(value, str) and value.strip():
            return _split_expected_ingredient_name(value.strip(), ingredient)
    return []


def _split_expected_ingredient_name(value: str, ingredient: dict[str, object]) -> list[str]:
    """Split bounded compound expected names when no dose is attached.

    Args:
        value: Expected ingredient display name.
        ingredient: Full expected ingredient row.

    Returns:
        A list of names. Dose-bearing rows are kept as one item.
    """
    if ingredient.get("amount") is not None or ingredient.get("unit") is not None:
        return [value]
    parts = [
        part.strip()
        for part in EXPECTED_NAME_SEPARATOR_PATTERN.split(value)
        if _looks_like_expected_name_part(part)
    ]
    return parts if len(parts) > 1 else [value]


def _looks_like_expected_name_part(value: str) -> bool:
    """Return whether a split expected-name part is safe to score.

    Args:
        value: Candidate expected-name fragment.

    Returns:
        True for bounded alphabetic ingredient-name fragments.
    """
    stripped = value.strip()
    return (
        MIN_EXPECTED_NAME_PART_CHARS <= len(stripped) <= MAX_EXPECTED_NAME_PART_CHARS
        and bool(re.search(r"[A-Za-z가-힣]", stripped))
        and not _is_packaging_quantity_token(stripped)
    )


def _expected_is_provisional(value: dict[str, object]) -> bool:
    """Return whether expected data is provisional or pending review.

    Args:
        value: Expected fixture object.

    Returns:
        True when the fixture should not be treated as human-verified.
    """
    if value.get("verification_status") == PROVISIONAL_VERIFICATION_STATUS:
        return True
    warnings = value.get("warnings")
    if isinstance(warnings, list) and (
        PENDING_REVIEW_WARNING in warnings or AUTO_EXPECTED_WARNING in warnings
    ):
        return True
    ingredients = value.get("ingredients")
    if not isinstance(ingredients, list):
        return False
    for ingredient in ingredients:
        if not isinstance(ingredient, dict):
            continue
        if ingredient.get("verification_status") == PROVISIONAL_VERIFICATION_STATUS:
            return True
    return False


def _expected_quality_warning(
    *,
    fixture_id: object,
    code: str,
    ingredient_index: int | None = None,
) -> dict[str, object]:
    """Build a bounded expected-quality warning row.

    Args:
        fixture_id: Fixture identifier.
        code: Stable warning code.
        ingredient_index: Optional ingredient index.

    Returns:
        Warning row that never includes raw OCR text or provider payloads.
    """
    warning: dict[str, object] = {"code": code}
    if isinstance(fixture_id, str) and fixture_id:
        warning["fixture_id"] = fixture_id
    if ingredient_index is not None:
        warning["ingredient_index"] = ingredient_index
    return warning


def _is_packaging_quantity_token(value: str) -> bool:
    """Return whether a candidate is packaging quantity, not ingredient.

    Args:
        value: Expected ingredient candidate.

    Returns:
        True for auto-seed contaminants such as ``g X30포(`` or ``정x 3개입(``.
    """
    normalized = _normalize_token(value)
    if not normalized:
        return False
    return any(
        re.fullmatch(pattern, normalized, re.IGNORECASE) for pattern in PACKAGING_TOKEN_PATTERNS
    )


def _expected_scoreable_exclusion_code(
    name: str,
    ingredient: dict[str, object],
) -> str | None:
    """Return why an expected ingredient should not be scoreable.

    Args:
        name: Candidate expected ingredient name.
        ingredient: Full expected ingredient row.

    Returns:
        Bounded warning code, or None when the row is scoreable.
    """
    if _is_packaging_quantity_token(name):
        return "packaging_token_expected_ingredient"
    if _is_non_ingredient_heading_name(name):
        return "non_ingredient_heading_expected"
    if _is_low_confidence_ocr_llm_expected(ingredient):
        return "low_confidence_expected_ingredient"
    return None


def _is_non_ingredient_heading_name(value: str) -> bool:
    """Return whether an expected name is a label heading, not an ingredient.

    Args:
        value: Expected ingredient candidate.

    Returns:
        True for section headings that should not enter scoreable KPI denominators.
    """
    return _normalize_token(value) in NON_INGREDIENT_HEADING_NAMES


def _is_low_confidence_ocr_llm_expected(ingredient: dict[str, object]) -> bool:
    """Return whether a provisional OCR LLM expected row is too weak to score.

    Args:
        ingredient: Expected ingredient row from the manifest.

    Returns:
        True when an ``ocr_llm_preview`` row is below the scoreable confidence
        floor. Human-reviewed rows are not filtered by this helper.
    """
    if ingredient.get("source") != OCR_LLM_PREVIEW_SOURCE:
        return False
    confidence = ingredient.get("confidence")
    if not isinstance(confidence, int | float):
        return False
    return float(confidence) < MIN_SCOREABLE_OCR_LLM_EXPECTED_CONFIDENCE


def _add_observation(
    accumulator: EvaluationAccumulator,
    *,
    observation: dict[str, object],
    fixture_id: object,
    expected_names: set[str],
    scoreable_expected_names: set[str],
    expected_conditions: list[str] | None = None,
) -> None:
    """Add one provider observation to aggregate metrics.

    Args:
        accumulator: Mutable aggregate state.
        observation: Observation row.
        fixture_id: Parent fixture id. Used only for bounded diagnostics.
        expected_names: Expected normalized ingredient names.
        scoreable_expected_names: Quality-filtered expected ingredient names.
        expected_conditions: Chronic-disease indications declared in the V3
            ``expected.chronic_disease_indications`` field. Used to bucket
            ingredient-accuracy contributions per B-persona condition.
    """
    provider = observation.get("provider")
    if not isinstance(provider, str) or not provider:
        return
    accumulator.observation_count += 1
    metrics = accumulator.providers[provider]
    metrics.calls += 1

    if observation.get("text_non_empty") is True:
        metrics.non_empty_count += 1
    if observation.get("parser_success") is True:
        metrics.parser_success_count += 1
    if observation.get("error") is True or observation.get("status") == "error":
        metrics.errors += 1
        _add_provider_error_diagnostics(
            metrics,
            observation=observation,
            fixture_id=fixture_id,
        )

    latency_ms = observation.get("latency_ms")
    if isinstance(latency_ms, int | float) and latency_ms >= 0:
        metrics.total_latency_ms += float(latency_ms)

    observed_names = _observed_ingredient_names(observation.get("parsed_ingredients"))
    match_count = _ingredient_match_count(
        expected_names=expected_names,
        observed_names=observed_names,
    )
    if match_count is not None:
        metrics.ingredient_name_total += len(expected_names)
        metrics.ingredient_name_matches += match_count
        _add_condition_accuracy(
            total_by_condition=metrics.ingredient_total_by_condition,
            matches_by_condition=metrics.ingredient_matches_by_condition,
            expected_conditions=expected_conditions,
            expected_total=len(expected_names),
            match_count=match_count,
        )
    scoreable_match_count = _ingredient_match_count(
        expected_names=scoreable_expected_names,
        observed_names=observed_names,
    )
    if scoreable_match_count is not None:
        metrics.scoreable_ingredient_name_total += len(scoreable_expected_names)
        metrics.scoreable_ingredient_name_matches += scoreable_match_count
        _add_condition_accuracy(
            total_by_condition=metrics.scoreable_ingredient_total_by_condition,
            matches_by_condition=metrics.scoreable_ingredient_matches_by_condition,
            expected_conditions=expected_conditions,
            expected_total=len(scoreable_expected_names),
            match_count=scoreable_match_count,
        )

    llm_parse_status = observation.get("llm_parse_status")
    if isinstance(llm_parse_status, str) and llm_parse_status != "skipped_empty_text":
        metrics.llm_parse_attempt_count += 1
        if llm_parse_status == "completed":
            metrics.llm_parse_success_count += 1
    llm_observed_names = _observed_ingredient_names(observation.get("llm_parsed_ingredients"))
    if expected_names and llm_observed_names:
        metrics.llm_ingredient_name_total += len(expected_names)
        metrics.llm_ingredient_name_matches += len(expected_names.intersection(llm_observed_names))

    _accumulate_language_metric(metrics, observation, "cer_ko")
    _accumulate_language_metric(metrics, observation, "cer_en")
    _accumulate_language_metric(metrics, observation, "wer_ko")
    _accumulate_language_metric(metrics, observation, "wer_en")


def _add_provider_error_diagnostics(
    metrics: ProviderMetrics,
    *,
    observation: dict[str, object],
    fixture_id: object,
) -> None:
    """Add bounded error diagnostics for one failed observation.

    Args:
        metrics: Mutable aggregate metrics container.
        observation: Failed provider observation.
        fixture_id: Parent fixture id. Only stable fixture identifiers are stored.
    """
    code = _bounded_error_code(observation.get("error_code"))
    metrics.error_codes[code] = metrics.error_codes.get(code, 0) + 1
    stage = _provider_error_stage(observation=observation, error_code=code)
    metrics.error_stages[stage] = metrics.error_stages.get(stage, 0) + 1
    if isinstance(fixture_id, str) and fixture_id and fixture_id not in metrics.error_fixture_ids:
        metrics.error_fixture_ids.append(fixture_id)


def _bounded_error_code(value: object) -> str:
    """Return a stable bounded error code.

    Args:
        value: Candidate error code.

    Returns:
        A normalized code safe to serialize in reports.
    """
    if not isinstance(value, str):
        return "missing_error_code"
    code = value.strip().casefold()
    if not BOUNDED_CODE_PATTERN.fullmatch(code):
        return "unclassified_error_code"
    return code


def _provider_error_stage(
    *,
    observation: dict[str, object],
    error_code: str,
) -> str:
    """Infer the failing OCR pipeline stage from bounded observation fields.

    Args:
        observation: Failed provider observation.
        error_code: Bounded normalized error code.

    Returns:
        One of ``image_input``, ``provider_setup``, ``ocr_output``,
        ``parser``, ``ocr_provider``, or ``unknown``.
    """
    if error_code in IMAGE_INPUT_ERROR_CODES:
        return "image_input"
    if error_code in PROVIDER_SETUP_ERROR_CODES:
        return "provider_setup"
    if error_code in OCR_OUTPUT_ERROR_CODES:
        return "ocr_output"
    if observation.get("text_non_empty") is True and observation.get("parser_success") is not True:
        return "parser"
    if (
        observation.get("text_non_empty") is False
        or observation.get("layout_available") is False
        or error_code in {"ocr_error", "provider_error"}
    ):
        return "ocr_provider"
    return "unknown"


def _ingredient_match_count(
    *,
    expected_names: set[str],
    observed_names: set[str],
) -> int | None:
    """Return exact-match count for one expected ingredient set.

    Args:
        expected_names: Normalized expected names.
        observed_names: Normalized observed names.

    Returns:
        Match count, or None when the expected set is empty.
    """
    if not expected_names:
        return None
    return len(expected_names.intersection(observed_names))


def _add_condition_accuracy(
    *,
    total_by_condition: dict[str, int],
    matches_by_condition: dict[str, int],
    expected_conditions: list[str] | None,
    expected_total: int,
    match_count: int,
) -> None:
    """Accumulate one ingredient match result into chronic-condition buckets.

    Args:
        total_by_condition: Mutable denominator bucket map.
        matches_by_condition: Mutable numerator bucket map.
        expected_conditions: Chronic-disease labels for the fixture.
        expected_total: Expected ingredient count for the fixture.
        match_count: Matched ingredient count for the fixture.
    """
    if not expected_conditions:
        return
    for condition in expected_conditions:
        total_by_condition[condition] = total_by_condition.get(condition, 0) + expected_total
        matches_by_condition[condition] = matches_by_condition.get(condition, 0) + match_count


def _accumulate_language_metric(
    metrics: ProviderMetrics,
    observation: dict[str, object],
    key: str,
) -> None:
    """Add one observation's language-segmented error rate to the running sum.

    Skipped silently when the observation does not carry the requested metric
    (e.g. fixture had no expected reference text).

    Args:
        metrics: Mutable aggregate metrics container.
        observation: One observation row.
        key: Metric field name (``"cer_ko"`` / ``"cer_en"`` / ``"wer_ko"`` / ``"wer_en"``).
    """
    raw_value = observation.get(key)
    if not isinstance(raw_value, int | float):
        return
    value = float(raw_value)
    if value < 0:
        return
    if key == "cer_ko":
        metrics.cer_ko_sum += value
        metrics.cer_ko_count += 1
    elif key == "cer_en":
        metrics.cer_en_sum += value
        metrics.cer_en_count += 1
    elif key == "wer_ko":
        metrics.wer_ko_sum += value
        metrics.wer_ko_count += 1
    elif key == "wer_en":
        metrics.wer_en_sum += value
        metrics.wer_en_count += 1


def _expected_chronic_conditions(value: object) -> list[str]:
    """Extract chronic-disease indications declared in the expected snapshot.

    Args:
        value: ``row["expected"]`` payload from the manifest.

    Returns:
        Unique list of condition strings, or an empty list when the field is
        missing or malformed. No schema validation is performed here; the V3
        snapshot's own validator owns that responsibility.
    """
    if not isinstance(value, dict):
        return []
    raw = value.get("chronic_disease_indications")
    if not isinstance(raw, list):
        return []
    seen: list[str] = []
    for item in raw:
        if isinstance(item, str) and item and item not in seen:
            seen.append(item)
    return seen


def _observed_ingredient_names(value: object) -> set[str]:
    """Extract observed ingredient names from one provider observation.

    Supports both legacy ``{"name": ...}`` rows emitted by OCR regex matching and
    the LLM parser's ``{"display_name", "normalized_name", ...}`` schema.

    Args:
        value: Parsed ingredients value.

    Returns:
        Normalized observed names.
    """
    if not isinstance(value, list):
        return set()
    names: set[str] = set()
    for ingredient in value:
        if not isinstance(ingredient, dict):
            continue
        for key in ("name", "normalized_name", "display_name"):
            candidate = ingredient.get(key)
            if isinstance(candidate, str) and candidate:
                names.add(_normalize_token(candidate))
                break
    return names


def _normalize_token(value: str) -> str:
    """Normalize text for simple exact comparisons.

    Args:
        value: Raw text.

    Returns:
        Normalized text.
    """
    return " ".join(value.casefold().split())


def _rate(numerator: int, denominator: int) -> float | None:
    """Calculate a rounded rate.

    Args:
        numerator: Numerator.
        denominator: Denominator.

    Returns:
        Rounded rate or None.
    """
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _average(total: float, count: int) -> float | None:
    """Calculate a rounded average from a running sum and observation count.

    Args:
        total: Accumulated sum.
        count: Number of observations contributing to ``total``.

    Returns:
        Average rounded to 4 decimal places, or ``None`` when count is zero.
    """
    if count <= 0:
        return None
    return round(total / count, 4)


def _render_markdown(summary: dict[str, object]) -> str:
    """Render a redacted Markdown report.

    Args:
        summary: Evaluation summary.

    Returns:
        Markdown report.
    """
    lines = [
        "# OCR 3-Tier Fixture Evaluation Report",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Manifest: `{summary['manifest']}`",
        f"- Fixtures: `{summary['fixture_count']}`",
        f"- Observations: `{summary['observation_count']}`",
        f"- Scoreable fixtures: `{summary.get('scoreable_fixture_count')}`",
        f"- Provisional fixtures: `{summary.get('provisional_fixture_count')}`",
        f"- Expected quality warnings: `{len(summary.get('expected_quality_warnings', []))}`",
        f"- Missing image files: `{summary['missing_image_count']}`",
        f"- Raw image artifacts stored: `{summary['raw_artifacts_stored']}`",
        f"- Raw OCR text stored: `{summary['raw_ocr_text_stored']}`",
        "",
        "## Provider Metrics",
        "",
        "| Provider | Calls | Text non-empty | Parser success | Avg latency ms | Ingredient name exact | Scoreable ingredient exact | Errors | LLM attempts | LLM parse success | LLM ingredient exact |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    provider_metrics = _provider_metric_items(summary)
    _append_provider_metric_rows(lines, provider_metrics)
    _append_provider_error_diagnostics(lines, provider_metrics)
    _append_language_metric_rows(lines, provider_metrics)
    _append_condition_metric_sections(lines, provider_metrics)
    lines.append("")
    return "\n".join(lines)


def _provider_metric_items(summary: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
    """Return provider metric rows from a summary object.

    Args:
        summary: Evaluation summary.

    Returns:
        Provider name and metric dictionaries.
    """
    providers = summary.get("providers", {})
    if not isinstance(providers, dict):
        return []
    return [
        (provider, raw_metrics)
        for provider, raw_metrics in providers.items()
        if isinstance(provider, str) and isinstance(raw_metrics, dict)
    ]


def _append_provider_metric_rows(
    lines: list[str],
    provider_metrics: list[tuple[str, dict[str, object]]],
) -> None:
    """Append provider metric table rows.

    Args:
        lines: Mutable Markdown lines.
        provider_metrics: Provider metric rows.
    """
    for provider, raw_metrics in provider_metrics:
        lines.append(
            "| {provider} | {calls} | {text_rate} | {parser_rate} | {latency} | {ingredient_rate} | {scoreable_rate} | {errors} | {llm_attempts} | {llm_parse_rate} | {llm_ingredient_rate} |".format(
                provider=provider,
                calls=raw_metrics.get("calls"),
                text_rate=raw_metrics.get("text_non_empty_rate"),
                parser_rate=raw_metrics.get("parser_success_rate"),
                latency=raw_metrics.get("average_latency_ms"),
                ingredient_rate=raw_metrics.get("ingredient_name_exact_rate"),
                scoreable_rate=raw_metrics.get("scoreable_ingredient_name_exact_rate"),
                errors=raw_metrics.get("errors"),
                llm_attempts=raw_metrics.get("llm_parse_attempt_count"),
                llm_parse_rate=raw_metrics.get("llm_parse_success_rate"),
                llm_ingredient_rate=raw_metrics.get("llm_ingredient_name_exact_rate"),
            )
        )


def _append_provider_error_diagnostics(
    lines: list[str],
    provider_metrics: list[tuple[str, dict[str, object]]],
) -> None:
    """Append bounded provider error diagnostics.

    Args:
        lines: Mutable Markdown lines.
        provider_metrics: Provider metric rows.
    """
    lines.extend(
        [
            "",
            "## Provider Error Diagnostics",
            "",
            "Bounded diagnostics only. Raw OCR text, provider payloads, and provider error messages are not stored.",
            "",
            "| Provider | Error codes | Error stages | Fixture ids |",
            "| --- | --- | --- | --- |",
        ]
    )
    for provider, raw_metrics in provider_metrics:
        lines.append(
            "| {provider} | {codes} | {stages} | {fixtures} |".format(
                provider=provider,
                codes=_format_mapping(raw_metrics.get("error_codes")),
                stages=_format_mapping(raw_metrics.get("error_stages")),
                fixtures=_format_list(raw_metrics.get("error_fixture_ids")),
            )
        )


def _append_language_metric_rows(
    lines: list[str],
    provider_metrics: list[tuple[str, dict[str, object]]],
) -> None:
    """Append language-segmented metric rows.

    Args:
        lines: Mutable Markdown lines.
        provider_metrics: Provider metric rows.
    """
    lines.extend(
        [
            "",
            "## Language-Segmented Error Rates (한국어/영문)",
            "",
            "| Provider | CER ko (avg) | CER en (avg) | WER ko (avg) | WER en (avg) |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for provider, raw_metrics in provider_metrics:
        lines.append(
            "| {provider} | {cer_ko} | {cer_en} | {wer_ko} | {wer_en} |".format(
                provider=provider,
                cer_ko=raw_metrics.get("cer_ko_avg"),
                cer_en=raw_metrics.get("cer_en_avg"),
                wer_ko=raw_metrics.get("wer_ko_avg"),
                wer_en=raw_metrics.get("wer_en_avg"),
            )
        )


def _append_condition_metric_sections(
    lines: list[str],
    provider_metrics: list[tuple[str, dict[str, object]]],
) -> None:
    """Append chronic-condition metric sections.

    Args:
        lines: Mutable Markdown lines.
        provider_metrics: Provider metric rows.
    """
    lines.extend(
        [
            "",
            "## 만성질환별 정확도 (B형 페르소나 시나리오)",
            "",
            "Expected fixture 의 ``chronic_disease_indications`` 별로 분리한 ingredient_name_exact_rate.",
            "Scoreable 지표는 포장/수량 auto-seed 오염을 제외한 denominator를 사용한다.",
            "값이 비어 있으면 해당 fixture set 에 그 만성질환 인디케이션 라벨이 없음을 뜻한다.",
            "",
        ]
    )
    for provider, raw_metrics in provider_metrics:
        _append_one_condition_metric_section(lines, provider, raw_metrics)


def _append_one_condition_metric_section(
    lines: list[str],
    provider: str,
    raw_metrics: dict[str, object],
) -> None:
    """Append one provider's chronic-condition metric section when present.

    Args:
        lines: Mutable Markdown lines.
        provider: Provider name.
        raw_metrics: Provider metric dictionary.
    """
    condition_map = raw_metrics.get("accuracy_by_condition")
    if not isinstance(condition_map, dict) or not condition_map:
        return
    lines.append(f"### {provider}")
    lines.append("")
    scoreable_condition_map = raw_metrics.get("scoreable_accuracy_by_condition")
    if not isinstance(scoreable_condition_map, dict):
        scoreable_condition_map = {}
    lines.append("| Chronic condition | accuracy | scoreable accuracy |")
    lines.append("| --- | ---: | ---: |")
    for condition, accuracy in sorted(condition_map.items()):
        lines.append(f"| {condition} | {accuracy} | {scoreable_condition_map.get(condition)} |")
    lines.append("")


def _format_mapping(value: object) -> str:
    """Format a small diagnostic mapping for Markdown.

    Args:
        value: Candidate mapping.

    Returns:
        Bounded Markdown cell text.
    """
    if not isinstance(value, dict) or not value:
        return ""
    parts = []
    for key, count in sorted(value.items()):
        if isinstance(key, str) and isinstance(count, int):
            parts.append(f"{key}:{count}")
    return ", ".join(parts)


def _format_list(value: object) -> str:
    """Format a small diagnostic list for Markdown.

    Args:
        value: Candidate list.

    Returns:
        Bounded Markdown cell text.
    """
    if not isinstance(value, list) or not value:
        return ""
    return ", ".join(item for item in value if isinstance(item, str))


if __name__ == "__main__":
    main()
