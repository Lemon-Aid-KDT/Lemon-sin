"""Evaluate redacted ROI-crop impact metrics for supplement OCR fixtures.

The input is a JSON manifest of precomputed metrics. This script does not call
OCR providers, read raw OCR text, or inspect raw image bytes.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

RAW_FORBIDDEN_KEYS = {
    "api_key",
    "authorization",
    "image_bytes",
    "raw_image",
    "raw_ocr_text",
    "raw_provider_payload",
    "request_headers",
    "service_key",
}
METRIC_KEYS = (
    "field_exact_match_rate",
    "numeric_exact_match_rate",
    "unit_exact_match_rate",
    "parser_success_rate",
)


@dataclass
class MetricAccumulator:
    """Aggregate before/after ROI metric deltas."""

    total_cases: int = 0
    roi_available_cases: int = 0
    metric_totals: dict[str, float] | None = None

    def __post_init__(self) -> None:
        """Initialize metric total state after dataclass construction."""
        if self.metric_totals is None:
            self.metric_totals = dict.fromkeys(METRIC_KEYS, 0.0)


def main() -> None:
    """Run the ROI impact evaluator from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=False, type=Path)
    args = parser.parse_args()

    summary = evaluate_manifest(args.manifest)
    if args.output_dir is None:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "roi-ocr-impact.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "roi-ocr-impact.md").write_text(_render_markdown(summary), encoding="utf-8")


def evaluate_manifest(manifest_path: Path) -> dict[str, object]:
    """Evaluate a redacted ROI OCR impact manifest.

    Args:
        manifest_path: Metric manifest path.

    Returns:
        Aggregate ROI impact summary.

    Raises:
        ValueError: If the manifest shape is invalid or contains raw fields.
    """
    parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
    _reject_raw_fields(parsed)
    cases = parsed.get("cases") if isinstance(parsed, dict) else None
    if not isinstance(cases, list):
        raise ValueError("Manifest must contain a cases list.")

    accumulator = MetricAccumulator()
    case_summaries: list[dict[str, object]] = []
    for raw_case in cases:
        if not isinstance(raw_case, dict):
            raise ValueError("Each case must be an object.")
        _reject_raw_fields(raw_case)
        case_summaries.append(_evaluate_case(raw_case, accumulator))

    assert accumulator.metric_totals is not None
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest": str(manifest_path),
        "case_count": accumulator.total_cases,
        "roi_available_cases": accumulator.roi_available_cases,
        "average_metric_delta": {
            key: _rate(accumulator.metric_totals[key], accumulator.roi_available_cases)
            for key in METRIC_KEYS
        },
        "cases": case_summaries,
        "interpretation": (
            "ROI impact metrics compare fixture observations for original versus crop "
            "inputs. They are not live OCR performance claims."
        ),
    }


def _evaluate_case(
    raw_case: dict[str, object], accumulator: MetricAccumulator
) -> dict[str, object]:
    """Evaluate one ROI impact case.

    Args:
        raw_case: Raw manifest case.
        accumulator: Mutable aggregate state.

    Returns:
        Redacted case summary.
    """
    case_id = raw_case.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("Each case requires a non-empty case_id.")
    original = _metric_mapping(raw_case.get("original"))
    roi_crop = _metric_mapping(raw_case.get("roi_crop"))

    accumulator.total_cases += 1
    roi_available = bool(raw_case.get("roi_available", bool(roi_crop)))
    if roi_available:
        accumulator.roi_available_cases += 1

    deltas = {
        key: _metric_value(roi_crop, key) - _metric_value(original, key) for key in METRIC_KEYS
    }
    assert accumulator.metric_totals is not None
    for key, value in deltas.items():
        accumulator.metric_totals[key] += value

    return {
        "case_id": case_id,
        "roi_available": roi_available,
        "metric_delta": deltas,
    }


def _metric_mapping(value: object) -> dict[str, object]:
    """Return a metric mapping.

    Args:
        value: Candidate mapping.

    Returns:
        Metric mapping, or empty dictionary.
    """
    if isinstance(value, dict):
        return value
    return {}


def _metric_value(mapping: dict[str, object], key: str) -> float:
    """Return a bounded metric value.

    Args:
        mapping: Metric mapping.
        key: Metric key.

    Returns:
        Metric value from 0.0 to 1.0, defaulting to 0.0.
    """
    value = mapping.get(key)
    if isinstance(value, int | float) and 0 <= value <= 1:
        return float(value)
    return 0.0


def _reject_raw_fields(value: object) -> None:
    """Reject forbidden raw-data keys recursively.

    Args:
        value: Candidate manifest value.

    Raises:
        ValueError: If a forbidden key is present.
    """
    if isinstance(value, dict):
        forbidden = RAW_FORBIDDEN_KEYS.intersection(str(key).lower() for key in value)
        if forbidden:
            raise ValueError(f"Manifest contains forbidden raw field(s): {sorted(forbidden)}")
        for nested_value in value.values():
            _reject_raw_fields(nested_value)
    elif isinstance(value, list):
        for item in value:
            _reject_raw_fields(item)


def _rate(numerator: float, denominator: int) -> float | None:
    """Return a rounded rate.

    Args:
        numerator: Numerator.
        denominator: Denominator.

    Returns:
        Rounded rate, or None when denominator is zero.
    """
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def _render_markdown(summary: dict[str, object]) -> str:
    """Render a short Markdown report.

    Args:
        summary: Evaluation summary.

    Returns:
        Markdown report.
    """
    lines = [
        "# ROI OCR Impact Evaluation",
        "",
        f"- Cases: {summary['case_count']}",
        f"- ROI available cases: {summary['roi_available_cases']}",
        "",
        "## Average Metric Delta",
    ]
    deltas = summary.get("average_metric_delta", {})
    if isinstance(deltas, dict):
        for key in METRIC_KEYS:
            lines.append(f"- `{key}`: {deltas.get(key)}")
    lines.append("")
    lines.append(str(summary["interpretation"]))
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
