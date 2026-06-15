"""Tests for supplement section panel-box merging."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[4]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

panelizer = importlib.import_module("scripts.merge_supplement_section_panel_boxes")

SECTION_CLASS_NAMES = [
    "product_identity",
    "supplement_facts",
    "ingredient_amounts",
    "precautions",
    "allergen_warning",
    "intake_method",
    "other_ingredients",
    "functional_claims",
]


def _label(
    class_name: str,
    y_center: float,
    height: float,
    x_center: float = 0.5,
    width: float = 0.2,
) -> dict[str, Any]:
    """Build one normalized YOLO label.

    Args:
        class_name: Section class name.
        y_center: Normalized y center.
        height: Normalized height.
        x_center: Normalized x center.
        width: Normalized width.

    Returns:
        Export label mapping.
    """
    class_id = SECTION_CLASS_NAMES.index(class_name)
    return {
        "class_id": class_id,
        "label": class_name,
        "x_center": x_center,
        "y_center": y_center,
        "width": width,
        "height": height,
    }


def _write_export(path: Path) -> Path:
    """Write a small supplement-section export fixture."""
    items = [
        {
            "source_ref": "media:11111111-1111-4111-8111-111111111111",
            "split": "train",
            "labels": [
                _label("ingredient_amounts", 0.30, 0.02),
                _label("ingredient_amounts", 0.34, 0.02),
                _label("ingredient_amounts", 0.90, 0.02),
                _label("intake_method", 0.10, 0.001, width=0.005),
            ],
        },
        {
            "source_ref": "media:22222222-2222-4222-8222-222222222222",
            "split": "val",
            "labels": [_label("supplement_facts", 0.20, 0.05)],
        },
    ]
    path.write_text(
        json.dumps(
            {
                "schema_version": "supplement-section-yolo-detect-export-v1",
                "class_names": SECTION_CLASS_NAMES,
                "item_count": len(items),
                "split_counts": {"train": 1, "val": 1, "test": 0, "holdout": 0},
                "items": items,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_merge_section_panel_boxes_merges_nearby_same_class_boxes(tmp_path: Path) -> None:
    """Verify nearby same-class line boxes become one larger panel."""
    export_path = _write_export(tmp_path / "export.json")

    export, needs_review, summary = panelizer.merge_section_panel_boxes(
        export_path=export_path,
        min_panel_height=0.015,
        min_panel_area=0.0025,
        rare_min_train_panels=1,
    )

    train_labels = export["items"][0]["labels"]
    ingredient_labels = [
        label for label in train_labels if label["label"] == "ingredient_amounts"
    ]
    assert len(ingredient_labels) == 2
    assert ingredient_labels[0]["height"] > 0.06
    assert summary["original_box_count"] == 5
    assert summary["panel_box_count"] == 3
    assert summary["original_tiny_height_count"] == 1
    assert len(needs_review) == 1
    assert needs_review[0]["source_ref_hash"]
    assert "media:" not in json.dumps(needs_review)


def test_cli_writes_redacted_summary_and_apply_outputs(
    tmp_path: Path,
    capsys: Any,
) -> None:
    """Verify CLI artifacts avoid raw source refs and local paths."""
    export_path = _write_export(tmp_path / "export.json")
    output_path = tmp_path / "panel.json"
    summary_path = tmp_path / "summary.json"
    review_path = tmp_path / "needs-review.jsonl"
    targets_path = tmp_path / "annotation-targets.json"

    panelizer.main(
        [
            "--export",
            str(export_path),
            "--output",
            str(output_path),
            "--summary",
            str(summary_path),
            "--needs-review",
            str(review_path),
            "--annotation-targets",
            str(targets_path),
            "--rare-min-train-panels",
            "1",
            "--apply",
        ]
    )
    captured = capsys.readouterr().out
    dumped = (
        summary_path.read_text(encoding="utf-8")
        + review_path.read_text(encoding="utf-8")
        + targets_path.read_text(encoding="utf-8")
        + captured
    )

    assert output_path.is_file()
    assert summary_path.is_file()
    assert review_path.is_file()
    assert targets_path.is_file()
    assert "media:" not in dumped
    assert str(tmp_path) not in dumped
    assert "/Volumes/" not in dumped
