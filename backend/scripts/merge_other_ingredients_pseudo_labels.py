"""Merge experimental other-ingredients pseudo-labels into a section export.

This script keeps pseudo-label provenance explicit. The resulting export is
suitable only for experimental detector training unless a separate human review
promotes the boxes. The redacted summary records counts and policy flags, not
raw OCR text or private paths.

References:
    https://docs.ultralytics.com/datasets/detect/
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.learning.retraining import (  # noqa: E402
    SUPPLEMENT_SECTION_CLASS_NAMES,
    SUPPLEMENT_SECTION_YOLO_EXPORT_SCHEMA_VERSION,
)

SUMMARY_SCHEMA_VERSION = "other-ingredients-pseudo-label-merge-summary-v1"
TARGET_CLASS = "other_ingredients"
SOURCE_DOC_URLS = ("https://docs.ultralytics.com/datasets/detect/",)


class PseudoLabelMergeError(ValueError):
    """Raised when pseudo-label merge input is malformed or unsafe."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument list for tests.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--proposals", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--min-proposals", type=int, default=18)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run pseudo-label merge.

    Args:
        argv: Optional argument list for tests.
    """
    args = parse_args(argv)
    try:
        output_export, summary = merge_pseudo_labels(
            export_path=args.export,
            proposals_path=args.proposals,
            min_proposals=args.min_proposals,
        )
        _write_json(args.summary, summary)
        if args.apply:
            _write_json(args.output, output_export)
        print(json.dumps(_cli_summary(summary), ensure_ascii=False, sort_keys=True))
    except (PseudoLabelMergeError, OSError, json.JSONDecodeError) as exc:
        failure = {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "absolute_paths_stored": False,
        }
        _write_json(args.summary, failure)
        print(json.dumps(_cli_summary(failure), ensure_ascii=False, sort_keys=True))
        raise SystemExit(1) from None


def merge_pseudo_labels(
    *,
    export_path: Path,
    proposals_path: Path,
    min_proposals: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Merge pseudo-label proposals into a copy of the source export.

    Args:
        export_path: Human-reviewed source export.
        proposals_path: Machine proposal artifact.
        min_proposals: Minimum proposals required to merge.

    Returns:
        Tuple of merged export and redacted summary.

    Raises:
        PseudoLabelMergeError: If input is invalid or proposal count is too low.
    """
    if min_proposals < 0:
        raise PseudoLabelMergeError("min_proposals must be non-negative.")
    export = _load_json_object(export_path, "source export")
    proposals_artifact = _load_json_object(proposals_path, "proposal artifact")
    _validate_export(export)
    proposals = _proposal_rows(proposals_artifact)
    if len(proposals) < min_proposals:
        raise PseudoLabelMergeError("not enough proposals for pseudo-label merge.")

    items_by_source_ref = {_string_field(item, "source_ref"): item for item in export["items"]}
    merged_count = 0
    skipped_counts: Counter[str] = Counter()
    for proposal in proposals:
        source_ref = _string_field(proposal, "source_ref")
        item = items_by_source_ref.get(source_ref)
        if item is None:
            skipped_counts["source_ref_missing"] += 1
            continue
        labels = item.get("labels")
        if not isinstance(labels, list):
            raise PseudoLabelMergeError("source export item labels must be a list.")
        if any(isinstance(label, dict) and label.get("label") == TARGET_CLASS for label in labels):
            skipped_counts["already_has_target_class"] += 1
            continue
        label = _proposal_label(proposal)
        label.update(
            {
                "annotation_source": "machine_proposed",
                "human_reviewed": False,
                "promotion_allowed": False,
                "pseudo_label_schema_version": proposals_artifact.get("schema_version"),
                "match_bucket": proposal.get("match_bucket"),
            }
        )
        labels.append(label)
        merged_count += 1

    output_export = dict(export)
    output_export["items"] = export["items"]
    output_export["item_count"] = len(export["items"])
    output_export["pseudo_label_policy"] = {
        "created_at": datetime.now(UTC).isoformat(),
        "target_class": TARGET_CLASS,
        "machine_proposed": True,
        "human_reviewed": False,
        "promotion_allowed": False,
        "source_proposal_schema_version": proposals_artifact.get("schema_version"),
    }
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "ready_for_panelizer" if merged_count >= min_proposals else "insufficient_merged_labels",
        "target_class": TARGET_CLASS,
        "proposal_count": len(proposals),
        "merged_label_count": merged_count,
        "skipped_counts": dict(skipped_counts),
        "machine_proposed": True,
        "human_reviewed": False,
        "promotion_allowed": False,
        "source_doc_urls": list(SOURCE_DOC_URLS),
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
    }
    _assert_redacted(summary)
    return output_export, summary


def _proposal_label(proposal: dict[str, Any]) -> dict[str, Any]:
    """Return validated label geometry from one proposal."""
    label = proposal.get("label")
    if not isinstance(label, dict):
        raise PseudoLabelMergeError("proposal label must be an object.")
    class_id = label.get("class_id")
    if class_id != SUPPLEMENT_SECTION_CLASS_NAMES.index(TARGET_CLASS):
        raise PseudoLabelMergeError("proposal class_id does not match target class.")
    return {
        "class_id": class_id,
        "label": TARGET_CLASS,
        "x_center": _coordinate(label, "x_center"),
        "y_center": _coordinate(label, "y_center"),
        "width": _coordinate(label, "width"),
        "height": _coordinate(label, "height"),
    }


def _proposal_rows(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """Return proposal rows after validating policy flags."""
    proposals = artifact.get("proposals")
    if not isinstance(proposals, list):
        raise PseudoLabelMergeError("proposal artifact requires proposals list.")
    summary = artifact.get("summary")
    if not isinstance(summary, dict):
        raise PseudoLabelMergeError("proposal artifact requires summary.")
    if summary.get("promotion_allowed") is not False or summary.get("human_reviewed") is not False:
        raise PseudoLabelMergeError("proposal artifact must remain experimental and unreviewed.")
    return [proposal for proposal in proposals if isinstance(proposal, dict)]


def _load_json_object(path: Path, description: str) -> dict[str, Any]:
    """Load a JSON object from disk."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PseudoLabelMergeError(f"{description} must be a JSON object.")
    return value


def _validate_export(export: dict[str, Any]) -> None:
    """Validate source export schema and class list."""
    if export.get("schema_version") != SUPPLEMENT_SECTION_YOLO_EXPORT_SCHEMA_VERSION:
        raise PseudoLabelMergeError("unsupported source export schema.")
    if export.get("class_names") != list(SUPPLEMENT_SECTION_CLASS_NAMES):
        raise PseudoLabelMergeError("source export class names do not match.")
    items = export.get("items")
    if not isinstance(items, list) or export.get("item_count") != len(items):
        raise PseudoLabelMergeError("source export item_count mismatch.")


def _coordinate(label: dict[str, Any], key: str) -> float:
    """Return one bounded normalized coordinate."""
    value = label.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PseudoLabelMergeError("label coordinate must be numeric.")
    coordinate = float(value)
    if not 0 <= coordinate <= 1:
        raise PseudoLabelMergeError("label coordinate must be normalized.")
    return round(coordinate, 6)


def _string_field(row: dict[str, Any], key: str) -> str:
    """Return one required string field."""
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PseudoLabelMergeError(f"{key} must be a non-empty string.")
    return value


def _write_json(path: Path, payload: object) -> None:
    """Write JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _cli_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Return compact CLI output."""
    return {
        "status": summary.get("status"),
        "proposal_count": summary.get("proposal_count"),
        "merged_label_count": summary.get("merged_label_count"),
        "skipped_counts": summary.get("skipped_counts"),
    }


def _assert_redacted(payload: object) -> None:
    """Reject unsafe strings in summaries."""
    dumped = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    forbidden_markers = (
        "/Users/",
        "/Volumes/",
        "/private/",
        "\\Users\\",
        "file://",
        "matched_keyword_lines",
        '"raw_ocr_text":',
        '"provider_payload":',
        '"provider_raw_payload":',
    )
    if any(marker in dumped for marker in forbidden_markers):
        raise PseudoLabelMergeError("merge summary contains unsafe content.")


if __name__ == "__main__":
    main()
