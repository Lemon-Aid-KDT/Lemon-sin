"""Build a redacted OCR ground-truth human review queue.

This tool turns a three-tier evaluation and its manifest into a bounded queue
for human ground-truth cleanup. It does not read or write raw OCR text, provider
payloads, request headers, image bytes, or secrets. The output contains only
fixture identifiers, expected-summary metadata, provider status codes, and
review action hints.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

RAW_FORBIDDEN_KEYS = {
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
DEFAULT_PROVIDER = "paddleocr_local"
MAX_EXPECTED_NAMES = 20
MAX_EXPECTED_NAME_LENGTH = 120
IMAGE_SHA256_PREFIX_LENGTH = 12


@dataclass(frozen=True)
class ReviewQueueItem:
    """One bounded fixture row requiring human review.

    Attributes:
        fixture_id: Stable fixture identifier.
        priority: Lower number means review sooner.
        review_reasons: Bounded reason codes from evaluation/provider state.
        recommended_actions: Bounded action hints for the reviewer.
        expected_ingredient_count: Current expected ingredient row count.
        expected_names: Current expected display names, truncated and bounded.
        provider_status: Provider observation status.
        provider_error_code: Optional bounded provider error code.
        text_non_empty: Whether provider output was non-empty.
        layout_available: Whether provider layout metadata was usable.
        parsed_ingredient_count: Number of redacted parsed ingredients.
        image_path: Manifest image path as supplied, never resolved to an
            absolute local path.
        image_sha256_prefix: First 12 chars of the fixture image hash, when
            present.
    """

    fixture_id: str
    priority: int
    review_reasons: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    expected_ingredient_count: int
    expected_names: tuple[str, ...]
    provider_status: str
    provider_error_code: str | None
    text_non_empty: bool
    layout_available: bool
    parsed_ingredient_count: int
    image_path: str | None
    image_sha256_prefix: str | None

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable review queue row.

        Returns:
            Bounded review queue row.
        """
        row: dict[str, object] = {
            "fixture_id": self.fixture_id,
            "priority": self.priority,
            "review_status": "pending_human_review",
            "review_reasons": list(self.review_reasons),
            "recommended_actions": list(self.recommended_actions),
            "expected_ingredient_count": self.expected_ingredient_count,
            "expected_names": list(self.expected_names),
            "provider_status": self.provider_status,
            "text_non_empty": self.text_non_empty,
            "layout_available": self.layout_available,
            "parsed_ingredient_count": self.parsed_ingredient_count,
        }
        if self.provider_error_code is not None:
            row["provider_error_code"] = self.provider_error_code
        if self.image_path is not None:
            row["image_path"] = self.image_path
        if self.image_sha256_prefix is not None:
            row["image_sha256_prefix"] = self.image_sha256_prefix
        return row


def build_review_queue(
    *,
    manifest_path: Path,
    evaluation_path: Path,
    provider: str = DEFAULT_PROVIDER,
) -> list[ReviewQueueItem]:
    """Build a redacted human review queue from manifest/evaluation artifacts.

    Args:
        manifest_path: Manifest JSONL containing expected fields and observations.
        evaluation_path: Evaluation JSON produced by ``evaluate_ocr_three_tier.py``.
        provider: Provider observation key to inspect.

    Returns:
        Review queue items sorted by priority and fixture id.
    """
    manifest_rows = _read_manifest_rows(manifest_path)
    evaluation = _read_evaluation(evaluation_path)
    warnings_by_fixture = _expected_warning_codes_by_fixture(evaluation)
    unscoreable_ids = _string_set(evaluation.get("unscoreable_fixture_ids"))
    queue: list[ReviewQueueItem] = []
    for row in manifest_rows:
        fixture_id = row.get("fixture_id")
        if not isinstance(fixture_id, str) or not fixture_id:
            continue
        expected = row.get("expected") if isinstance(row.get("expected"), dict) else {}
        observation = _provider_observation(row, provider)
        review_reasons = _review_reasons(
            warning_codes=warnings_by_fixture.get(fixture_id, ()),
            is_unscoreable=fixture_id in unscoreable_ids,
            observation=observation,
        )
        if not review_reasons:
            continue
        queue.append(
            ReviewQueueItem(
                fixture_id=fixture_id,
                priority=_priority(review_reasons),
                review_reasons=review_reasons,
                recommended_actions=_recommended_actions(review_reasons),
                expected_ingredient_count=len(_expected_ingredients(expected)),
                expected_names=tuple(_expected_names(expected)),
                provider_status=_string_field(observation.get("status"), "missing"),
                provider_error_code=_optional_string_field(observation.get("error_code")),
                text_non_empty=observation.get("text_non_empty") is True,
                layout_available=observation.get("layout_available") is True,
                parsed_ingredient_count=_list_count(observation.get("parsed_ingredients")),
                image_path=_optional_string_field(row.get("image_path")),
                image_sha256_prefix=_hash_prefix(row.get("image_sha256")),
            )
        )
    return sorted(queue, key=lambda item: (item.priority, item.fixture_id))


def write_review_queue(
    *,
    manifest_path: Path,
    evaluation_path: Path,
    output_dir: Path,
    provider: str = DEFAULT_PROVIDER,
) -> tuple[Path, Path, list[ReviewQueueItem]]:
    """Write JSONL and Markdown review queue artifacts.

    Args:
        manifest_path: Source manifest JSONL.
        evaluation_path: Source evaluation JSON.
        output_dir: Destination directory.
        provider: Provider observation key to inspect.

    Returns:
        JSONL path, Markdown path, and in-memory queue items.
    """
    queue = build_review_queue(
        manifest_path=manifest_path,
        evaluation_path=evaluation_path,
        provider=provider,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "ground-truth-review-queue.jsonl"
    markdown_path = output_dir / "ground-truth-review-queue.md"
    jsonl_path.write_text(
        "".join(json.dumps(item.as_dict(), ensure_ascii=False) + "\n" for item in queue),
        encoding="utf-8",
    )
    markdown_path.write_text(
        _render_markdown(
            queue=queue,
            manifest_path=manifest_path,
            evaluation_path=evaluation_path,
            provider=provider,
        ),
        encoding="utf-8",
    )
    return jsonl_path, markdown_path, queue


def _read_manifest_rows(path: Path) -> list[dict[str, object]]:
    """Read manifest rows and reject raw fields.

    Args:
        path: JSONL manifest path.

    Returns:
        Parsed manifest rows.
    """
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise ValueError(f"Manifest line {line_number} must be a JSON object.")
        _reject_raw_fields(parsed)
        rows.append(parsed)
    return rows


def _read_evaluation(path: Path) -> dict[str, object]:
    """Read evaluation JSON and reject raw fields.

    Args:
        path: Evaluation JSON path.

    Returns:
        Parsed evaluation object.
    """
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Evaluation JSON must be an object.")
    _reject_raw_fields(parsed)
    return parsed


def _reject_raw_fields(value: object) -> None:
    """Reject raw image/OCR/provider fields recursively.

    Args:
        value: Candidate parsed value.

    Raises:
        ValueError: If forbidden raw-data keys are present.
    """
    if isinstance(value, dict):
        forbidden = RAW_FORBIDDEN_KEYS.intersection(str(key).lower() for key in value)
        if forbidden:
            raise ValueError(f"Forbidden raw field(s): {sorted(forbidden)}")
        for nested_value in value.values():
            _reject_raw_fields(nested_value)
    elif isinstance(value, list):
        for item in value:
            _reject_raw_fields(item)


def _expected_warning_codes_by_fixture(
    evaluation: dict[str, object],
) -> dict[str, tuple[str, ...]]:
    """Group expected-quality warning codes by fixture id.

    Args:
        evaluation: Evaluation summary.

    Returns:
        Mapping of fixture id to warning codes.
    """
    grouped: dict[str, list[str]] = {}
    warnings = evaluation.get("expected_quality_warnings")
    if not isinstance(warnings, list):
        return {}
    for warning in warnings:
        if not isinstance(warning, dict):
            continue
        fixture_id = warning.get("fixture_id")
        code = warning.get("code")
        if not isinstance(fixture_id, str) or not isinstance(code, str):
            continue
        grouped.setdefault(fixture_id, []).append(code)
    return {fixture_id: tuple(sorted(set(codes))) for fixture_id, codes in sorted(grouped.items())}


def _provider_observation(row: dict[str, object], provider: str) -> dict[str, object]:
    """Return the provider observation for a manifest row.

    Args:
        row: Manifest row.
        provider: Provider key.

    Returns:
        Provider observation dict or an empty dict.
    """
    observations = row.get("observations")
    if not isinstance(observations, list):
        return {}
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        if observation.get("provider") == provider:
            return observation
    return {}


def _review_reasons(
    *,
    warning_codes: tuple[str, ...],
    is_unscoreable: bool,
    observation: dict[str, object],
) -> tuple[str, ...]:
    """Return bounded reason codes for review.

    Args:
        warning_codes: Expected-quality warning codes.
        is_unscoreable: Whether the fixture lacks scoreable expected names.
        observation: Provider observation.

    Returns:
        Review reason codes.
    """
    reasons = list(warning_codes)
    if is_unscoreable:
        reasons.append("unscoreable_fixture")
    if observation.get("status") == "error":
        reasons.append(f"provider_error:{_string_field(observation.get('error_code'), 'unknown')}")
    return tuple(sorted(set(reasons)))


def _recommended_actions(review_reasons: tuple[str, ...]) -> tuple[str, ...]:
    """Return bounded human-review action hints.

    Args:
        review_reasons: Review reason codes.

    Returns:
        Suggested action codes.
    """
    actions: list[str] = []
    reason_set = set(review_reasons)
    if "expected_ingredients_missing" in reason_set:
        actions.append("add_human_reviewed_expected_ingredients")
    if "scoreable_expected_ingredients_missing" in reason_set:
        actions.append("verify_or_replace_low_quality_expected_ingredients")
    if "low_confidence_expected_ingredient" in reason_set:
        actions.append("confirm_low_confidence_expected_rows")
    if "non_ingredient_heading_expected" in reason_set:
        actions.append("remove_heading_from_expected_ingredients")
    if "provisional_expected_fixture" in reason_set:
        actions.append("clear_pending_review_after_manual_validation")
    if any(reason.startswith("provider_error:ocr_empty_text") for reason in reason_set):
        actions.append("replace_non_label_or_empty_ocr_fixture")
    if not actions:
        actions.append("manual_quality_review")
    return tuple(actions)


def _priority(review_reasons: tuple[str, ...]) -> int:
    """Return review priority for reason codes.

    Args:
        review_reasons: Review reason codes.

    Returns:
        Integer priority where lower is more urgent.
    """
    reason_set = set(review_reasons)
    if any(reason.startswith("provider_error:") for reason in reason_set):
        return 10
    if "expected_ingredients_missing" in reason_set:
        return 20
    if "scoreable_expected_ingredients_missing" in reason_set:
        return 30
    if "low_confidence_expected_ingredient" in reason_set:
        return 40
    return 50


def _expected_ingredients(expected: object) -> list[dict[str, object]]:
    """Return expected ingredient rows.

    Args:
        expected: Expected object from manifest.

    Returns:
        Ingredient dictionaries.
    """
    if not isinstance(expected, dict):
        return []
    ingredients = expected.get("ingredients")
    if not isinstance(ingredients, list):
        return []
    return [item for item in ingredients if isinstance(item, dict)]


def _expected_names(expected: object) -> list[str]:
    """Return bounded expected ingredient display names.

    Args:
        expected: Expected object from manifest.

    Returns:
        Expected names with count/length bounds.
    """
    names: list[str] = []
    for ingredient in _expected_ingredients(expected):
        for key in ("display_name", "name", "normalized_name"):
            value = ingredient.get(key)
            if isinstance(value, str) and value.strip():
                names.append(value.strip()[:MAX_EXPECTED_NAME_LENGTH])
                break
        if len(names) >= MAX_EXPECTED_NAMES:
            break
    return names


def _render_markdown(
    *,
    queue: list[ReviewQueueItem],
    manifest_path: Path,
    evaluation_path: Path,
    provider: str,
) -> str:
    """Render a bounded Markdown queue report.

    Args:
        queue: Review queue items.
        manifest_path: Source manifest path.
        evaluation_path: Source evaluation path.
        provider: Provider key.

    Returns:
        Markdown report text.
    """
    reason_counts = Counter(reason for item in queue for reason in item.review_reasons)
    lines = [
        "# OCR Ground Truth Review Queue",
        "",
        f"- Manifest: `{manifest_path}`",
        f"- Evaluation: `{evaluation_path}`",
        f"- Provider: `{provider}`",
        f"- Queue items: `{len(queue)}`",
        "- Raw OCR text stored: `False`",
        "- Provider payload stored: `False`",
        "",
        "## Reason Counts",
        "",
        "| Reason | Count |",
        "| --- | ---: |",
    ]
    for reason, count in sorted(reason_counts.items()):
        lines.append(f"| `{reason}` | {count} |")
    lines.extend(
        [
            "",
            "## Review Items",
            "",
            "| Priority | Fixture | Reasons | Actions | Expected count | Provider status | Error |",
            "| ---: | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for item in queue:
        lines.append(
            "| "
            f"{item.priority} | `{item.fixture_id}` | "
            f"`{', '.join(item.review_reasons)}` | "
            f"`{', '.join(item.recommended_actions)}` | "
            f"{item.expected_ingredient_count} | `{item.provider_status}` | "
            f"`{item.provider_error_code or ''}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _string_set(value: object) -> set[str]:
    """Return a set of non-empty strings from a list-like value."""
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str) and item}


def _string_field(value: object, default: str) -> str:
    """Return a bounded string field with a fallback."""
    return value if isinstance(value, str) and value else default


def _optional_string_field(value: object) -> str | None:
    """Return a non-empty string or None."""
    return value if isinstance(value, str) and value else None


def _hash_prefix(value: object) -> str | None:
    """Return a bounded image hash prefix."""
    if not isinstance(value, str) or len(value) < IMAGE_SHA256_PREFIX_LENGTH:
        return None
    return value[:IMAGE_SHA256_PREFIX_LENGTH]


def _list_count(value: object) -> int:
    """Return list length or zero."""
    return len(value) if isinstance(value, list) else 0


def main(argv: list[str] | None = None) -> int:
    """Run the review queue builder CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--evaluation", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    args = parser.parse_args(argv)

    jsonl_path, markdown_path, queue = write_review_queue(
        manifest_path=args.manifest,
        evaluation_path=args.evaluation,
        output_dir=args.output_dir,
        provider=args.provider,
    )
    print(
        json.dumps(
            {
                "queue_count": len(queue),
                "jsonl": str(jsonl_path),
                "markdown": str(markdown_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
