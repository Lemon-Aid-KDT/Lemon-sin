"""Tests for adaptive PaddleOCR structured evaluation."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[4]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

adaptive_eval = importlib.import_module("scripts.run_paddleocr_adaptive_structured_eval")


def _write_bundle(bundle_dir: Path) -> None:
    """Write a minimal two-ingredient benchmark bundle."""
    bundle_dir.mkdir()
    (bundle_dir / "ground-truth.todo.jsonl").write_text(
        json.dumps(
            {
                "fixture_id": "fixture-1",
                "image_path": "image.jpg",
                "ready_for_benchmark_after_review": True,
                "expected": {
                    "ingredients": [
                        {"display_name": "Vitamin C", "amount": "100", "unit": "mg"},
                        {"display_name": "Vitamin D", "amount": "200", "unit": "mcg"},
                    ]
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def test_adaptive_union_improves_ingredient_recall_without_raw_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify union merge can lift recall and keeps normal artifacts redacted."""
    bundle_dir = tmp_path / "bundle"
    output_dir = tmp_path / "out"
    splits = tmp_path / "splits.jsonl"
    _write_bundle(bundle_dir)
    splits.write_text(
        json.dumps({"fixture_id": "fixture-1", "split": "holdout"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    def fake_build_ocr(**kwargs: Any) -> dict[str, Any]:
        return {"rec_model_dir": kwargs["rec_model_dir"]}

    def fake_predict_lines(ocr: dict[str, Any], _: Path) -> list[str]:
        if ocr["rec_model_dir"] == "primary-dir":
            return ["Vitamin C 100 mg"]
        return ["Vitamin D 200 mcg"]

    monkeypatch.setattr(adaptive_eval, "_build_ocr", fake_build_ocr)
    monkeypatch.setattr(adaptive_eval, "_predict_lines", fake_predict_lines)
    args = argparse.Namespace(
        bundle_dir=bundle_dir,
        splits=splits,
        output_dir=output_dir,
        profile="server_detection",
        primary_name="b128",
        primary_rec_model_dir="primary-dir",
        secondary_name="b64",
        secondary_rec_model_dir="secondary-dir",
        det_model=None,
        rec_model=None,
        max_side=None,
        det_box_thresh=None,
        det_thresh=None,
        det_unclip_ratio=2.5,
        post_pass="ingredient_alias_amount_unit",
        eval_split="holdout",
        provider="paddleocr_local",
        target_threshold="0.90",
        min_ingredient_recall="0.85",
        min_fixtures=1,
        limit=None,
        raw_debug_dir=None,
        apply=True,
    )

    result = adaptive_eval.run_adaptive_eval(args)

    by_strategy = {item["strategy"]: item for item in result["strategy_summaries"]}
    assert by_strategy["b128"]["metrics"]["ingredient_recall"] == 0.5
    assert by_strategy["union"]["metrics"]["ingredient_recall"] == 1.0
    assert result["ingredient_recall_improved_by_union"] is True
    assert (output_dir / "line-comparison-hardcases.redacted.json").is_file()
    assert "Vitamin C" not in json.dumps(result, ensure_ascii=False)
    assert "Vitamin D" not in (output_dir / "paddleocr-adaptive-eval.union.json").read_text(
        encoding="utf-8"
    )
