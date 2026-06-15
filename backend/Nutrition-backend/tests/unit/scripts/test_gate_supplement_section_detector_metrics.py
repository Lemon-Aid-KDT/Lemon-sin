"""Tests for supplement section detector promotion gate."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[4]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

detector_gate = importlib.import_module("scripts.gate_supplement_section_detector_metrics")

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


def _write_metrics(path: Path, recall: float = 0.9, map50: float = 0.8) -> Path:
    """Write detector metrics fixture.

    Args:
        path: Destination metrics path.
        recall: Per-class recall value.
        map50: Overall mAP50 value.

    Returns:
        Written metrics path.
    """
    path.write_text(
        json.dumps(
            {
                "schema_version": "supplement-section-detector-eval-summary-v1",
                "overall": {"mAP50": map50},
                "per_class": {
                    class_name: {"recall": recall}
                    for class_name in SECTION_CLASS_NAMES
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_gate_detector_metrics_passes_when_thresholds_are_met(tmp_path: Path) -> None:
    """Verify promotion is allowed when detector metrics pass."""
    metrics_path = _write_metrics(tmp_path / "metrics.json")

    gate = detector_gate.gate_detector_metrics(metrics_path=metrics_path)

    assert gate["status"] == "passed"
    assert gate["promotion_allowed"] is True
    assert gate["blockers"] == []


def test_gate_detector_metrics_blocks_low_key_recalls(tmp_path: Path) -> None:
    """Verify class-specific recall thresholds are enforced."""
    metrics_path = _write_metrics(tmp_path / "metrics.json", recall=0.7, map50=0.72)

    gate = detector_gate.gate_detector_metrics(metrics_path=metrics_path)

    assert gate["status"] == "blocked"
    assert gate["promotion_allowed"] is False
    blocked_metrics = {blocker["metric"] for blocker in gate["blockers"]}
    assert "per_class.ingredient_amounts.recall" in blocked_metrics
    assert "per_class.supplement_facts.recall" in blocked_metrics


def test_gate_detector_metrics_blocks_missing_class_metrics(tmp_path: Path) -> None:
    """Verify missing per-class metrics fail closed."""
    metrics_path = _write_metrics(tmp_path / "metrics.json")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["per_class"].pop("other_ingredients")
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")

    gate = detector_gate.gate_detector_metrics(metrics_path=metrics_path)

    assert gate["status"] == "blocked"
    assert gate["promotion_allowed"] is False
    assert any(
        blocker["metric"] == "per_class.other_ingredients.recall"
        and blocker["actual"] is None
        for blocker in gate["blockers"]
    )


def test_cli_writes_detector_gate_output(tmp_path: Path, capsys: Any) -> None:
    """Verify CLI writes a compact redacted gate summary."""
    metrics_path = _write_metrics(tmp_path / "metrics.json")
    output_path = tmp_path / "gate.json"

    detector_gate.main(["--metrics", str(metrics_path), "--output", str(output_path)])
    captured = capsys.readouterr().out

    assert output_path.is_file()
    assert '"promotion_allowed": true' in output_path.read_text(encoding="utf-8")
    assert "passed" in captured


def test_gate_detector_metrics_rejects_bad_threshold(tmp_path: Path) -> None:
    """Verify invalid threshold values are rejected."""
    metrics_path = _write_metrics(tmp_path / "metrics.json")

    with pytest.raises(ValueError, match="min_map50"):
        detector_gate.gate_detector_metrics(metrics_path=metrics_path, min_map50=1.5)

