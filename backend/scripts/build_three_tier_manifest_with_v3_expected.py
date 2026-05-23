"""Build a redacted three-tier evaluation manifest with V3 expected snapshots.

The builder maps live fixture ids such as ``naver-live-0001`` to
``naver-chronic-0001.snapshot_v3.json`` and projects only the expected fields
needed by the evaluator. It never copies raw OCR text, provider payloads,
request headers, image bytes, or local snapshot paths into the output JSONL.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent / "Nutrition-backend"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from pydantic import ValidationError  # noqa: E402
from src.models.schemas.supplement_snapshot import (  # noqa: E402
    SupplementParsedSnapshotV3,
)

PENDING_REVIEW_WARNING = "ground_truth_pending_human_review"
COMPOUND_EXPECTED_WARNING = "compound_expected_ingredient_name"
EXPECTED_NAME_SEPARATOR_PATTERN = re.compile(r"\s*(?:,|\uff0c|\u3001)\s*")
MIN_EXPECTED_NAME_PART_CHARS = 2
MAX_EXPECTED_NAME_PART_CHARS = 80
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
        snapshot = SupplementParsedSnapshotV3.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as exc:
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
    snapshot: SupplementParsedSnapshotV3,
) -> dict[str, Any]:
    """Project a validated V3 snapshot into evaluator expected shape.

    Args:
        snapshot_id: V3 snapshot id without extension.
        snapshot: Validated V3 snapshot model.

    Returns:
        Redacted expected object. Evidence spans and local file paths are not included.
    """
    warnings = list(snapshot.warnings)
    ingredients = _project_v3_ingredients(snapshot.ingredients, warnings=warnings)
    is_provisional = PENDING_REVIEW_WARNING in warnings
    return {
        "expected_source": "v3_snapshot",
        "expected_snapshot_id": snapshot_id,
        "expected_snapshot_schema": snapshot.schema_version,
        "verification_status": "provisional" if is_provisional else "verified",
        "ingredients": ingredients,
        "chronic_disease_indications": list(snapshot.chronic_disease_indications),
        "warnings": warnings,
    }


def _project_v3_ingredients(
    ingredients: list[Any],
    *,
    warnings: list[str],
) -> list[dict[str, Any]]:
    """Project V3 ingredients and split bounded compound name rows.

    Args:
        ingredients: Validated V3 snapshot ingredient objects.
        warnings: Mutable expected-level warning list.

    Returns:
        Redacted expected ingredient rows for evaluator input.
    """
    projected: list[dict[str, Any]] = []
    for ingredient in ingredients:
        names = _split_expected_ingredient_name(
            ingredient.display_name,
            amount=ingredient.amount,
            unit=ingredient.unit,
        )
        if len(names) > 1 and COMPOUND_EXPECTED_WARNING not in warnings:
            warnings.append(COMPOUND_EXPECTED_WARNING)
        for name in names:
            projected.append(
                {
                    "display_name": name,
                    "normalized_name": (
                        ingredient.normalized_name
                        if len(names) == 1
                        else _normalize_expected_name(name)
                    ),
                    "amount": ingredient.amount,
                    "unit": ingredient.unit,
                    "source": ingredient.source,
                    "confidence": ingredient.confidence,
                }
            )
    return projected


def _split_expected_ingredient_name(
    value: str,
    *,
    amount: object,
    unit: object,
) -> list[str]:
    """Split a dose-free compound ingredient display name.

    Args:
        value: Ingredient display name.
        amount: Parsed amount from the V3 snapshot.
        unit: Parsed unit from the V3 snapshot.

    Returns:
        One or more bounded display names.
    """
    if amount is not None or unit is not None:
        return [value]
    parts = [
        part.strip()
        for part in EXPECTED_NAME_SEPARATOR_PATTERN.split(value)
        if _looks_like_expected_name_part(part)
    ]
    return parts if len(parts) > 1 else [value]


def _looks_like_expected_name_part(value: str) -> bool:
    """Return whether a split name part is safe to project.

    Args:
        value: Candidate expected-name fragment.

    Returns:
        True for bounded alphabetic ingredient-name fragments.
    """
    stripped = value.strip()
    return MIN_EXPECTED_NAME_PART_CHARS <= len(stripped) <= MAX_EXPECTED_NAME_PART_CHARS and bool(
        re.search(r"[A-Za-z가-힣]", stripped)
    )


def _normalize_expected_name(value: str) -> str:
    """Normalize a projected expected ingredient name.

    Args:
        value: Display name.

    Returns:
        Case-folded whitespace-normalized name.
    """
    return " ".join(value.casefold().split())


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
