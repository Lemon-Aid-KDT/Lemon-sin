"""Scaffold blank ``SupplementParsedSnapshotV2``/``V3`` ground-truth templates.

Given a prepared live OCR manifest and a category filter, this helper emits one
``<case_id>.snapshot_v2.json`` and one ``<case_id>.snapshot_v3.json`` per
selected fixture into the requested output directory. The templates carry
the schema-required scaffolding (``schema_version``, ``requires_user_confirmation``,
``source`` with ``raw_*_stored=false``, empty ``ingredient_candidates`` etc.) so
that human labellers only need to fill in the ingredient/serving/product fields
from the visible label.

This script does not run OCR, does not read image bytes, and refuses any
``raw_*`` keys in the manifest input.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

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

V2_SCHEMA_VERSION = "supplement-parsed-snapshot-v2"
V3_SCHEMA_VERSION = "supplement-parsed-snapshot-v3"


def main() -> None:
    """Run the scaffold helper from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="Prepared live OCR manifest JSON (object with a cases list).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where <case_id>.snapshot_v{2,3}.json files are written.",
    )
    parser.add_argument(
        "--categories",
        default=None,
        help="Optional comma-separated category_label filter (e.g. 비타민A,비타민B).",
    )
    parser.add_argument(
        "--fixture-ids",
        default=None,
        help="Optional comma-separated fixture_id filter (overrides --categories when set).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing snapshot files. Default is to skip them.",
    )
    args = parser.parse_args()

    summary = scaffold_snapshots(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        categories=_split(args.categories),
        fixture_ids=_split(args.fixture_ids),
        overwrite=args.overwrite,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def scaffold_snapshots(
    *,
    manifest_path: Path,
    output_dir: Path,
    categories: Sequence[str] | None,
    fixture_ids: Sequence[str] | None,
    overwrite: bool,
) -> dict[str, object]:
    """Generate V2 and V3 snapshot templates for matching fixture cases.

    Args:
        manifest_path: Prepared manifest JSON object path.
        output_dir: Output directory for snapshot files.
        categories: Optional category_label allowlist.
        fixture_ids: Optional fixture_id allowlist (takes precedence).
        overwrite: Whether to replace existing snapshot files.

    Returns:
        Redacted summary with counts of written/skipped cases.

    Raises:
        ValueError: If the manifest contains forbidden raw fields or no cases match.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _reject_raw(manifest)
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Manifest must contain a 'cases' list.")

    output_dir.mkdir(parents=True, exist_ok=True)
    selected: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        _reject_raw(case)
        if not _matches(case, categories=categories, fixture_ids=fixture_ids):
            continue
        selected.append(case)

    if not selected:
        raise ValueError("No fixture cases matched the requested filter.")

    written: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    for case in selected:
        fixture_id = case["fixture_id"]
        category = case.get("source_metadata", {}).get("category_label", "unknown")
        for schema_kind in ("v2", "v3"):
            target = output_dir / f"{fixture_id}.snapshot_{schema_kind}.json"
            if target.exists() and not overwrite:
                skipped.append(
                    {"fixture_id": fixture_id, "schema": schema_kind, "path": str(target)}
                )
                continue
            template = _build_template(case=case, schema_kind=schema_kind)
            target.write_text(
                json.dumps(template, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            written.append(
                {
                    "fixture_id": fixture_id,
                    "schema": schema_kind,
                    "category": category,
                    "path": str(target),
                }
            )

    return {
        "selected_count": len(selected),
        "written": written,
        "skipped": skipped,
        "overwrite": overwrite,
        "raw_image_stored": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
    }


def _split(value: str | None) -> list[str] | None:
    """Split a comma-separated filter argument into a trimmed list.

    Args:
        value: Raw CLI argument or None.

    Returns:
        Sequence of non-empty tokens or None.
    """
    if value is None:
        return None
    tokens = [token.strip() for token in value.split(",")]
    return [token for token in tokens if token] or None


def _matches(
    case: dict[str, Any],
    *,
    categories: Sequence[str] | None,
    fixture_ids: Sequence[str] | None,
) -> bool:
    """Return True if the case satisfies the active filter."""
    if fixture_ids:
        return case.get("fixture_id") in set(fixture_ids)
    if categories:
        category = case.get("source_metadata", {}).get("category_label")
        return category in set(categories)
    return True


def _build_template(*, case: dict[str, Any], schema_kind: str) -> dict[str, Any]:
    """Build a blank V2 or V3 ground-truth snapshot template.

    Args:
        case: Manifest case object.
        schema_kind: Either ``v2`` or ``v3``.

    Returns:
        Snapshot template dictionary ready to be hand-filled by a reviewer.
    """
    if schema_kind == "v2":
        return _build_v2_template(case)
    return _build_v3_template(case)


def _common_warnings(case: dict[str, Any]) -> list[str]:
    """Return the warning list shared between V2 and V3 templates."""
    labels = case.get("labels", [])
    category = case.get("source_metadata", {}).get("category_label", "unknown")
    return [
        "ground_truth_pending_human_review",
        f"category:{category}",
        f"labels:{','.join(labels) if labels else 'unspecified'}",
    ]


def _analysis_id(fixture_id: str) -> str:
    """Derive a stable placeholder analysis_id from a fixture id."""
    return f"00000000-0000-4000-8000-{abs(hash(fixture_id)) % 10**12:012d}"


def _build_v2_template(case: dict[str, Any]) -> dict[str, Any]:
    """Return a SupplementParsedSnapshotV2-compatible blank template."""
    return {
        "schema_version": V2_SCHEMA_VERSION,
        "requires_user_confirmation": True,
        "source": {
            "analysis_id": _analysis_id(case["fixture_id"]),
            "ocr_provider": "manual",
            "ocr_confidence": None,
            "layout_available": False,
            "raw_image_stored": False,
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
        },
        "product": {
            "product_name": "TBD",
            "manufacturer": None,
            "barcode_text": None,
            "barcode_format": None,
        },
        "serving": {
            "serving_size_text": "TBD",
            "serving_amount": None,
            "serving_unit": None,
            "daily_servings": None,
            "evidence_refs": [],
        },
        "label_sections": [],
        "ingredient_candidates": [],
        "intake_method": {
            "text": None,
            "structured": {
                "frequency": "unknown",
                "time_of_day": [],
                "with_food": "unknown",
            },
            "evidence_refs": [],
        },
        "precautions": [],
        "functional_claims": [],
        "low_confidence_fields": [],
        "warnings": _common_warnings(case),
    }


def _build_v3_template(case: dict[str, Any]) -> dict[str, Any]:
    """Return a SupplementParsedSnapshotV3-compatible blank template."""
    return {
        "schema_version": V3_SCHEMA_VERSION,
        "requires_user_confirmation": True,
        "source": {
            "analysis_id": _analysis_id(case["fixture_id"]),
            "parser_schema_version": "supplement-parser-output-v2",
            "ocr_provider": "manual",
            "ocr_confidence": None,
            "layout_available": False,
            "raw_image_stored": False,
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "raw_model_response_stored": False,
        },
        "product": {
            "product_name": "TBD",
            "manufacturer": None,
            "barcode_candidates": [],
            "evidence_refs": [],
        },
        "serving": {
            "serving_size_text": "TBD",
            "serving_amount": None,
            "serving_unit": None,
            "daily_servings": None,
            "evidence_refs": [],
        },
        "ingredients": [],
        "label_sections": [],
        "intake_method": {
            "text": None,
            "structured": {
                "frequency": "unknown",
                "time_of_day": [],
                "with_food": "unknown",
            },
            "evidence_refs": [],
        },
        "precautions": [],
        "functional_claims": [],
        "evidence_spans": [],
        "low_confidence_fields": [],
        "warnings": _common_warnings(case),
    }


def _reject_raw(value: object) -> None:
    """Recursively reject raw artifact keys.

    Args:
        value: Candidate value.

    Raises:
        ValueError: If ``value`` contains forbidden raw keys.
    """
    if isinstance(value, dict):
        forbidden = RAW_FORBIDDEN_KEYS.intersection(value.keys())
        if forbidden:
            raise ValueError(f"Input contains forbidden raw field(s): {sorted(forbidden)}")
        for nested in value.values():
            _reject_raw(nested)
    elif isinstance(value, list):
        for item in value:
            _reject_raw(item)


def _iter_categories(case: dict[str, Any]) -> Iterable[str]:
    """Yield the category_label for a case, defaulting to ``unknown``.

    Args:
        case: Manifest case object.

    Yields:
        Category label string.
    """
    yield str(case.get("source_metadata", {}).get("category_label", "unknown"))


if __name__ == "__main__":
    main()
