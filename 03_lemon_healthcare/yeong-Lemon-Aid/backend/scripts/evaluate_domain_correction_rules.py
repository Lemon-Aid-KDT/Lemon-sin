"""Evaluate parser/domain correction metrics from redacted fixture reports."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from src.services.parser_domain_correction import (
    PRIMARY_DOMAIN_CORRECTION_METRICS,
    SAFETY_DOMAIN_CORRECTION_METRICS,
    evaluate_domain_correction_promotion_gate,
    reject_forbidden_correction_fields,
)


def main() -> None:
    """Run the parser/domain correction evaluator from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=False, type=Path)
    args = parser.parse_args()

    summary = evaluate_manifest(args.manifest)
    if args.output_dir is None:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "parser-domain-correction-evaluation.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "parser-domain-correction-evaluation.md").write_text(
        _render_markdown(summary),
        encoding="utf-8",
    )


def evaluate_manifest(manifest_path: Path) -> dict[str, object]:
    """Evaluate a redacted parser/domain correction metrics manifest.

    Args:
        manifest_path: Manifest containing aggregate baseline and candidate metrics.

    Returns:
        Promotion decision and metric deltas.

    Raises:
        ValueError: If raw OCR/image/provider fields are present or the manifest is malformed.
    """
    parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
    reject_forbidden_correction_fields(parsed)
    if not isinstance(parsed, dict):
        raise ValueError("Manifest must be a JSON object.")
    baseline = _mapping(parsed.get("baseline"))
    candidate = _mapping(parsed.get("candidate"))
    decision = evaluate_domain_correction_promotion_gate(
        baseline=baseline,
        candidate=candidate,
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest": str(manifest_path),
        "promotion": decision,
        "metric_delta": {
            metric: _metric(candidate.get(metric)) - _metric(baseline.get(metric))
            for metric in PRIMARY_DOMAIN_CORRECTION_METRICS
        },
        "safety_metrics": {
            metric: _metric(candidate.get(metric)) for metric in SAFETY_DOMAIN_CORRECTION_METRICS
        },
    }


def _mapping(value: object) -> Mapping[str, object]:
    """Validate a manifest metrics object.

    Args:
        value: Candidate metrics object.

    Returns:
        Metrics mapping.

    Raises:
        ValueError: If the value is not a mapping.
    """
    if not isinstance(value, Mapping):
        raise ValueError("Manifest must contain baseline and candidate metric objects.")
    return value


def _metric(value: object) -> float:
    """Return a numeric metric value or zero.

    Args:
        value: Candidate metric value.

    Returns:
        Numeric metric value.
    """
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _render_markdown(summary: Mapping[str, object]) -> str:
    """Render a compact Markdown evaluation report.

    Args:
        summary: Evaluation summary.

    Returns:
        Markdown report.
    """
    promotion = summary["promotion"]
    assert isinstance(promotion, Mapping)
    lines = [
        "# Parser/domain correction evaluation",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Promotable: `{promotion['promotable']}`",
        f"- Errors: `{promotion['errors']}`",
        "",
        "## Metric delta",
    ]
    metric_delta = summary["metric_delta"]
    assert isinstance(metric_delta, Mapping)
    for metric, value in metric_delta.items():
        lines.append(f"- `{metric}`: `{value}`")
    lines.extend(["", "## Safety metrics"])
    safety_metrics = summary["safety_metrics"]
    assert isinstance(safety_metrics, Mapping)
    for metric, value in safety_metrics.items():
        lines.append(f"- `{metric}`: `{value}`")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
