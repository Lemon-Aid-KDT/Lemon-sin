"""Merge supplement section line boxes into trainable panel boxes.

This operator-side script consumes the reviewed supplement section YOLO export
produced by ``promote_supplement_yolo_annotation_template.py`` and writes a new
export artifact with nearby boxes of the same class merged into larger section
panels. The goal is to avoid training a detector on tiny token/line boxes when
the downstream structured extractor needs section-level regions.

The CLI summary and needs-review artifact are redacted: they contain counts,
class names, normalized geometry buckets, and source-ref hashes only. They never
write raw OCR text, provider payloads, absolute paths, or private source refs.

References:
    https://docs.ultralytics.com/datasets/detect/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
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

SUMMARY_SCHEMA_VERSION = "supplement-section-panel-merge-summary-v1"
NEEDS_REVIEW_SCHEMA_VERSION = "supplement-section-panel-needs-review-v1"
ANNOTATION_TARGETS_SCHEMA_VERSION = "supplement-section-panel-annotation-targets-v1"
DEFAULT_MAX_Y_GAP = 0.035
DEFAULT_PANEL_PADDING = 0.01
DEFAULT_MIN_PANEL_HEIGHT = 0.015
DEFAULT_MIN_PANEL_AREA = 0.0025
DEFAULT_TINY_HEIGHT = 0.01
DEFAULT_TINY_AREA = 0.001
DEFAULT_RARE_MIN_TRAIN_PANELS = 30
RARE_CLASS_NAMES = (
    "other_ingredients",
    "allergen_warning",
    "intake_method",
    "precautions",
)
SOURCE_DOC_URLS = ("https://docs.ultralytics.com/datasets/detect/",)


class PanelMergeError(ValueError):
    """Raised when panelization input or parameters are unsafe."""


@dataclass(frozen=True)
class Box:
    """Normalized box in corner format."""

    class_id: int
    label: str
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        """Return normalized box width."""
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        """Return normalized box height."""
        return max(0.0, self.y1 - self.y0)

    @property
    def area(self) -> float:
        """Return normalized box area."""
        return self.width * self.height

    def padded(self, padding: float) -> Box:
        """Return a clipped padded copy.

        Args:
            padding: Normalized padding added on every side.

        Returns:
            Padded normalized box.
        """
        return Box(
            class_id=self.class_id,
            label=self.label,
            x0=max(0.0, self.x0 - padding),
            y0=max(0.0, self.y0 - padding),
            x1=min(1.0, self.x1 + padding),
            y1=min(1.0, self.y1 + padding),
        )

    def to_yolo_label(self) -> dict[str, Any]:
        """Return a YOLO normalized label mapping.

        Returns:
            Label dictionary compatible with the existing materializer.
        """
        return {
            "class_id": self.class_id,
            "label": self.label,
            "x_center": round((self.x0 + self.x1) / 2, 6),
            "y_center": round((self.y0 + self.y1) / 2, 6),
            "width": round(self.width, 6),
            "height": round(self.height, 6),
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument list for tests.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--needs-review", required=True, type=Path)
    parser.add_argument("--annotation-targets", type=Path, default=None)
    parser.add_argument("--max-y-gap", type=float, default=DEFAULT_MAX_Y_GAP)
    parser.add_argument("--panel-padding", type=float, default=DEFAULT_PANEL_PADDING)
    parser.add_argument("--min-panel-height", type=float, default=DEFAULT_MIN_PANEL_HEIGHT)
    parser.add_argument("--min-panel-area", type=float, default=DEFAULT_MIN_PANEL_AREA)
    parser.add_argument("--tiny-height", type=float, default=DEFAULT_TINY_HEIGHT)
    parser.add_argument("--tiny-area", type=float, default=DEFAULT_TINY_AREA)
    parser.add_argument(
        "--rare-min-train-panels",
        type=int,
        default=DEFAULT_RARE_MIN_TRAIN_PANELS,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write panelized export and needs-review artifacts.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the panel merge CLI.

    Args:
        argv: Optional argument list for tests.
    """
    args = parse_args(argv)
    try:
        export, needs_review, summary = merge_section_panel_boxes(
            export_path=args.export,
            max_y_gap=args.max_y_gap,
            panel_padding=args.panel_padding,
            min_panel_height=args.min_panel_height,
            min_panel_area=args.min_panel_area,
            tiny_height=args.tiny_height,
            tiny_area=args.tiny_area,
            rare_min_train_panels=args.rare_min_train_panels,
        )
        _write_json(args.summary, summary)
        if args.apply:
            _write_json(args.output, export)
            _write_jsonl(args.needs_review, needs_review)
            if args.annotation_targets is not None:
                _write_json(
                    args.annotation_targets,
                    _annotation_targets(
                        panel_export=export,
                        summary=summary,
                        rare_min_train_panels=args.rare_min_train_panels,
                    ),
                )
        print(json.dumps(_cli_summary(summary), ensure_ascii=False, sort_keys=True))
    except (OSError, json.JSONDecodeError, PanelMergeError, ValueError) as exc:
        failure = _failure_summary(error=exc, export_name=args.export.name)
        _write_json(args.summary, failure)
        print(json.dumps(_cli_summary(failure), ensure_ascii=False, sort_keys=True))
        raise SystemExit(1) from None


def merge_section_panel_boxes(
    *,
    export_path: Path,
    max_y_gap: float = DEFAULT_MAX_Y_GAP,
    panel_padding: float = DEFAULT_PANEL_PADDING,
    min_panel_height: float = DEFAULT_MIN_PANEL_HEIGHT,
    min_panel_area: float = DEFAULT_MIN_PANEL_AREA,
    tiny_height: float = DEFAULT_TINY_HEIGHT,
    tiny_area: float = DEFAULT_TINY_AREA,
    rare_min_train_panels: int = DEFAULT_RARE_MIN_TRAIN_PANELS,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Merge same-class line boxes into larger section panels.

    Args:
        export_path: Source supplement-section YOLO export JSON.
        max_y_gap: Maximum normalized vertical gap for merging adjacent boxes.
        panel_padding: Normalized panel padding added after union.
        min_panel_height: Minimum panel height required for training export.
        min_panel_area: Minimum panel area required for training export.
        tiny_height: Diagnostic raw-box tiny height threshold.
        tiny_area: Diagnostic raw-box tiny area threshold.
        rare_min_train_panels: Minimum train panel count for rare classes.

    Returns:
        Tuple of panelized export, redacted needs-review rows, and summary.

    Raises:
        PanelMergeError: If the source export is malformed or unsafe.
        ValueError: If merge thresholds are invalid.
    """
    _validate_thresholds(
        max_y_gap=max_y_gap,
        panel_padding=panel_padding,
        min_panel_height=min_panel_height,
        min_panel_area=min_panel_area,
        tiny_height=tiny_height,
        tiny_area=tiny_area,
        rare_min_train_panels=rare_min_train_panels,
    )
    source_export = _read_export(export_path)
    items = _export_items(source_export)

    panel_items: list[dict[str, Any]] = []
    needs_review: list[dict[str, Any]] = []
    original_class_counts: Counter[str] = Counter()
    panel_class_counts: Counter[str] = Counter()
    panel_split_class_counts: dict[str, Counter[str]] = defaultdict(Counter)
    split_counts: Counter[str] = Counter()
    original_tiny_height_count = 0
    original_tiny_area_count = 0
    skipped_items: Counter[str] = Counter()

    for item in items:
        source_ref = _source_ref(item)
        split = _split(item)
        boxes = [_label_to_box(label) for label in _labels(item)]
        for box in boxes:
            original_class_counts[box.label] += 1
            if box.height < tiny_height:
                original_tiny_height_count += 1
            if box.area < tiny_area:
                original_tiny_area_count += 1
        panels = _merge_item_panels(
            boxes,
            max_y_gap=max_y_gap,
            panel_padding=panel_padding,
        )
        trainable_labels: list[dict[str, Any]] = []
        for panel in panels:
            if panel.height < min_panel_height or panel.area < min_panel_area:
                needs_review.append(
                    _needs_review_row(
                        source_ref=source_ref,
                        split=split,
                        panel=panel,
                        reason="panel_below_min_geometry",
                    )
                )
                continue
            trainable_labels.append(panel.to_yolo_label())
            panel_class_counts[panel.label] += 1
            panel_split_class_counts[split][panel.label] += 1
        if not trainable_labels:
            skipped_items["no_trainable_panels"] += 1
            continue
        split_counts[split] += 1
        panel_items.append(
            {
                "source_ref": source_ref,
                "split": split,
                "labels": trainable_labels,
            }
        )

    output_export = {
        "schema_version": SUPPLEMENT_SECTION_YOLO_EXPORT_SCHEMA_VERSION,
        "class_names": list(SUPPLEMENT_SECTION_CLASS_NAMES),
        "item_count": len(panel_items),
        "split_counts": {
            "train": split_counts.get("train", 0),
            "val": split_counts.get("val", 0),
            "test": split_counts.get("test", 0),
            "holdout": 0,
        },
        "panelization": {
            "source_export_name": export_path.name,
            "created_at": datetime.now(UTC).isoformat(),
            "max_y_gap": max_y_gap,
            "panel_padding": panel_padding,
            "min_panel_height": min_panel_height,
            "min_panel_area": min_panel_area,
        },
        "items": panel_items,
    }
    summary = _summary(
        export_path=export_path,
        source_items=items,
        panel_items=panel_items,
        needs_review=needs_review,
        original_class_counts=original_class_counts,
        panel_class_counts=panel_class_counts,
        panel_split_class_counts=panel_split_class_counts,
        original_tiny_height_count=original_tiny_height_count,
        original_tiny_area_count=original_tiny_area_count,
        skipped_items=skipped_items,
        rare_min_train_panels=rare_min_train_panels,
        thresholds={
            "max_y_gap": max_y_gap,
            "panel_padding": panel_padding,
            "min_panel_height": min_panel_height,
            "min_panel_area": min_panel_area,
            "tiny_height": tiny_height,
            "tiny_area": tiny_area,
        },
    )
    _assert_redacted(summary)
    _assert_redacted(needs_review)
    return output_export, needs_review, summary


def _validate_thresholds(
    *,
    max_y_gap: float,
    panel_padding: float,
    min_panel_height: float,
    min_panel_area: float,
    tiny_height: float,
    tiny_area: float,
    rare_min_train_panels: int,
) -> None:
    """Validate CLI threshold arguments."""
    for name, value in {
        "max_y_gap": max_y_gap,
        "panel_padding": panel_padding,
        "min_panel_height": min_panel_height,
        "min_panel_area": min_panel_area,
        "tiny_height": tiny_height,
        "tiny_area": tiny_area,
    }.items():
        if not math.isfinite(value) or value < 0 or value > 1:
            raise ValueError(f"{name} must be in the normalized 0..1 range.")
    if rare_min_train_panels < 0:
        raise ValueError("rare_min_train_panels must be non-negative.")


def _read_export(export_path: Path) -> dict[str, Any]:
    """Read and validate the source export header."""
    value = json.loads(export_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PanelMergeError("YOLO export must be a JSON object.")
    if value.get("schema_version") != SUPPLEMENT_SECTION_YOLO_EXPORT_SCHEMA_VERSION:
        raise PanelMergeError("Unsupported supplement section YOLO export schema.")
    if value.get("class_names") != list(SUPPLEMENT_SECTION_CLASS_NAMES):
        raise PanelMergeError("Export class names do not match the supplement section contract.")
    return value


def _export_items(export: dict[str, Any]) -> list[dict[str, Any]]:
    """Return source export items after shape validation."""
    items = export.get("items")
    if not isinstance(items, list) or not items:
        raise PanelMergeError("YOLO export requires at least one item.")
    if export.get("item_count") != len(items):
        raise PanelMergeError("YOLO export item_count does not match items.")
    if not all(isinstance(item, dict) for item in items):
        raise PanelMergeError("YOLO export items must be objects.")
    return items


def _source_ref(item: dict[str, Any]) -> str:
    """Return one private source ref."""
    source_ref = item.get("source_ref")
    if not isinstance(source_ref, str) or not source_ref.strip():
        raise PanelMergeError("Export item requires source_ref.")
    if source_ref.startswith("/") or "://" in source_ref or ".." in source_ref:
        raise PanelMergeError("Export source_ref must stay a private token.")
    return source_ref


def _split(item: dict[str, Any]) -> str:
    """Return one supported split."""
    split = item.get("split")
    if split not in {"train", "val", "test"}:
        raise PanelMergeError("Export item split must be train, val, or test.")
    return str(split)


def _labels(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Return label list for one item."""
    labels = item.get("labels")
    if not isinstance(labels, list) or not labels:
        raise PanelMergeError("Export item requires at least one label.")
    if not all(isinstance(label, dict) for label in labels):
        raise PanelMergeError("Export item labels must be objects.")
    return labels


def _label_to_box(label: dict[str, Any]) -> Box:
    """Convert a normalized YOLO label to corner coordinates."""
    class_id = label.get("class_id")
    if isinstance(class_id, bool) or not isinstance(class_id, int):
        raise PanelMergeError("Label class_id must be an integer.")
    if not 0 <= class_id < len(SUPPLEMENT_SECTION_CLASS_NAMES):
        raise PanelMergeError("Label class_id is outside supplement section names.")
    label_name = label.get("label") or SUPPLEMENT_SECTION_CLASS_NAMES[class_id]
    if label_name != SUPPLEMENT_SECTION_CLASS_NAMES[class_id]:
        raise PanelMergeError("Label class_id and label name do not match.")
    x_center = _coordinate(label, "x_center")
    y_center = _coordinate(label, "y_center")
    width = _coordinate(label, "width")
    height = _coordinate(label, "height")
    x0 = max(0.0, x_center - width / 2)
    y0 = max(0.0, y_center - height / 2)
    x1 = min(1.0, x_center + width / 2)
    y1 = min(1.0, y_center + height / 2)
    if x1 <= x0 or y1 <= y0:
        raise PanelMergeError("Label box has non-positive geometry.")
    return Box(
        class_id=class_id,
        label=SUPPLEMENT_SECTION_CLASS_NAMES[class_id],
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
    )


def _coordinate(label: dict[str, Any], key: str) -> float:
    """Return one normalized coordinate value."""
    value = label.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PanelMergeError("Label coordinate must be numeric.")
    coordinate = float(value)
    if not math.isfinite(coordinate) or not 0 <= coordinate <= 1:
        raise PanelMergeError("Label coordinate must be normalized.")
    return coordinate


def _merge_item_panels(
    boxes: Iterable[Box],
    *,
    max_y_gap: float,
    panel_padding: float,
) -> list[Box]:
    """Merge boxes per class into vertically adjacent panels."""
    panels: list[Box] = []
    boxes_by_class: dict[int, list[Box]] = defaultdict(list)
    for box in boxes:
        boxes_by_class[box.class_id].append(box)

    for class_id, class_boxes in boxes_by_class.items():
        label = SUPPLEMENT_SECTION_CLASS_NAMES[class_id]
        sorted_boxes = sorted(class_boxes, key=lambda box: (box.y0, box.x0))
        current = sorted_boxes[0]
        for candidate in sorted_boxes[1:]:
            if _should_merge(current, candidate, max_y_gap=max_y_gap):
                current = _union(current, candidate)
                continue
            panels.append(current.padded(panel_padding))
            current = candidate
        panels.append(current.padded(panel_padding))
        for panel in panels:
            if panel.class_id == class_id and panel.label != label:
                raise PanelMergeError("Merged panel label mismatch.")
    return sorted(panels, key=lambda box: (box.y0, box.x0, box.class_id))


def _should_merge(first: Box, second: Box, *, max_y_gap: float) -> bool:
    """Return whether two same-class boxes belong to one section panel."""
    if first.class_id != second.class_id:
        return False
    vertical_gap = max(0.0, second.y0 - first.y1)
    vertical_overlap = min(first.y1, second.y1) - max(first.y0, second.y0)
    return vertical_gap <= max_y_gap or vertical_overlap >= 0


def _union(first: Box, second: Box) -> Box:
    """Return the normalized union of two same-class boxes."""
    return Box(
        class_id=first.class_id,
        label=first.label,
        x0=min(first.x0, second.x0),
        y0=min(first.y0, second.y0),
        x1=max(first.x1, second.x1),
        y1=max(first.y1, second.y1),
    )


def _needs_review_row(
    *,
    source_ref: str,
    split: str,
    panel: Box,
    reason: str,
) -> dict[str, Any]:
    """Build a redacted needs-review row."""
    return {
        "schema_version": NEEDS_REVIEW_SCHEMA_VERSION,
        "source_ref_hash": _source_ref_hash(source_ref),
        "split": split,
        "class_name": panel.label,
        "reason": reason,
        "height": round(panel.height, 6),
        "area": round(panel.area, 6),
    }


def _summary(
    *,
    export_path: Path,
    source_items: list[dict[str, Any]],
    panel_items: list[dict[str, Any]],
    needs_review: list[dict[str, Any]],
    original_class_counts: Counter[str],
    panel_class_counts: Counter[str],
    panel_split_class_counts: dict[str, Counter[str]],
    original_tiny_height_count: int,
    original_tiny_area_count: int,
    skipped_items: Counter[str],
    rare_min_train_panels: int,
    thresholds: dict[str, float],
) -> dict[str, Any]:
    """Build a redacted panelization summary."""
    original_box_count = sum(original_class_counts.values())
    panel_box_count = sum(panel_class_counts.values())
    train_counts = panel_split_class_counts.get("train", Counter())
    rare_status = {
        class_name: {
            "train_panel_count": train_counts.get(class_name, 0),
            "min_required": rare_min_train_panels,
            "passed": train_counts.get(class_name, 0) >= rare_min_train_panels,
        }
        for class_name in RARE_CLASS_NAMES
    }
    class_coverage = {
        class_name: panel_class_counts.get(class_name, 0)
        for class_name in SUPPLEMENT_SECTION_CLASS_NAMES
    }
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": (
            "ready_for_panelized_yolo_materialization"
            if all(value["passed"] for value in rare_status.values())
            else "needs_more_review_or_rare_class_annotation"
        ),
        "created_at": datetime.now(UTC).isoformat(),
        "source_export_name": export_path.name,
        "source_doc_urls": list(SOURCE_DOC_URLS),
        "thresholds": thresholds,
        "original_item_count": len(source_items),
        "original_box_count": original_box_count,
        "original_tiny_height_count": original_tiny_height_count,
        "original_tiny_area_count": original_tiny_area_count,
        "panel_item_count": len(panel_items),
        "panel_box_count": panel_box_count,
        "box_reduction_count": original_box_count - panel_box_count,
        "box_reduction_ratio": round(
            (original_box_count - panel_box_count) / original_box_count,
            6,
        )
        if original_box_count
        else 0.0,
        "panel_class_counts": class_coverage,
        "panel_split_class_counts": {
            split: {
                class_name: counts.get(class_name, 0)
                for class_name in SUPPLEMENT_SECTION_CLASS_NAMES
            }
            for split, counts in sorted(panel_split_class_counts.items())
        },
        "needs_review_count": len(needs_review),
        "needs_review_class_counts": dict(Counter(row["class_name"] for row in needs_review)),
        "skipped_item_counts": dict(skipped_items),
        "rare_class_min_train_panel_gate": rare_status,
        "all_classes_present": all(count > 0 for count in class_coverage.values()),
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
        "private_source_refs_stored_in_review_artifact": False,
    }


def _annotation_targets(
    *,
    panel_export: dict[str, Any],
    summary: dict[str, Any],
    rare_min_train_panels: int,
) -> dict[str, Any]:
    """Build redacted rare-class annotation targets.

    Args:
        panel_export: Panelized export artifact.
        summary: Panel merge summary.
        rare_min_train_panels: Minimum train panel count for rare classes.

    Returns:
        Redacted annotation target artifact for operator planning.
    """
    rare_status = summary.get("rare_class_min_train_panel_gate", {})
    deficits = {
        class_name: {
            "train_panel_count": status.get("train_panel_count", 0),
            "min_required": rare_min_train_panels,
            "additional_train_panels_needed": max(
                0,
                rare_min_train_panels - int(status.get("train_panel_count", 0)),
            ),
        }
        for class_name, status in rare_status.items()
        if isinstance(status, dict) and status.get("passed") is not True
    }
    items = panel_export.get("items", [])
    candidates: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict) or item.get("split") != "train":
            continue
        source_ref = item.get("source_ref")
        if not isinstance(source_ref, str):
            continue
        labels = item.get("labels")
        if not isinstance(labels, list):
            continue
        class_names = sorted(
            {
                label.get("label")
                for label in labels
                if isinstance(label, dict) and isinstance(label.get("label"), str)
            }
        )
        for class_name, deficit in deficits.items():
            if class_name in class_names:
                continue
            if not {"ingredient_amounts", "supplement_facts"} & set(class_names):
                continue
            candidates.append(
                {
                    "source_ref_hash": _source_ref_hash(source_ref),
                    "split": "train",
                    "target_class": class_name,
                    "candidate_reason": "train image has nutrition sections but no panel for target rare class",
                    "existing_class_count": len(class_names),
                    "additional_train_panels_needed": deficit[
                        "additional_train_panels_needed"
                    ],
                }
            )
    targets = {
        "schema_version": ANNOTATION_TARGETS_SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "needs_operator_annotation" if deficits else "not_needed",
        "rare_class_deficits": deficits,
        "candidate_strategy": (
            "Prioritize train split images with ingredient_amounts or "
            "supplement_facts panels but no target rare-class panel."
        ),
        "candidate_count": len(candidates),
        "candidates": candidates[:100],
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
        "private_source_refs_stored": False,
    }
    _assert_redacted(targets)
    return targets


def _source_ref_hash(source_ref: str) -> str:
    """Return a short stable source-ref digest."""
    return hashlib.sha256(source_ref.encode("utf-8")).hexdigest()[:16]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON object with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write JSONL rows with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _cli_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Return safe compact CLI output."""
    return {
        "status": summary.get("status"),
        "original_item_count": summary.get("original_item_count"),
        "original_box_count": summary.get("original_box_count"),
        "panel_item_count": summary.get("panel_item_count"),
        "panel_box_count": summary.get("panel_box_count"),
        "needs_review_count": summary.get("needs_review_count"),
        "rare_class_min_train_panel_gate": summary.get("rare_class_min_train_panel_gate"),
    }


def _failure_summary(*, error: Exception, export_name: str) -> dict[str, Any]:
    """Build a redacted failure summary."""
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": "failed",
        "source_export_name": export_name,
        "error_type": type(error).__name__,
        "error": str(error),
        "source_doc_urls": list(SOURCE_DOC_URLS),
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
    }


def _assert_redacted(payload: object) -> None:
    """Reject unsafe strings in summary/review payloads.

    Args:
        payload: JSON-like payload to inspect.

    Raises:
        PanelMergeError: If a raw path, URL, provider payload key, or private
            source ref is found in an operator-facing artifact.
    """
    dumped = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    forbidden_markers = (
        "/Users/",
        "/Volumes/",
        "/private/",
        "\\Users\\",
        "\\Volumes\\",
        "file://",
        "media:",
        "learning_image:",
        '"raw_ocr_text":',
        '"provider_payload":',
        '"provider_raw_payload":',
        '"image_bytes":',
        '"authorization":',
    )
    if any(marker in dumped for marker in forbidden_markers):
        raise PanelMergeError("Operator-facing panel merge artifact contains unsafe raw data.")


if __name__ == "__main__":
    main()
