"""Evaluate supplement OCR baseline fixtures.

This script validates the fixture manifest and expected
``SupplementParsedSnapshotV2``/``SupplementParsedSnapshotV3`` files. It does not
call live OCR providers and it rejects raw image bytes, raw OCR text, raw
provider/model payloads, credentials, and headers in manifests or snapshots.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.models.schemas.supplement_snapshot import (  # noqa: E402
    SupplementParsedSnapshotV2,
    SupplementParsedSnapshotV3,
)

RAW_FORBIDDEN_KEYS = {
    "api_key",
    "authorization",
    "google_cloud_api_key",
    "image_bytes",
    "raw_image",
    "raw_model_response",
    "raw_ocr_text",
    "raw_provider_payload",
    "recommendation",
    "request_body",
    "request_headers",
    "service_key",
    "x_ocr_secret",
}
EXPECTED_SNAPSHOT_KEY = "expected_snapshot_path"
EXPECTED_SNAPSHOT_V3_KEY = "expected_snapshot_v3_path"
ACTUAL_SNAPSHOT_KEY = "actual_snapshot_path"


@dataclass
class BaselineAccumulator:
    """Mutable state for baseline fixture aggregation."""

    fixture_count: int = 0
    image_fixture_count: int = 0
    missing_image_count: int = 0
    ocr_text_fixture_count: int = 0
    missing_ocr_text_count: int = 0
    expected_snapshot_count: int = 0
    expected_snapshot_valid_count: int = 0
    expected_snapshot_v3_count: int = 0
    expected_snapshot_v3_valid_count: int = 0
    evidence_span_count: int = 0
    evidence_ref_count: int = 0
    actual_snapshot_count: int = 0
    field_match_count: int = 0
    field_total_count: int = 0
    confirmation_required_count: int = 0
    raw_image_stored_count: int = 0
    raw_ocr_text_stored_count: int = 0
    raw_provider_payload_stored_count: int = 0
    raw_model_response_stored_count: int = 0


def main() -> None:
    """Run the baseline evaluator from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=False, type=Path)
    args = parser.parse_args()

    summary = evaluate_manifest(args.manifest)
    if args.output_dir is None:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "supplement-ocr-baseline.json"
    markdown_path = args.output_dir / "supplement-ocr-baseline.md"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown(summary), encoding="utf-8")


def evaluate_manifest(manifest_path: Path) -> dict[str, object]:
    """Evaluate a Phase 0 supplement OCR baseline manifest.

    Args:
        manifest_path: JSON manifest path.

    Returns:
        Redacted baseline summary.

    Raises:
        ValueError: If the manifest shape is invalid or contains forbidden raw fields.
    """
    manifest = _read_manifest(manifest_path)
    _reject_raw_fields(manifest)
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Manifest must contain a cases list.")

    root = manifest_path.parent
    accumulator = BaselineAccumulator()
    case_summaries: list[dict[str, object]] = []
    for raw_case in cases:
        if not isinstance(raw_case, dict):
            raise ValueError("Each manifest case must be an object.")
        _reject_raw_fields(raw_case)
        case_summary = _evaluate_case(root, raw_case, accumulator)
        case_summaries.append(case_summary)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest": str(manifest_path),
        "manifest_version": manifest.get("version"),
        "fixture_count": accumulator.fixture_count,
        "image_fixture_count": accumulator.image_fixture_count,
        "missing_image_count": accumulator.missing_image_count,
        "ocr_text_fixture_count": accumulator.ocr_text_fixture_count,
        "missing_ocr_text_count": accumulator.missing_ocr_text_count,
        "expected_snapshot_count": accumulator.expected_snapshot_count,
        "expected_snapshot_valid_count": accumulator.expected_snapshot_valid_count,
        "expected_snapshot_v3_count": accumulator.expected_snapshot_v3_count,
        "expected_snapshot_v3_valid_count": accumulator.expected_snapshot_v3_valid_count,
        "evidence_span_count": accumulator.evidence_span_count,
        "evidence_ref_count": accumulator.evidence_ref_count,
        "evidence_refs_dangling": False,
        "actual_snapshot_count": accumulator.actual_snapshot_count,
        "field_exact_match_rate": _rate(
            accumulator.field_match_count,
            accumulator.field_total_count,
        ),
        "confirmation_required_rate": _rate(
            accumulator.confirmation_required_count,
            accumulator.expected_snapshot_valid_count,
        ),
        "raw_image_stored": accumulator.raw_image_stored_count > 0,
        "raw_ocr_text_stored": accumulator.raw_ocr_text_stored_count > 0,
        "raw_provider_payload_stored": accumulator.raw_provider_payload_stored_count > 0,
        "raw_model_response_stored": accumulator.raw_model_response_stored_count > 0,
        "cases": case_summaries,
        "interpretation": (
            "Baseline metrics validate fixture contracts and storage invariants. "
            "They are not live OCR accuracy or release-readiness claims."
        ),
    }


def _evaluate_case(
    root: Path,
    raw_case: Mapping[str, object],
    accumulator: BaselineAccumulator,
) -> dict[str, object]:
    """Evaluate one manifest case.

    Args:
        root: Manifest root directory.
        raw_case: Manifest case object.
        accumulator: Mutable aggregate state.

    Returns:
        Redacted case summary.

    Raises:
        ValueError: If required case fields are invalid.
    """
    case_id = raw_case.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("Each case requires a non-empty case_id.")
    accumulator.fixture_count += 1

    image_exists = _check_optional_path(
        root=root,
        raw_case=raw_case,
        key="image_path",
    )
    if raw_case.get("image_required") is True:
        accumulator.image_fixture_count += 1
        if not image_exists:
            accumulator.missing_image_count += 1

    ocr_text_exists = _check_optional_path(
        root=root,
        raw_case=raw_case,
        key="ocr_text_path",
    )
    if isinstance(raw_case.get("ocr_text_path"), str):
        accumulator.ocr_text_fixture_count += 1
        if not ocr_text_exists:
            accumulator.missing_ocr_text_count += 1

    expected_snapshot = _load_snapshot(root, raw_case, EXPECTED_SNAPSHOT_KEY)
    accumulator.expected_snapshot_count += 1
    accumulator.expected_snapshot_valid_count += 1
    _add_storage_invariants(expected_snapshot, accumulator)
    if expected_snapshot.requires_user_confirmation:
        accumulator.confirmation_required_count += 1

    expected_snapshot_v3 = _load_snapshot_v3(root, raw_case, EXPECTED_SNAPSHOT_V3_KEY)
    accumulator.expected_snapshot_v3_count += 1
    accumulator.expected_snapshot_v3_valid_count += 1
    _add_storage_invariants_v3(expected_snapshot_v3, accumulator)
    evidence_ref_count = _count_v3_evidence_refs(expected_snapshot_v3)
    accumulator.evidence_span_count += len(expected_snapshot_v3.evidence_spans)
    accumulator.evidence_ref_count += evidence_ref_count

    actual_snapshot_path = raw_case.get(ACTUAL_SNAPSHOT_KEY)
    field_exact_match_rate = None
    if isinstance(actual_snapshot_path, str) and actual_snapshot_path.strip():
        actual_snapshot = _load_snapshot(root, raw_case, ACTUAL_SNAPSHOT_KEY)
        accumulator.actual_snapshot_count += 1
        matches, total = _compare_snapshot_fields(expected_snapshot, actual_snapshot)
        accumulator.field_match_count += matches
        accumulator.field_total_count += total
        field_exact_match_rate = _rate(matches, total)

    return {
        "case_id": case_id,
        "image_exists": image_exists,
        "ocr_text_exists": ocr_text_exists,
        "expected_snapshot_valid": True,
        "expected_snapshot_v3_valid": True,
        "evidence_span_count": len(expected_snapshot_v3.evidence_spans),
        "evidence_ref_count": evidence_ref_count,
        "actual_snapshot_present": isinstance(actual_snapshot_path, str)
        and bool(actual_snapshot_path.strip()),
        "field_exact_match_rate": field_exact_match_rate,
        "requires_user_confirmation": expected_snapshot.requires_user_confirmation,
        "raw_image_stored": expected_snapshot.source.raw_image_stored,
        "raw_ocr_text_stored": expected_snapshot.source.raw_ocr_text_stored,
        "raw_provider_payload_stored": expected_snapshot.source.raw_provider_payload_stored,
        "raw_model_response_stored": expected_snapshot_v3.source.raw_model_response_stored,
    }


def _read_manifest(manifest_path: Path) -> dict[str, object]:
    """Read a JSON manifest object.

    Args:
        manifest_path: Manifest path.

    Returns:
        Manifest object.

    Raises:
        ValueError: If the file does not contain a JSON object.
    """
    parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Manifest must be a JSON object.")
    return parsed


def _check_optional_path(
    *,
    root: Path,
    raw_case: Mapping[str, object],
    key: str,
) -> bool:
    """Check a manifest path without reading raw artifact content.

    Args:
        root: Manifest root directory.
        raw_case: Manifest case object.
        key: Path key to inspect.
    Returns:
        True if a path is present and exists.

    Raises:
        ValueError: If a present path value is not a string.
    """
    value = raw_case.get(key)
    if value is None:
        return False
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string or null.")
    if not value.strip():
        return False
    return (root / value).exists()


def _load_snapshot(
    root: Path,
    raw_case: Mapping[str, object],
    key: str,
) -> SupplementParsedSnapshotV2:
    """Load and validate a versioned parsed supplement snapshot.

    Args:
        root: Manifest root directory.
        raw_case: Manifest case object.
        key: Snapshot path key.

    Returns:
        Validated snapshot.

    Raises:
        ValueError: If the path is absent, missing, or contains raw fields.
    """
    value = raw_case.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required.")
    path = root / value
    if not path.exists():
        raise ValueError(f"{key} does not exist: {value}")
    parsed = json.loads(path.read_text(encoding="utf-8"))
    _reject_raw_fields(parsed)
    return SupplementParsedSnapshotV2.model_validate(parsed)


def _load_snapshot_v3(
    root: Path,
    raw_case: Mapping[str, object],
    key: str,
) -> SupplementParsedSnapshotV3:
    """Load and validate a V3 parsed supplement snapshot.

    Args:
        root: Manifest root directory.
        raw_case: Manifest case object.
        key: V3 snapshot path key.

    Returns:
        Validated V3 snapshot.

    Raises:
        ValueError: If the path is absent, missing, or contains raw fields.
    """
    value = raw_case.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required.")
    path = root / value
    if not path.exists():
        raise ValueError(f"{key} does not exist: {value}")
    parsed = json.loads(path.read_text(encoding="utf-8"))
    _reject_raw_fields(parsed)
    return SupplementParsedSnapshotV3.model_validate(parsed)


def _add_storage_invariants(
    snapshot: SupplementParsedSnapshotV2,
    accumulator: BaselineAccumulator,
) -> None:
    """Accumulate raw storage invariant flags.

    Args:
        snapshot: Validated expected snapshot.
        accumulator: Mutable aggregate state.
    """
    accumulator.raw_image_stored_count += int(snapshot.source.raw_image_stored)
    accumulator.raw_ocr_text_stored_count += int(snapshot.source.raw_ocr_text_stored)
    accumulator.raw_provider_payload_stored_count += int(
        snapshot.source.raw_provider_payload_stored
    )


def _add_storage_invariants_v3(
    snapshot: SupplementParsedSnapshotV3,
    accumulator: BaselineAccumulator,
) -> None:
    """Accumulate V3 raw storage invariant flags.

    Args:
        snapshot: Validated V3 snapshot.
        accumulator: Mutable aggregate state.
    """
    accumulator.raw_image_stored_count += int(snapshot.source.raw_image_stored)
    accumulator.raw_ocr_text_stored_count += int(snapshot.source.raw_ocr_text_stored)
    accumulator.raw_provider_payload_stored_count += int(
        snapshot.source.raw_provider_payload_stored
    )
    accumulator.raw_model_response_stored_count += int(snapshot.source.raw_model_response_stored)


def _count_v3_evidence_refs(snapshot: SupplementParsedSnapshotV3) -> int:
    """Count V3 evidence references.

    Args:
        snapshot: Validated V3 snapshot.

    Returns:
        Evidence reference count.
    """
    count = 0
    count += len(snapshot.product.evidence_refs)
    count += len(snapshot.serving.evidence_refs)
    count += len(snapshot.intake_method.evidence_refs)
    for barcode in snapshot.product.barcode_candidates:
        count += len(barcode.evidence_refs)
    for ingredient in snapshot.ingredients:
        count += len(ingredient.evidence_refs)
    for section in snapshot.label_sections:
        count += len(section.evidence_refs)
    for precaution in snapshot.precautions:
        count += len(precaution.evidence_refs)
    for claim in snapshot.functional_claims:
        count += len(claim.evidence_refs)
    return count


def _compare_snapshot_fields(
    expected: SupplementParsedSnapshotV2,
    actual: SupplementParsedSnapshotV2,
) -> tuple[int, int]:
    """Compare snapshot fields using exact JSON-compatible values.

    Args:
        expected: Expected snapshot.
        actual: Actual snapshot.

    Returns:
        Matched field count and total comparable field count.
    """
    expected_fields = _flatten(expected.model_dump(mode="json"))
    actual_fields = _flatten(actual.model_dump(mode="json"))
    matches = 0
    for path, expected_value in expected_fields.items():
        if actual_fields.get(path) == expected_value:
            matches += 1
    return matches, len(expected_fields)


def _flatten(value: object, prefix: str = "") -> dict[str, object]:
    """Flatten a JSON-compatible structure into field paths.

    Args:
        value: JSON-compatible value.
        prefix: Current field path prefix.

    Returns:
        Mapping from field paths to scalar values.
    """
    if isinstance(value, dict):
        flattened: dict[str, object] = {}
        for key, nested_value in sorted(value.items()):
            nested_prefix = f"{prefix}.{key}" if prefix else key
            flattened.update(_flatten(nested_value, nested_prefix))
        return flattened
    if isinstance(value, list):
        flattened = {}
        for index, nested_value in enumerate(value):
            flattened.update(_flatten(nested_value, f"{prefix}[{index}]"))
        return flattened
    return {prefix: value}


def _reject_raw_fields(value: object) -> None:
    """Reject forbidden raw data and secret keys recursively.

    Args:
        value: Candidate manifest or snapshot value.

    Raises:
        ValueError: If a forbidden key is found.
    """
    if isinstance(value, dict):
        normalized_keys = {str(key).casefold(): key for key in value}
        forbidden = RAW_FORBIDDEN_KEYS.intersection(normalized_keys.keys())
        if forbidden:
            display_keys = [str(normalized_keys[key]) for key in sorted(forbidden)]
            raise ValueError(f"Forbidden raw or secret field(s): {display_keys}")
        for nested_value in value.values():
            _reject_raw_fields(nested_value)
    elif isinstance(value, list):
        for item in value:
            _reject_raw_fields(item)


def _rate(numerator: int, denominator: int) -> float | None:
    """Return a rounded rate or None for an empty denominator.

    Args:
        numerator: Numerator.
        denominator: Denominator.

    Returns:
        Rounded rate or None.
    """
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _render_markdown(summary: dict[str, object]) -> str:
    """Render a compact redacted Markdown summary.

    Args:
        summary: Evaluation summary.

    Returns:
        Markdown report.
    """
    lines = [
        "# Supplement OCR Baseline Evaluation",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- manifest: `{summary['manifest']}`",
        f"- fixture_count: `{summary['fixture_count']}`",
        f"- expected_snapshot_valid_count: `{summary['expected_snapshot_valid_count']}`",
        f"- expected_snapshot_v3_valid_count: `{summary['expected_snapshot_v3_valid_count']}`",
        f"- evidence_refs_dangling: `{summary['evidence_refs_dangling']}`",
        f"- field_exact_match_rate: `{summary['field_exact_match_rate']}`",
        f"- confirmation_required_rate: `{summary['confirmation_required_rate']}`",
        f"- raw_image_stored: `{summary['raw_image_stored']}`",
        f"- raw_ocr_text_stored: `{summary['raw_ocr_text_stored']}`",
        f"- raw_provider_payload_stored: `{summary['raw_provider_payload_stored']}`",
        f"- raw_model_response_stored: `{summary['raw_model_response_stored']}`",
        f"- interpretation: {summary['interpretation']}",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
