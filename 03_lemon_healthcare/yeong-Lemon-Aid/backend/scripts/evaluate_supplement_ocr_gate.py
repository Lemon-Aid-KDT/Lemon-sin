"""Evaluate the supplement OCR validation gate from redacted observations.

This evaluator consumes a committed fixture manifest and redacted provider
observations. It never stores or reads raw OCR text, provider payloads,
credentials, or request headers. Metrics are fixture observations for
no-regression governance, not official OCR accuracy claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.models.schemas.governance import RedactedEvaluationReport  # noqa: E402

SUPPLEMENT_OCR_GATE_SCHEMA_VERSION: Literal["supplement-ocr-gate-report-v1"] = (
    "supplement-ocr-gate-report-v1"
)
ProviderName = Literal["google_vision_document", "paddleocr_local", "clova_ocr"]
GateMode = Literal["report_only", "block_release"]
GateStatus = Literal["passed", "warning", "blocked"]

REQUIRED_PROVIDERS: tuple[ProviderName, ...] = (
    "google_vision_document",
    "paddleocr_local",
    "clova_ocr",
)
PRIMARY_METRICS = (
    "text_non_empty_rate",
    "parser_success_rate",
    "ingredient_name_exact_rate",
    "numeric_amount_exact_rate",
    "unit_exact_rate",
    "layout_available_rate",
    "evidence_grounded_rate",
)
SAFETY_METRICS = (
    "provider_not_run_count",
    "provider_error_count",
    "raw_text_leak_count",
    "raw_data_leak_count",
    "evidence_grounding_regression_count",
)
SOURCE_DOC_URLS = (
    "https://cloud.google.com/vision/docs/ocr",
    "https://cloud.google.com/vision/docs/reference/rest/v1/Feature",
    "https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html",
    "https://api.ncloud-docs.com/docs/en/ai-application-service-ocr",
)
RAW_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "image_bytes",
        "ocr_text",
        "provider_payload",
        "raw_image",
        "raw_ocr_text",
        "raw_provider_payload",
        "request_headers",
        "service_key",
    }
)
ALLOWED_LICENSE_STATUS = frozenset({"public", "team_approved", "consented", "synthetic"})
ALLOWED_CONSENT_STATUS = frozenset({"not_required", "team_approved", "consented"})
MIN_BLOCK_RELEASE_FIXTURES = 12
AUTO_EXPECTED_SOURCE = "google_vision_auto_seed"
AUTO_EXPECTED_VERIFICATION_STATUS = "provisional"
HUMAN_VERIFIED_STATUS = "human_verified"


@dataclass(frozen=True)
class FixtureCase:
    """One validated OCR gate fixture.

    Attributes:
        fixture_id: Stable fixture identifier.
        expected: Redacted expected field summary.
    """

    fixture_id: str
    expected: dict[str, object]


@dataclass
class ProviderAccumulator:
    """Aggregate metric state for one OCR provider.

    Attributes:
        observations: Number of observation rows for the provider.
        completed: Completed provider calls.
        not_run: Not-run observations plus missing fixture/provider pairs.
        errors: Provider error observations.
        text_non_empty: Completed calls with non-empty OCR text.
        parser_success: Completed calls where expected fields were recoverable.
        layout_available: Completed calls with usable layout metadata.
        evidence_grounded: Completed calls whose parsed values were grounded.
        latency_total_ms: Sum of completed call latencies.
        ingredient_name_matches: Matched ingredient-name observations.
        ingredient_name_total: Expected ingredient-name observations.
        numeric_amount_matches: Matched ingredient amount observations.
        numeric_amount_total: Expected ingredient amount observations.
        unit_matches: Matched ingredient unit observations.
        unit_total: Expected ingredient unit observations.
        self_seeded_expected_exclusions: Completed observations excluded from exact
            field metrics because the provider is the source of provisional expected data.
    """

    observations: int = 0
    completed: int = 0
    not_run: int = 0
    errors: int = 0
    text_non_empty: int = 0
    parser_success: int = 0
    layout_available: int = 0
    evidence_grounded: int = 0
    latency_total_ms: float = 0.0
    ingredient_name_matches: int = 0
    ingredient_name_total: int = 0
    numeric_amount_matches: int = 0
    numeric_amount_total: int = 0
    unit_matches: int = 0
    unit_total: int = 0
    self_seeded_expected_exclusions: int = 0

    def as_metrics(self) -> dict[str, int | float | None]:
        """Return provider-level metrics.

        Returns:
            Serializable aggregate metrics.
        """
        return {
            "observations": self.observations,
            "completed_calls": self.completed,
            "not_run_count": self.not_run,
            "error_count": self.errors,
            "text_non_empty_rate": _rate(self.text_non_empty, self.completed),
            "parser_success_rate": _rate(self.parser_success, self.completed),
            "ingredient_name_exact_rate": _rate(
                self.ingredient_name_matches,
                self.ingredient_name_total,
            ),
            "numeric_amount_exact_rate": _rate(
                self.numeric_amount_matches,
                self.numeric_amount_total,
            ),
            "unit_exact_rate": _rate(self.unit_matches, self.unit_total),
            "layout_available_rate": _rate(self.layout_available, self.completed),
            "evidence_grounded_rate": _rate(self.evidence_grounded, self.completed),
            "self_seeded_expected_excluded_count": self.self_seeded_expected_exclusions,
            "average_latency_ms": (
                round(self.latency_total_ms / self.completed, 3) if self.completed else None
            ),
        }


@dataclass
class EvaluationAccumulator:
    """Aggregate OCR gate evaluation state.

    Attributes:
        providers: Provider metrics keyed by provider id.
        observed_pairs: Fixture/provider pairs present in observations.
    """

    providers: dict[str, ProviderAccumulator] = field(
        default_factory=lambda: defaultdict(ProviderAccumulator)
    )
    observed_pairs: set[tuple[str, str]] = field(default_factory=set)


def main() -> None:
    """Run the supplement OCR gate evaluator from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--baseline-report", type=Path, default=None)
    parser.add_argument(
        "--gate-mode", choices=("report_only", "block_release"), default="report_only"
    )
    parser.add_argument(
        "--required-providers",
        default=",".join(REQUIRED_PROVIDERS),
        help="Comma-separated providers required for block_release.",
    )
    args = parser.parse_args()

    summary = evaluate_gate(
        manifest_path=args.manifest,
        observations_path=args.observations,
        gate_mode=cast(GateMode, args.gate_mode),
        baseline_report_path=args.baseline_report,
        required_providers=_parse_providers(args.required_providers),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "supplement-ocr-gate.json"
    markdown_path = args.output_dir / "supplement-ocr-gate.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_markdown(summary), encoding="utf-8")
    print(json.dumps({"report": str(json_path), "markdown": str(markdown_path)}))


def evaluate_gate(
    *,
    manifest_path: Path,
    observations_path: Path,
    gate_mode: GateMode,
    baseline_report_path: Path | None = None,
    required_providers: tuple[ProviderName, ...] = REQUIRED_PROVIDERS,
) -> dict[str, object]:
    """Evaluate the OCR validation gate.

    Args:
        manifest_path: Fixture manifest path.
        observations_path: Redacted observation JSONL path.
        gate_mode: Report-only or blocking mode.
        baseline_report_path: Optional previous gate report for no-regression checks.
        required_providers: Provider ids required in block-release mode.

    Returns:
        Redacted gate report.

    Raises:
        ValueError: If inputs contain raw fields or unsafe fixture metadata.
    """
    fixtures, fixture_version, missing_image_count = _read_fixture_manifest(manifest_path)
    observations = _read_observations(observations_path)
    accumulator = _evaluate_observations(fixtures, observations, required_providers)
    expected_source_counts = _expected_source_counts(fixtures)
    provisional_expected_count = _provisional_expected_count(fixtures)
    provider_metrics: dict[str, dict[str, int | float | None]] = {
        provider: accumulator.providers[provider].as_metrics() for provider in required_providers
    }
    candidate_metrics = _overall_candidate_metrics(provider_metrics)
    baseline_metrics = _baseline_metrics(baseline_report_path) or dict(candidate_metrics)
    safety_metrics = _safety_metrics(accumulator, provider_metrics)
    reasons = _gate_reasons(
        fixtures=fixtures,
        gate_mode=gate_mode,
        missing_image_count=missing_image_count,
        required_providers=required_providers,
        provider_metrics=provider_metrics,
        candidate_metrics=candidate_metrics,
        baseline_metrics=baseline_metrics,
        baseline_report_path=baseline_report_path,
        safety_metrics=safety_metrics,
        provisional_expected_count=provisional_expected_count,
    )
    release_blocked = gate_mode == "block_release" and bool(reasons)
    governance_report = _build_governance_report(
        fixture_version=fixture_version,
        fixture_count=len(fixtures),
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        safety_metrics=safety_metrics,
    )
    return {
        "schema_version": SUPPLEMENT_OCR_GATE_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "gate_mode": gate_mode,
        "gate_status": _gate_status(gate_mode, reasons),
        "release_blocked": release_blocked,
        "fixture_version": fixture_version,
        "fixture_count": len(fixtures),
        "missing_image_count": missing_image_count,
        "expected_source_counts": expected_source_counts,
        "provisional_expected_count": provisional_expected_count,
        "required_providers": list(required_providers),
        "provider_metrics": provider_metrics,
        "baseline_metrics": baseline_metrics,
        "candidate_metrics": candidate_metrics,
        "safety_metrics": safety_metrics,
        "reasons": reasons,
        "source_doc_urls": list(SOURCE_DOC_URLS),
        "interpretation": (_interpretation_for_expected_policy(provisional_expected_count)),
        "governance_report": governance_report.model_dump(mode="json"),
    }


def _read_fixture_manifest(manifest_path: Path) -> tuple[list[FixtureCase], str, int]:
    """Read and validate OCR gate fixture manifest.

    Args:
        manifest_path: JSON or JSONL fixture manifest path.

    Returns:
        Fixture cases, fixture version, and missing image count.
    """
    parsed = _manifest_payload(manifest_path)
    version = parsed.get("version") if isinstance(parsed, dict) else None
    rows = _manifest_rows(parsed)
    fixtures: list[FixtureCase] = []
    missing_image_count = 0
    for raw_row in rows:
        _reject_raw_fields(raw_row)
        fixture_id = _required_string(raw_row, "fixture_id")
        image_path = _required_string(raw_row, "image_path")
        image_sha256 = _required_string(raw_row, "image_sha256")
        if raw_row.get("contains_personal_data") is not False:
            raise ValueError(f"Fixture must set contains_personal_data=false: {fixture_id}")
        if raw_row.get("license_status") not in ALLOWED_LICENSE_STATUS:
            raise ValueError(f"Fixture has unsupported license_status: {fixture_id}")
        if raw_row.get("consent_status") not in ALLOWED_CONSENT_STATUS:
            raise ValueError(f"Fixture has unsupported consent_status: {fixture_id}")
        fixture_image = manifest_path.parent / image_path
        if fixture_image.exists():
            actual_sha = hashlib.sha256(fixture_image.read_bytes()).hexdigest()
            if actual_sha != image_sha256:
                raise ValueError(f"Fixture image_sha256 mismatch: {fixture_id}")
        else:
            missing_image_count += 1
        expected = raw_row.get("expected", {})
        if not isinstance(expected, dict):
            raise ValueError(f"Fixture expected must be an object: {fixture_id}")
        fixtures.append(FixtureCase(fixture_id=fixture_id, expected=expected))
    if not fixtures:
        raise ValueError("OCR gate manifest must contain at least one fixture.")
    return fixtures, str(version or "unversioned"), missing_image_count


def _manifest_payload(manifest_path: Path) -> object:
    """Read a JSON or JSONL manifest payload.

    Args:
        manifest_path: Manifest path.

    Returns:
        Parsed payload.
    """
    text = manifest_path.read_text(encoding="utf-8")
    if manifest_path.suffix == ".jsonl":
        return [
            json.loads(line)
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    return json.loads(text)


def _manifest_rows(payload: object) -> list[dict[str, object]]:
    """Return fixture rows from a parsed manifest payload.

    Args:
        payload: Parsed JSON or JSONL payload.

    Returns:
        Fixture rows.
    """
    if isinstance(payload, dict) and isinstance(payload.get("cases"), list):
        return [cast(dict[str, object], row) for row in payload["cases"]]
    if isinstance(payload, list):
        return [cast(dict[str, object], row) for row in payload]
    raise ValueError("Manifest must be JSONL, a JSON list, or a JSON object with cases.")


def _read_observations(observations_path: Path) -> list[dict[str, object]]:
    """Read redacted observation rows.

    Args:
        observations_path: Observation JSONL path.

    Returns:
        Observation dictionaries.
    """
    observations: list[dict[str, object]] = []
    for line_number, line in enumerate(
        observations_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        row = json.loads(stripped)
        if not isinstance(row, dict):
            raise ValueError(f"Observation line {line_number} must be an object.")
        _reject_raw_fields(row)
        observations.append(row)
    return observations


def _evaluate_observations(
    fixtures: list[FixtureCase],
    observations: list[dict[str, object]],
    required_providers: tuple[ProviderName, ...],
) -> EvaluationAccumulator:
    """Aggregate observations into provider metrics.

    Args:
        fixtures: Fixture cases.
        observations: Redacted observation rows.
        required_providers: Required provider ids.

    Returns:
        Evaluation accumulator.
    """
    fixture_by_id = {fixture.fixture_id: fixture for fixture in fixtures}
    accumulator = EvaluationAccumulator()
    for observation in observations:
        fixture_id = observation.get("fixture_id")
        provider = observation.get("provider")
        if not isinstance(fixture_id, str) or fixture_id not in fixture_by_id:
            continue
        if provider not in required_providers:
            continue
        provider_key = cast(str, provider)
        accumulator.observed_pairs.add((fixture_id, provider_key))
        _add_observation(
            accumulator.providers[provider_key],
            fixture=fixture_by_id[fixture_id],
            observation=observation,
            provider=provider_key,
        )
    for provider in required_providers:
        missing = len(fixtures) - sum(
            1
            for fixture in fixtures
            if (fixture.fixture_id, provider) in accumulator.observed_pairs
        )
        accumulator.providers[provider].not_run += max(missing, 0)
    return accumulator


def _add_observation(
    accumulator: ProviderAccumulator,
    *,
    fixture: FixtureCase,
    observation: dict[str, object],
    provider: str,
) -> None:
    """Add one observation to provider metrics.

    Args:
        accumulator: Mutable provider accumulator.
        fixture: Fixture case.
        observation: Observation row.
        provider: Observation provider id.
    """
    accumulator.observations += 1
    status = observation.get("status")
    if status == "not_run":
        accumulator.not_run += 1
        return
    if status == "error":
        accumulator.errors += 1
        return
    if status != "completed":
        accumulator.errors += 1
        return
    accumulator.completed += 1
    accumulator.text_non_empty += int(observation.get("text_non_empty") is True)
    accumulator.parser_success += int(observation.get("parser_success") is True)
    accumulator.layout_available += int(observation.get("layout_available") is True)
    accumulator.evidence_grounded += int(observation.get("evidence_grounded") is True)
    latency_ms = observation.get("latency_ms")
    if isinstance(latency_ms, int | float) and latency_ms >= 0:
        accumulator.latency_total_ms += float(latency_ms)
    _add_field_metrics(
        accumulator,
        fixture.expected,
        observation.get("parsed_ingredients"),
        provider=provider,
    )


def _add_field_metrics(
    accumulator: ProviderAccumulator,
    expected: dict[str, object],
    parsed_value: object,
    *,
    provider: str,
) -> None:
    """Add ingredient field exact-match metrics.

    Args:
        accumulator: Mutable provider accumulator.
        expected: Expected fixture summary.
        parsed_value: Parsed ingredient observation value.
        provider: Observation provider id.
    """
    if _is_self_seeded_expected(expected, provider):
        accumulator.self_seeded_expected_exclusions += 1
        return
    expected_ingredients = _expected_ingredients(expected)
    parsed_ingredients = _parsed_ingredients(parsed_value)
    parsed_by_name = {
        _normalize_value(item.get("name")): item
        for item in parsed_ingredients
        if isinstance(item.get("name"), str)
    }
    for ingredient in expected_ingredients:
        expected_name = _normalize_value(ingredient.get("name"))
        if not expected_name:
            continue
        accumulator.ingredient_name_total += 1
        observed = parsed_by_name.get(expected_name)
        if observed is None:
            continue
        accumulator.ingredient_name_matches += 1
        if ingredient.get("amount") is not None:
            accumulator.numeric_amount_total += 1
            accumulator.numeric_amount_matches += int(
                _normalize_value(observed.get("amount"))
                == _normalize_value(ingredient.get("amount"))
            )
        if ingredient.get("unit") is not None:
            accumulator.unit_total += 1
            accumulator.unit_matches += int(
                _normalize_value(observed.get("unit")) == _normalize_value(ingredient.get("unit"))
            )


def _overall_candidate_metrics(
    provider_metrics: dict[str, dict[str, int | float | None]],
) -> dict[str, float]:
    """Average provider rates into candidate governance metrics.

    Args:
        provider_metrics: Provider metric mappings.

    Returns:
        Overall candidate metrics.
    """
    candidate: dict[str, float] = {}
    for metric in PRIMARY_METRICS:
        values: list[float] = []
        for raw_metrics in provider_metrics.values():
            value = raw_metrics.get(metric)
            if isinstance(value, int | float):
                values.append(float(value))
        candidate[metric] = round(sum(values) / len(values), 6) if values else 0.0
    return candidate


def _baseline_metrics(baseline_report_path: Path | None) -> dict[str, float] | None:
    """Read baseline metrics from a previous OCR gate report.

    Args:
        baseline_report_path: Optional baseline report path.

    Returns:
        Baseline metric mapping or None.
    """
    if baseline_report_path is None:
        return None
    parsed = json.loads(baseline_report_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Baseline report must be a JSON object.")
    metrics = parsed.get("candidate_metrics", parsed.get("baseline_metrics"))
    if not isinstance(metrics, dict):
        raise ValueError("Baseline report must contain candidate_metrics.")
    return {
        key: float(value)
        for key, value in metrics.items()
        if key in PRIMARY_METRICS and isinstance(value, int | float)
    }


def _safety_metrics(
    accumulator: EvaluationAccumulator,
    provider_metrics: dict[str, dict[str, int | float | None]],
) -> dict[str, float]:
    """Build safety metrics for governance.

    Args:
        accumulator: Evaluation accumulator.
        provider_metrics: Provider metrics.

    Returns:
        Safety metric mapping.
    """
    provider_not_run = sum(
        int(metrics.get("not_run_count", 0) or 0) for metrics in provider_metrics.values()
    )
    provider_errors = sum(
        int(metrics.get("error_count", 0) or 0) for metrics in provider_metrics.values()
    )
    evidence_failures = sum(
        accumulator.providers[provider].completed
        - accumulator.providers[provider].evidence_grounded
        for provider in provider_metrics
    )
    return {
        "provider_not_run_count": float(provider_not_run),
        "provider_error_count": float(provider_errors),
        "raw_text_leak_count": 0.0,
        "raw_data_leak_count": 0.0,
        "evidence_grounding_regression_count": float(max(evidence_failures, 0)),
    }


def _gate_reasons(
    *,
    fixtures: list[FixtureCase],
    gate_mode: GateMode,
    missing_image_count: int,
    required_providers: tuple[ProviderName, ...],
    provider_metrics: dict[str, dict[str, int | float | None]],
    candidate_metrics: dict[str, float],
    baseline_metrics: dict[str, float],
    baseline_report_path: Path | None,
    safety_metrics: dict[str, float],
    provisional_expected_count: int,
) -> list[str]:
    """Build safe gate reasons.

    Args:
        fixtures: Fixture cases.
        gate_mode: Gate mode.
        missing_image_count: Missing fixture image count.
        required_providers: Required providers.
        provider_metrics: Provider metrics.
        candidate_metrics: Candidate metrics.
        baseline_metrics: Baseline metrics.
        baseline_report_path: Optional baseline report path.
        safety_metrics: Safety metrics.
        provisional_expected_count: Fixtures whose expected snapshot is not human verified.

    Returns:
        Safe reason codes.
    """
    reasons: list[str] = []
    if len(fixtures) < MIN_BLOCK_RELEASE_FIXTURES:
        reasons.append("baseline_fixture_count_below_minimum")
    if missing_image_count:
        reasons.append("fixture_image_missing")
    for provider in required_providers:
        metrics = provider_metrics[provider]
        if metrics.get("completed_calls") != len(fixtures):
            reasons.append(f"provider_observation_missing:{provider}")
    if gate_mode == "block_release" and baseline_report_path is None:
        reasons.append("baseline_report_required")
    if gate_mode == "block_release" and provisional_expected_count:
        reasons.append("human_verified_expected_required")
    for metric in PRIMARY_METRICS:
        baseline = baseline_metrics.get(metric)
        candidate = candidate_metrics.get(metric)
        if baseline is None or candidate is None:
            reasons.append(f"baseline_metric_missing:{metric}")
            continue
        if candidate < baseline:
            reasons.append(f"primary_metric_regressed:{metric}")
    for metric in SAFETY_METRICS:
        if safety_metrics.get(metric, 0.0) != 0.0:
            reasons.append(f"safety_metric_nonzero:{metric}")
    return _dedupe(reasons)


def _build_governance_report(
    *,
    fixture_version: str,
    fixture_count: int,
    baseline_metrics: dict[str, float],
    candidate_metrics: dict[str, float],
    safety_metrics: dict[str, float],
) -> RedactedEvaluationReport:
    """Build a governance-compatible redacted evaluation report.

    Args:
        fixture_version: Fixture version.
        fixture_count: Fixture count.
        baseline_metrics: Baseline metrics.
        candidate_metrics: Candidate metrics.
        safety_metrics: Safety metrics.

    Returns:
        Redacted governance report.
    """
    return RedactedEvaluationReport(
        report_id=f"supplement-ocr-gate-{datetime.now(UTC).date().isoformat()}",
        pipeline="supplement_ocr_gate",
        frozen_fixture_version=fixture_version,
        split_version="supplement-ocr-gate-fixtures",
        aggregate_case_count=fixture_count,
        primary_metric_names=list(PRIMARY_METRICS),
        required_safety_metric_names=list(SAFETY_METRICS),
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        safety_metrics=safety_metrics,
        source_doc_urls=list(SOURCE_DOC_URLS),
        notes=["No official supplement-label OCR acceptance threshold is claimed."],
    )


def _gate_status(gate_mode: GateMode, reasons: list[str]) -> GateStatus:
    """Resolve gate status.

    Args:
        gate_mode: Gate mode.
        reasons: Safe reason codes.

    Returns:
        Gate status.
    """
    if not reasons:
        return "passed"
    if gate_mode == "block_release":
        return "blocked"
    return "warning"


def _render_markdown(summary: dict[str, object]) -> str:
    """Render a Markdown OCR gate report.

    Args:
        summary: Gate summary.

    Returns:
        Markdown report.
    """
    lines = [
        "# Supplement OCR Gate Report",
        "",
        f"- Gate mode: `{summary['gate_mode']}`",
        f"- Gate status: `{summary['gate_status']}`",
        f"- Release blocked: `{summary['release_blocked']}`",
        f"- Fixtures: `{summary['fixture_count']}`",
        f"- Provisional expected fixtures: `{summary.get('provisional_expected_count')}`",
        f"- Interpretation: {summary['interpretation']}",
        f"- Expected sources: `{summary.get('expected_source_counts')}`",
        "",
        "## Provider Metrics",
        "",
        "| Provider | Completed | Not run | Errors | Text non-empty | Parser success | Ingredient exact | Amount exact | Unit exact | Layout | Evidence grounded | Self-seed excluded | Avg latency ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    provider_metrics = summary.get("provider_metrics", {})
    if isinstance(provider_metrics, dict):
        for provider, metrics in provider_metrics.items():
            if not isinstance(metrics, dict):
                continue
            lines.append(
                "| {provider} | {completed} | {not_run} | {errors} | {text} | {parser} | {ingredient} | {amount} | {unit} | {layout} | {evidence} | {self_seed} | {latency} |".format(
                    provider=provider,
                    completed=metrics.get("completed_calls"),
                    not_run=metrics.get("not_run_count"),
                    errors=metrics.get("error_count"),
                    text=metrics.get("text_non_empty_rate"),
                    parser=metrics.get("parser_success_rate"),
                    ingredient=metrics.get("ingredient_name_exact_rate"),
                    amount=metrics.get("numeric_amount_exact_rate"),
                    unit=metrics.get("unit_exact_rate"),
                    layout=metrics.get("layout_available_rate"),
                    evidence=metrics.get("evidence_grounded_rate"),
                    self_seed=metrics.get("self_seeded_expected_excluded_count"),
                    latency=metrics.get("average_latency_ms"),
                )
            )
    lines.extend(["", "## Reasons", ""])
    reasons = summary.get("reasons", [])
    if isinstance(reasons, list) and reasons:
        lines.extend(f"- `{reason}`" for reason in reasons)
    else:
        lines.append("- `gate_passed`")
    lines.append("")
    return "\n".join(lines)


def _reject_raw_fields(value: object) -> None:
    """Reject raw image, OCR text, provider payload, and credential fields.

    Args:
        value: Candidate manifest or observation object.

    Raises:
        ValueError: If any forbidden field is present.
    """
    if isinstance(value, dict):
        forbidden = RAW_FORBIDDEN_KEYS.intersection(str(key).lower() for key in value)
        if forbidden:
            raise ValueError(f"Payload contains forbidden raw field(s): {sorted(forbidden)}")
        for nested_value in value.values():
            _reject_raw_fields(nested_value)
    elif isinstance(value, list):
        for item in value:
            _reject_raw_fields(item)


def _required_string(row: dict[str, object], key: str) -> str:
    """Return a required string field.

    Args:
        row: Fixture row.
        key: Field key.

    Returns:
        Field value.

    Raises:
        ValueError: If missing or blank.
    """
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Fixture requires non-empty {key}.")
    return value.strip()


def _expected_ingredients(expected: dict[str, object]) -> list[dict[str, object]]:
    """Return expected ingredients.

    Args:
        expected: Expected fixture summary.

    Returns:
        Ingredient dictionaries.
    """
    ingredients = expected.get("ingredients")
    if not isinstance(ingredients, list):
        return []
    return [item for item in ingredients if isinstance(item, dict)]


def _is_self_seeded_expected(expected: dict[str, object], provider: str) -> bool:
    """Return whether the provider generated the provisional expected snapshot.

    Args:
        expected: Fixture expected object.
        provider: Observation provider id.

    Returns:
        True when exact-match fields must be excluded for this provider.
    """
    return (
        expected.get("expected_source") == AUTO_EXPECTED_SOURCE
        and expected.get("verification_status") == AUTO_EXPECTED_VERIFICATION_STATUS
        and expected.get("seed_provider") == provider
    )


def _expected_source_counts(fixtures: list[FixtureCase]) -> dict[str, int]:
    """Count expected snapshot sources across fixtures.

    Args:
        fixtures: Fixture cases.

    Returns:
        Counts keyed by expected source.
    """
    counts: dict[str, int] = {}
    for fixture in fixtures:
        source = fixture.expected.get("expected_source")
        key = source if isinstance(source, str) and source else "unspecified"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _provisional_expected_count(fixtures: list[FixtureCase]) -> int:
    """Count fixtures whose expected object is not human verified.

    Args:
        fixtures: Fixture cases.

    Returns:
        Provisional fixture count.
    """
    return sum(
        1
        for fixture in fixtures
        if fixture.expected.get("verification_status") != HUMAN_VERIFIED_STATUS
    )


def _interpretation_for_expected_policy(provisional_expected_count: int) -> str:
    """Return the report interpretation for the expected snapshot policy.

    Args:
        provisional_expected_count: Number of non-human-verified expected fixtures.

    Returns:
        Human-readable interpretation string.
    """
    if provisional_expected_count:
        return (
            "Metrics are redacted fixture observations. Provisional Google Vision "
            "auto-seeded expected snapshots are agreement baselines, not official OCR "
            "accuracy claims; the seed provider is excluded from self-exact field metrics."
        )
    return (
        "Metrics are redacted fixture observations for no-regression governance, "
        "not official OCR accuracy claims."
    )


def _parsed_ingredients(value: object) -> list[dict[str, object]]:
    """Return parsed ingredient observations.

    Args:
        value: Candidate parsed ingredient value.

    Returns:
        Ingredient dictionaries.
    """
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _normalize_value(value: object) -> str:
    """Normalize a scalar value for exact metric matching.

    Args:
        value: Candidate value.

    Returns:
        Normalized string.
    """
    raw = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value or "")
    return " ".join(raw.casefold().split())


def _rate(numerator: int, denominator: int) -> float | None:
    """Return a rounded rate.

    Args:
        numerator: Numerator.
        denominator: Denominator.

    Returns:
        Rounded rate or None.
    """
    if denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def _dedupe(values: list[str]) -> list[str]:
    """Deduplicate strings while preserving order.

    Args:
        values: Candidate strings.

    Returns:
        Deduplicated strings.
    """
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _parse_providers(value: str) -> tuple[ProviderName, ...]:
    """Parse CLI provider list.

    Args:
        value: Comma-separated provider list.

    Returns:
        Provider tuple.
    """
    providers: list[ProviderName] = []
    for item in value.split(","):
        provider = item.strip()
        if not provider:
            continue
        if provider not in REQUIRED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")
        providers.append(provider)
    return tuple(providers or REQUIRED_PROVIDERS)


if __name__ == "__main__":
    main()
