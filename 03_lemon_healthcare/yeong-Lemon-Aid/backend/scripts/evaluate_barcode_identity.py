"""Generate redacted barcode identity fixture evaluation reports.

The script consumes JSONL fixture rows and provider observations. It does not
call live FoodQR or MFDS APIs; live smoke tests stay explicit opt-in gates.
This keeps fixture evaluation reproducible and prevents credentials, full URLs,
or raw provider payloads from entering committed artifacts.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

RAW_FORBIDDEN_KEYS = {
    "full_url",
    "keyId",
    "mfds_api_key",
    "query",
    "raw_api_payload",
    "raw_payload",
    "request_url",
    "serviceKey",
    "service_key",
    "foodqr_service_key",
}


@dataclass
class ProviderMetrics:
    """Aggregate metrics for one barcode identity provider."""

    calls: int = 0
    matched_count: int = 0
    not_found_count: int = 0
    provider_error_count: int = 0
    single_item_count: int = 0
    multi_item_count: int = 0
    max_item_count: int | None = None
    expected_status_matches: int = 0
    expected_status_total: int = 0

    def as_dict(self) -> dict[str, object]:
        """Return serializable metrics.

        Returns:
            Provider metrics as a dictionary.
        """
        return {
            "calls": self.calls,
            "matched_rate": _rate(self.matched_count, self.calls),
            "not_found_rate": _rate(self.not_found_count, self.calls),
            "provider_error_rate": _rate(self.provider_error_count, self.calls),
            "single_item_observation_count": self.single_item_count,
            "multi_item_observation_count": self.multi_item_count,
            "max_item_count": self.max_item_count,
            "expected_status_match_rate": _rate(
                self.expected_status_matches,
                self.expected_status_total,
            ),
        }


@dataclass
class EvaluationAccumulator:
    """Aggregate barcode fixture evaluation state."""

    fixture_count: int = 0
    observation_count: int = 0
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
    json_path = args.output_dir / "barcode-identity-evaluation.json"
    markdown_path = args.output_dir / "barcode-identity-evaluation.md"
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
        ValueError: If manifest rows contain credentials, full URLs, or raw payloads.
    """
    accumulator = EvaluationAccumulator()
    for row in _read_manifest_rows(manifest_path):
        _reject_raw_fields(row)
        accumulator.fixture_count += 1

        observations = row.get("observations", [])
        if not isinstance(observations, list):
            continue
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            _reject_raw_fields(observation)
            _add_observation(accumulator, observation=observation)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest": str(manifest_path),
        "fixture_count": accumulator.fixture_count,
        "observation_count": accumulator.observation_count,
        "providers": {
            provider: metrics.as_dict()
            for provider, metrics in sorted(accumulator.providers.items())
        },
        "raw_provider_payload_stored": False,
        "credentials_stored": False,
        "interpretation": (
            "Provider status rates are fixture observations, not barcode accuracy, "
            "MFDS coverage, or OCR improvement metrics."
        ),
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
    """Reject credentials, full URLs, and raw provider payloads recursively.

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


def _add_observation(
    accumulator: EvaluationAccumulator,
    *,
    observation: dict[str, object],
) -> None:
    """Add one provider observation to aggregate metrics.

    Args:
        accumulator: Mutable aggregate state.
        observation: Observation row.
    """
    provider = observation.get("provider")
    if not isinstance(provider, str) or not provider:
        return
    status = observation.get("status")
    if not isinstance(status, str):
        return

    accumulator.observation_count += 1
    metrics = accumulator.providers[provider]
    metrics.calls += 1
    if status == "matched":
        metrics.matched_count += 1
    elif status == "not_found":
        metrics.not_found_count += 1
    elif status == "provider_error":
        metrics.provider_error_count += 1

    item_count = observation.get("item_count")
    if isinstance(item_count, int):
        metrics.max_item_count = (
            item_count
            if metrics.max_item_count is None
            else max(metrics.max_item_count, item_count)
        )
        if item_count == 1:
            metrics.single_item_count += 1
        elif item_count > 1:
            metrics.multi_item_count += 1

    expected_status = observation.get("expected_status")
    if isinstance(expected_status, str):
        metrics.expected_status_total += 1
        if expected_status == status:
            metrics.expected_status_matches += 1


def _rate(numerator: int, denominator: int) -> float | None:
    """Return a rounded rate or None for an empty denominator.

    Args:
        numerator: Numerator.
        denominator: Denominator.

    Returns:
        Rounded rate or None.
    """
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _render_markdown(summary: dict[str, object]) -> str:
    """Render a short Markdown report.

    Args:
        summary: Evaluation summary.

    Returns:
        Markdown report.
    """
    lines = [
        "# Barcode Identity Evaluation",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- fixture_count: `{summary['fixture_count']}`",
        f"- observation_count: `{summary['observation_count']}`",
        f"- raw_provider_payload_stored: `{summary['raw_provider_payload_stored']}`",
        f"- credentials_stored: `{summary['credentials_stored']}`",
        f"- interpretation: {summary['interpretation']}",
        "",
        "## Providers",
        "",
    ]
    providers = summary.get("providers", {})
    if not isinstance(providers, dict) or not providers:
        lines.append("- No provider observations were supplied.")
        return "\n".join(lines) + "\n"

    for provider, raw_metrics in providers.items():
        if not isinstance(raw_metrics, dict):
            continue
        lines.extend(
            [
                f"### {provider}",
                "",
                f"- calls: `{raw_metrics.get('calls')}`",
                f"- matched_rate: `{raw_metrics.get('matched_rate')}`",
                f"- not_found_rate: `{raw_metrics.get('not_found_rate')}`",
                f"- provider_error_rate: `{raw_metrics.get('provider_error_rate')}`",
                (
                    "- single_item_observation_count: "
                    f"`{raw_metrics.get('single_item_observation_count')}`"
                ),
                (
                    "- multi_item_observation_count: "
                    f"`{raw_metrics.get('multi_item_observation_count')}`"
                ),
                f"- max_item_count: `{raw_metrics.get('max_item_count')}`",
                (
                    "- expected_status_match_rate: "
                    f"`{raw_metrics.get('expected_status_match_rate')}`"
                ),
                "",
            ]
        )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
