"""Generate redacted OCR 3-tier fixture evaluation reports.

The script consumes JSONL fixture rows and optional provider observations. It
does not call real OCR providers; smoke tests for Google/CLOVA remain explicit
opt-in gates. This keeps report generation reproducible and prevents raw image
or raw OCR text from being written into artifacts.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

RAW_FORBIDDEN_KEYS = {"image_bytes", "raw_image", "raw_ocr_text", "ocr_text"}


@dataclass
class ProviderMetrics:
    """Aggregate metrics for one OCR provider observation set."""

    calls: int = 0
    non_empty_count: int = 0
    parser_success_count: int = 0
    total_latency_ms: float = 0.0
    ingredient_name_matches: int = 0
    ingredient_name_total: int = 0
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
        }


@dataclass
class EvaluationAccumulator:
    """Aggregate OCR fixture evaluation state."""

    fixture_count: int = 0
    missing_image_count: int = 0
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

        expected_names = _expected_ingredient_names(row.get("expected"))
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
                expected_names=expected_names,
                expected_conditions=expected_conditions,
            )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest": str(manifest_path),
        "fixture_count": accumulator.fixture_count,
        "missing_image_count": accumulator.missing_image_count,
        "observation_count": accumulator.observation_count,
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


def _expected_ingredient_names(value: object) -> set[str]:
    """Extract normalized expected ingredient names.

    Args:
        value: Expected fixture object.

    Returns:
        Normalized expected names.
    """
    if not isinstance(value, dict):
        return set()
    ingredients = value.get("ingredients")
    if not isinstance(ingredients, list):
        return set()
    names: set[str] = set()
    for ingredient in ingredients:
        if not isinstance(ingredient, dict):
            continue
        name = ingredient.get("name")
        if isinstance(name, str):
            names.add(_normalize_token(name))
    return names


def _add_observation(
    accumulator: EvaluationAccumulator,
    *,
    observation: dict[str, object],
    expected_names: set[str],
    expected_conditions: list[str] | None = None,
) -> None:
    """Add one provider observation to aggregate metrics.

    Args:
        accumulator: Mutable aggregate state.
        observation: Observation row.
        expected_names: Expected normalized ingredient names.
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
    if observation.get("error") is True:
        metrics.errors += 1

    latency_ms = observation.get("latency_ms")
    if isinstance(latency_ms, int | float) and latency_ms >= 0:
        metrics.total_latency_ms += float(latency_ms)

    observed_names = _observed_ingredient_names(observation.get("parsed_ingredients"))
    if expected_names:
        metrics.ingredient_name_total += len(expected_names)
        match_count = len(expected_names.intersection(observed_names))
        metrics.ingredient_name_matches += match_count
        if expected_conditions:
            for condition in expected_conditions:
                metrics.ingredient_total_by_condition[condition] = (
                    metrics.ingredient_total_by_condition.get(condition, 0) + len(expected_names)
                )
                metrics.ingredient_matches_by_condition[condition] = (
                    metrics.ingredient_matches_by_condition.get(condition, 0) + match_count
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
        f"- Missing image files: `{summary['missing_image_count']}`",
        f"- Raw image artifacts stored: `{summary['raw_artifacts_stored']}`",
        f"- Raw OCR text stored: `{summary['raw_ocr_text_stored']}`",
        "",
        "## Provider Metrics",
        "",
        "| Provider | Calls | Text non-empty | Parser success | Avg latency ms | Ingredient name exact | Errors | LLM attempts | LLM parse success | LLM ingredient exact |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    providers = summary.get("providers", {})
    if isinstance(providers, dict):
        for provider, raw_metrics in providers.items():
            if not isinstance(raw_metrics, dict):
                continue
            lines.append(
                "| {provider} | {calls} | {text_rate} | {parser_rate} | {latency} | {ingredient_rate} | {errors} | {llm_attempts} | {llm_parse_rate} | {llm_ingredient_rate} |".format(
                    provider=provider,
                    calls=raw_metrics.get("calls"),
                    text_rate=raw_metrics.get("text_non_empty_rate"),
                    parser_rate=raw_metrics.get("parser_success_rate"),
                    latency=raw_metrics.get("average_latency_ms"),
                    ingredient_rate=raw_metrics.get("ingredient_name_exact_rate"),
                    errors=raw_metrics.get("errors"),
                    llm_attempts=raw_metrics.get("llm_parse_attempt_count"),
                    llm_parse_rate=raw_metrics.get("llm_parse_success_rate"),
                    llm_ingredient_rate=raw_metrics.get("llm_ingredient_name_exact_rate"),
                )
            )
    lines.extend(
        [
            "",
            "## Language-Segmented Error Rates (한국어/영문)",
            "",
            "| Provider | CER ko (avg) | CER en (avg) | WER ko (avg) | WER en (avg) |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    if isinstance(providers, dict):
        for provider, raw_metrics in providers.items():
            if not isinstance(raw_metrics, dict):
                continue
            lines.append(
                "| {provider} | {cer_ko} | {cer_en} | {wer_ko} | {wer_en} |".format(
                    provider=provider,
                    cer_ko=raw_metrics.get("cer_ko_avg"),
                    cer_en=raw_metrics.get("cer_en_avg"),
                    wer_ko=raw_metrics.get("wer_ko_avg"),
                    wer_en=raw_metrics.get("wer_en_avg"),
                )
            )
    lines.extend(
        [
            "",
            "## 만성질환별 정확도 (B형 페르소나 시나리오)",
            "",
            "Expected fixture 의 ``chronic_disease_indications`` 별로 분리한 ingredient_name_exact_rate.",
            "값이 비어 있으면 해당 fixture set 에 그 만성질환 인디케이션 라벨이 없음을 뜻한다.",
            "",
        ]
    )
    if isinstance(providers, dict):
        for provider, raw_metrics in providers.items():
            if not isinstance(raw_metrics, dict):
                continue
            condition_map = raw_metrics.get("accuracy_by_condition")
            if not isinstance(condition_map, dict) or not condition_map:
                continue
            lines.append(f"### {provider}")
            lines.append("")
            lines.append("| Chronic condition | accuracy |")
            lines.append("| --- | ---: |")
            for condition, accuracy in sorted(condition_map.items()):
                lines.append(f"| {condition} | {accuracy} |")
            lines.append("")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
