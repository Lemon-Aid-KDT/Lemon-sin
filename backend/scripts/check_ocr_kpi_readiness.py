"""Check whether a redacted OCR evaluation can support an official KPI claim.

This gate is intentionally stricter than ``evaluate_ocr_three_tier.py``. The
evaluator may report provisional metrics for diagnosis, but this checker fails
closed unless the selected provider has enough scoreable fixtures, no
provisional expected fixtures, no expected-quality warnings, no raw artifact
storage flags, and a metric value at or above the configured threshold.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_PROVIDER = "paddleocr_local"
DEFAULT_METRIC = "scoreable_ingredient_name_exact_rate"
DEFAULT_MIN_RATE = 0.95
DEFAULT_MIN_SCOREABLE_FIXTURES = 16
DEFAULT_MAX_PROVISIONAL_FIXTURES = 0
DEFAULT_MAX_EXPECTED_QUALITY_WARNINGS = 0
DEFAULT_MAX_PROVIDER_ERRORS = 0


@dataclass(frozen=True)
class KpiReadinessFinding:
    """One bounded KPI readiness finding.

    Attributes:
        code: Stable finding code.
        detail: Bounded detail without raw OCR text, provider payloads, or secrets.
    """

    code: str
    detail: str


@dataclass(frozen=True)
class KpiReadinessResult:
    """KPI readiness result.

    Attributes:
        provider: Provider name being checked.
        findings: Bounded findings. Empty means the evaluation is ready.
    """

    provider: str
    findings: tuple[KpiReadinessFinding, ...]

    @property
    def ok(self) -> bool:
        """Return whether all KPI readiness checks passed.

        Returns:
            True when no findings were produced.
        """
        return not self.findings


def check_kpi_readiness(
    *,
    evaluation_path: Path,
    provider: str = DEFAULT_PROVIDER,
    metric: str = DEFAULT_METRIC,
    min_rate: float = DEFAULT_MIN_RATE,
    min_scoreable_fixtures: int = DEFAULT_MIN_SCOREABLE_FIXTURES,
    max_provisional_fixtures: int = DEFAULT_MAX_PROVISIONAL_FIXTURES,
    max_expected_quality_warnings: int = DEFAULT_MAX_EXPECTED_QUALITY_WARNINGS,
    max_provider_errors: int = DEFAULT_MAX_PROVIDER_ERRORS,
) -> KpiReadinessResult:
    """Check one evaluation JSON for official KPI readiness.

    Args:
        evaluation_path: Redacted ``ocr-three-tier-evaluation.json`` path.
        provider: Provider key under ``summary["providers"]``.
        metric: Provider metric key to compare with ``min_rate``.
        min_rate: Minimum acceptable metric value.
        min_scoreable_fixtures: Minimum required scoreable fixture count.
        max_provisional_fixtures: Maximum allowed provisional expected fixtures.
        max_expected_quality_warnings: Maximum allowed expected quality warnings.
        max_provider_errors: Maximum allowed provider error observations.

    Returns:
        KPI readiness result.
    """
    summary = _read_evaluation(evaluation_path)
    findings: list[KpiReadinessFinding] = []
    findings.extend(_privacy_findings(summary))
    findings.extend(
        _summary_quality_findings(
            summary=summary,
            min_scoreable_fixtures=min_scoreable_fixtures,
            max_provisional_fixtures=max_provisional_fixtures,
            max_expected_quality_warnings=max_expected_quality_warnings,
        )
    )
    providers = summary.get("providers")
    if not isinstance(providers, dict):
        findings.append(KpiReadinessFinding("providers_missing", "providers_not_object"))
        return KpiReadinessResult(provider=provider, findings=tuple(findings))
    raw_metrics = providers.get(provider)
    if not isinstance(raw_metrics, dict):
        findings.append(KpiReadinessFinding("provider_missing", f"provider={provider}"))
        return KpiReadinessResult(provider=provider, findings=tuple(findings))
    findings.extend(
        _provider_quality_findings(
            provider=provider,
            metrics=raw_metrics,
            metric=metric,
            min_rate=min_rate,
            max_provider_errors=max_provider_errors,
        )
    )
    return KpiReadinessResult(provider=provider, findings=tuple(findings))


def _read_evaluation(path: Path) -> dict[str, Any]:
    """Read a redacted evaluation JSON file.

    Args:
        path: Evaluation JSON path.

    Returns:
        Parsed evaluation object.

    Raises:
        ValueError: If the file is not a JSON object.
    """
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("evaluation JSON must be an object")
    return parsed


def _privacy_findings(summary: dict[str, Any]) -> list[KpiReadinessFinding]:
    """Return findings for raw artifact storage flags.

    Args:
        summary: Parsed evaluation summary.

    Returns:
        Privacy-related KPI findings.
    """
    findings: list[KpiReadinessFinding] = []
    if summary.get("raw_artifacts_stored") is not False:
        findings.append(
            KpiReadinessFinding(
                "raw_artifacts_flag_not_false",
                f"value={summary.get('raw_artifacts_stored')!r}",
            )
        )
    if summary.get("raw_ocr_text_stored") is not False:
        findings.append(
            KpiReadinessFinding(
                "raw_ocr_text_flag_not_false",
                f"value={summary.get('raw_ocr_text_stored')!r}",
            )
        )
    return findings


def _summary_quality_findings(
    *,
    summary: dict[str, Any],
    min_scoreable_fixtures: int,
    max_provisional_fixtures: int,
    max_expected_quality_warnings: int,
) -> list[KpiReadinessFinding]:
    """Return findings for expected-data quality gates.

    Args:
        summary: Parsed evaluation summary.
        min_scoreable_fixtures: Minimum required scoreable fixtures.
        max_provisional_fixtures: Maximum allowed provisional fixtures.
        max_expected_quality_warnings: Maximum allowed expected-quality warning count.

    Returns:
        Expected-data findings.
    """
    findings: list[KpiReadinessFinding] = []
    scoreable_count = _int_value(summary.get("scoreable_fixture_count"))
    if scoreable_count is None or scoreable_count < min_scoreable_fixtures:
        findings.append(
            KpiReadinessFinding(
                "scoreable_fixture_count_below_min",
                f"value={scoreable_count} min={min_scoreable_fixtures}",
            )
        )
    provisional_count = _int_value(summary.get("provisional_fixture_count"))
    if provisional_count is None or provisional_count > max_provisional_fixtures:
        findings.append(
            KpiReadinessFinding(
                "provisional_fixture_count_exceeded",
                f"value={provisional_count} max={max_provisional_fixtures}",
            )
        )
    warnings = summary.get("expected_quality_warnings")
    warning_count = len(warnings) if isinstance(warnings, list) else None
    if warning_count is None or warning_count > max_expected_quality_warnings:
        findings.append(
            KpiReadinessFinding(
                "expected_quality_warnings_exceeded",
                f"value={warning_count} max={max_expected_quality_warnings}",
            )
        )
    return findings


def _provider_quality_findings(
    *,
    provider: str,
    metrics: dict[str, Any],
    metric: str,
    min_rate: float,
    max_provider_errors: int,
) -> list[KpiReadinessFinding]:
    """Return findings for provider-level KPI gates.

    Args:
        provider: Provider name being checked.
        metrics: Provider metric dictionary.
        metric: Metric key to compare.
        min_rate: Minimum acceptable rate.
        max_provider_errors: Maximum allowed provider errors.

    Returns:
        Provider-level findings.
    """
    findings: list[KpiReadinessFinding] = []
    error_count = _int_value(metrics.get("errors"))
    if error_count is None or error_count > max_provider_errors:
        findings.append(
            KpiReadinessFinding(
                "provider_errors_exceeded",
                f"provider={provider} value={error_count} max={max_provider_errors}",
            )
        )
    rate = _float_value(metrics.get(metric))
    if rate is None:
        findings.append(
            KpiReadinessFinding(
                "metric_missing",
                f"provider={provider} metric={metric}",
            )
        )
    elif rate < min_rate:
        findings.append(
            KpiReadinessFinding(
                "metric_below_min",
                f"provider={provider} metric={metric} value={rate} min={min_rate}",
            )
        )
    return findings


def _int_value(value: Any) -> int | None:
    """Return ``value`` as int when it is a non-bool integer.

    Args:
        value: Candidate value.

    Returns:
        Integer value or None.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _float_value(value: Any) -> float | None:
    """Return ``value`` as float when numeric and finite enough for comparison.

    Args:
        value: Candidate value.

    Returns:
        Float value or None.
    """
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) else None


def _print_result(result: KpiReadinessResult) -> None:
    """Print bounded CLI diagnostics.

    Args:
        result: Readiness result to print.
    """
    if result.ok:
        print(f"ocr_kpi_ready provider={result.provider}")
        return
    for finding in result.findings:
        print(f"{finding.code} {finding.detail}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """Run the KPI readiness gate.

    Args:
        argv: Optional CLI argument list.

    Returns:
        Process exit code. Zero means the selected provider can support the
        configured official KPI claim.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", required=True, type=Path)
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--metric", default=DEFAULT_METRIC)
    parser.add_argument("--min-rate", type=float, default=DEFAULT_MIN_RATE)
    parser.add_argument(
        "--min-scoreable-fixtures",
        type=int,
        default=DEFAULT_MIN_SCOREABLE_FIXTURES,
    )
    parser.add_argument(
        "--max-provisional-fixtures",
        type=int,
        default=DEFAULT_MAX_PROVISIONAL_FIXTURES,
    )
    parser.add_argument(
        "--max-expected-quality-warnings",
        type=int,
        default=DEFAULT_MAX_EXPECTED_QUALITY_WARNINGS,
    )
    parser.add_argument("--max-provider-errors", type=int, default=DEFAULT_MAX_PROVIDER_ERRORS)
    args = parser.parse_args(argv)

    result = check_kpi_readiness(
        evaluation_path=args.evaluation,
        provider=args.provider,
        metric=args.metric,
        min_rate=args.min_rate,
        min_scoreable_fixtures=args.min_scoreable_fixtures,
        max_provisional_fixtures=args.max_provisional_fixtures,
        max_expected_quality_warnings=args.max_expected_quality_warnings,
        max_provider_errors=args.max_provider_errors,
    )
    _print_result(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
