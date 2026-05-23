"""Build a redacted three-tier evaluation manifest with V3 expected snapshots.

The builder maps live fixture ids such as ``naver-live-0001`` to
``naver-chronic-0001.snapshot_v3.json`` and projects only the expected fields
needed by the evaluator. It never copies raw OCR text, provider payloads,
request headers, image bytes, or local snapshot paths into the output JSONL.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PENDING_REVIEW_WARNING = "ground_truth_pending_human_review"
V3_SCHEMA_VERSION = "supplement-parsed-snapshot-v3"
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
        "secret",
        "service_key",
    }
)


@dataclass(frozen=True)
class BuildSummary:
    """Build result counts.

    Attributes:
        rows: Number of input manifest rows written to output.
        v3_expected_attached: Rows whose expected field was replaced by a V3 projection.
        ingredient_count: Total projected expected ingredients.
        provisional_expected: Rows still pending human review.
    """

    rows: int
    v3_expected_attached: int
    ingredient_count: int
    provisional_expected: int


def build_manifest_with_v3_expected(
    *,
    manifest_path: Path,
    expected_dir: Path,
    output_path: Path,
) -> BuildSummary:
    """Write a JSONL manifest whose expected fields come from V3 snapshots.

    Args:
        manifest_path: Source JSONL manifest with fixture rows.
        expected_dir: Directory containing ``*.snapshot_v3.json`` files.
        output_path: Destination JSONL path.

    Returns:
        Build summary counts.

    Raises:
        ValueError: If a row contains forbidden raw fields, a fixture id cannot
            map to a V3 snapshot, or a V3 snapshot is invalid.
    """
    rows: list[dict[str, Any]] = []
    attached = 0
    ingredient_count = 0
    provisional_count = 0
    for row in _read_jsonl_rows(manifest_path):
        _reject_raw_fields(row)
        fixture_id = row.get("fixture_id")
        if not isinstance(fixture_id, str) or not fixture_id:
            raise ValueError("manifest row fixture_id must be a non-empty string")
        expected = _load_projected_v3_expected(
            fixture_id=fixture_id,
            expected_dir=expected_dir,
        )
        row["expected"] = expected
        rows.append(row)
        attached += 1
        ingredients = expected.get("ingredients")
        if isinstance(ingredients, list):
            ingredient_count += len(ingredients)
        if expected.get("verification_status") == "provisional":
            provisional_count += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return BuildSummary(
        rows=len(rows),
        v3_expected_attached=attached,
        ingredient_count=ingredient_count,
        provisional_expected=provisional_count,
    )


def _read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    """Read JSONL manifest rows.

    Args:
        path: JSONL path.

    Returns:
        Parsed row objects.

    Raises:
        ValueError: If any non-empty line is not a JSON object.
    """
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError(f"manifest line {line_number} must be a JSON object")
        rows.append(parsed)
    return rows


def _load_projected_v3_expected(
    *,
    fixture_id: str,
    expected_dir: Path,
) -> dict[str, Any]:
    """Load and project one V3 expected snapshot for an evaluation row.

    Args:
        fixture_id: Source manifest fixture id.
        expected_dir: Directory containing V3 expected snapshots.

    Returns:
        Redacted expected object for ``evaluate_ocr_three_tier.py``.

    Raises:
        ValueError: If the mapped V3 snapshot is missing or invalid.
    """
    snapshot_id = _v3_snapshot_id_for_fixture(fixture_id)
    snapshot_path = expected_dir / f"{snapshot_id}.snapshot_v3.json"
    if not snapshot_path.exists():
        raise ValueError(f"missing V3 expected snapshot for fixture_id={fixture_id}")
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot = _validate_v3_snapshot_payload(payload)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid V3 expected snapshot for fixture_id={fixture_id}") from exc
    return _project_v3_expected(snapshot_id=snapshot_id, snapshot=snapshot)


def _v3_snapshot_id_for_fixture(fixture_id: str) -> str:
    """Return the V3 snapshot id for a source manifest fixture id.

    Args:
        fixture_id: Manifest fixture id.

    Returns:
        Snapshot id without file extension.
    """
    if fixture_id.startswith("naver-live-"):
        return fixture_id.replace("naver-live-", "naver-chronic-", 1)
    return fixture_id


def _project_v3_expected(
    *,
    snapshot_id: str,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Project a validated V3 snapshot into evaluator expected shape.

    Args:
        snapshot_id: V3 snapshot id without extension.
        snapshot: Validated V3 snapshot payload.

    Returns:
        Redacted expected object. Evidence spans and local file paths are not included.
    """
    warnings = list(snapshot["warnings"])
    is_provisional = PENDING_REVIEW_WARNING in warnings
    return {
        "expected_source": "v3_snapshot",
        "expected_snapshot_id": snapshot_id,
        "expected_snapshot_schema": snapshot["schema_version"],
        "verification_status": "provisional" if is_provisional else "verified",
        "ingredients": [
            {
                "display_name": ingredient["display_name"],
                "normalized_name": ingredient.get("normalized_name"),
                "amount": ingredient.get("amount"),
                "unit": ingredient.get("unit"),
                "source": ingredient["source"],
                "confidence": ingredient["confidence"],
            }
            for ingredient in snapshot["ingredients"]
        ],
        "chronic_disease_indications": list(snapshot["chronic_disease_indications"]),
        "warnings": warnings,
    }


def _validate_v3_snapshot_payload(value: Any) -> dict[str, Any]:
    """Validate the V3 fields needed for redacted evaluation projection.

    This local validation avoids importing the full application schema in
    export branches whose model dependencies may be split across PRs.

    Args:
        value: Parsed V3 snapshot JSON payload.

    Returns:
        Validated payload.

    Raises:
        ValueError: If required redacted fields are missing or malformed.
    """
    if not isinstance(value, dict):
        raise ValueError("V3 snapshot must be an object")
    _reject_raw_fields(value)
    if value.get("schema_version") != V3_SCHEMA_VERSION:
        raise ValueError("unexpected V3 schema_version")
    warnings = value.get("warnings")
    if not _is_string_list(warnings):
        raise ValueError("V3 warnings must be a string list")
    chronic_conditions = value.get("chronic_disease_indications")
    if not _is_string_list(chronic_conditions):
        raise ValueError("V3 chronic_disease_indications must be a string list")
    source = value.get("source")
    if isinstance(source, dict):
        for raw_flag in (
            "raw_image_stored",
            "raw_ocr_text_stored",
            "raw_provider_payload_stored",
            "raw_model_response_stored",
        ):
            if source.get(raw_flag) is not False:
                raise ValueError(f"V3 source {raw_flag} must be false")
    ingredients = value.get("ingredients")
    if not isinstance(ingredients, list):
        raise ValueError("V3 ingredients must be a list")
    for index, ingredient in enumerate(ingredients):
        if not isinstance(ingredient, dict):
            raise ValueError(f"V3 ingredient[{index}] must be an object")
        _validate_v3_ingredient(ingredient, index)
    return value


def _validate_v3_ingredient(ingredient: dict[str, Any], index: int) -> None:
    """Validate fields needed from one V3 ingredient.

    Args:
        ingredient: Candidate V3 ingredient payload.
        index: Ingredient index for bounded error messages.

    Raises:
        ValueError: If required fields are malformed.
    """
    display_name = ingredient.get("display_name")
    if not isinstance(display_name, str) or not display_name.strip():
        raise ValueError(f"V3 ingredient[{index}].display_name must be non-empty")
    normalized_name = ingredient.get("normalized_name")
    if normalized_name is not None and not isinstance(normalized_name, str):
        raise ValueError(f"V3 ingredient[{index}].normalized_name must be string or null")
    amount = ingredient.get("amount")
    if amount is not None and (isinstance(amount, bool) or not isinstance(amount, int | float)):
        raise ValueError(f"V3 ingredient[{index}].amount must be numeric or null")
    unit = ingredient.get("unit")
    if unit is not None and not isinstance(unit, str):
        raise ValueError(f"V3 ingredient[{index}].unit must be string or null")
    source = ingredient.get("source")
    if not isinstance(source, str) or not source:
        raise ValueError(f"V3 ingredient[{index}].source must be non-empty string")
    confidence = ingredient.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, int | float):
        raise ValueError(f"V3 ingredient[{index}].confidence must be numeric")


def _is_string_list(value: Any) -> bool:
    """Return whether value is a list of strings.

    Args:
        value: Candidate value.

    Returns:
        True if value is a list and every item is a string.
    """
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _reject_raw_fields(value: Any) -> None:
    """Reject raw OCR/provider/image fields recursively.

    Args:
        value: Candidate manifest value.

    Raises:
        ValueError: If a forbidden raw-data key is present.
    """
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key)
            if key_text.lower() in RAW_FORBIDDEN_KEYS:
                raise ValueError(f"manifest contains forbidden raw field: {key_text}")
            _reject_raw_fields(nested)
    elif isinstance(value, list):
        for item in value:
            _reject_raw_fields(item)


def main() -> None:
    """Run the manifest builder from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--expected-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    summary = build_manifest_with_v3_expected(
        manifest_path=args.manifest,
        expected_dir=args.expected_dir,
        output_path=args.output,
    )
    print(
        f"rows={summary.rows} v3_expected_attached={summary.v3_expected_attached} "
        f"ingredient_count={summary.ingredient_count} "
        f"provisional_expected={summary.provisional_expected}"
    )


if __name__ == "__main__":
    main()
