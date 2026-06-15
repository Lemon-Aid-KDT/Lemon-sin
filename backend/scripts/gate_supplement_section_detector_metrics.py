"""Gate supplement section detector metrics before structured promotion.

The detector gate is intentionally separate from the structured extraction gate:
it verifies whether the section detector is strong enough to be promoted as a
production signal. Failing this gate does not prevent diagnostic structured
evaluation, but it blocks model promotion.

Expected input schema:

```
{
  "schema_version": "supplement-section-detector-eval-summary-v1",
  "overall": {"mAP50": 0.72},
  "per_class": {
    "ingredient_amounts": {"recall": 0.86},
    "supplement_facts": {"recall": 0.88}
  }
}
```

References:
    https://docs.ultralytics.com/modes/train/
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SUMMARY_SCHEMA_VERSION = "supplement-section-detector-promotion-gate-v1"
METRICS_SCHEMA_VERSION = "supplement-section-detector-eval-summary-v1"
DEFAULT_MIN_MAP50 = 0.70
DEFAULT_MIN_INGREDIENT_RECALL = 0.85
DEFAULT_MIN_SUPPLEMENT_FACTS_RECALL = 0.85
DEFAULT_MIN_KEY_CLASS_RECALL = 0.65
KEY_CLASS_NAMES = (
    "product_identity",
    "supplement_facts",
    "ingredient_amounts",
    "precautions",
    "allergen_warning",
    "intake_method",
    "other_ingredients",
    "functional_claims",
)
SOURCE_DOC_URLS = ("https://docs.ultralytics.com/modes/train/",)


class DetectorGateError(ValueError):
    """Raised when detector gate input is malformed."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument list for tests.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--min-map50", type=float, default=DEFAULT_MIN_MAP50)
    parser.add_argument(
        "--min-ingredient-recall",
        type=float,
        default=DEFAULT_MIN_INGREDIENT_RECALL,
    )
    parser.add_argument(
        "--min-supplement-facts-recall",
        type=float,
        default=DEFAULT_MIN_SUPPLEMENT_FACTS_RECALL,
    )
    parser.add_argument(
        "--min-key-class-recall",
        type=float,
        default=DEFAULT_MIN_KEY_CLASS_RECALL,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run detector gate CLI.

    Args:
        argv: Optional argument list for tests.
    """
    args = parse_args(argv)
    try:
        gate = gate_detector_metrics(
            metrics_path=args.metrics,
            min_map50=args.min_map50,
            min_ingredient_recall=args.min_ingredient_recall,
            min_supplement_facts_recall=args.min_supplement_facts_recall,
            min_key_class_recall=args.min_key_class_recall,
        )
        _write_json(args.output, gate)
        print(json.dumps(_cli_summary(gate), ensure_ascii=False, sort_keys=True))
    except (OSError, json.JSONDecodeError, DetectorGateError, ValueError) as exc:
        failure = _failure_summary(error=exc, metrics_name=args.metrics.name)
        _write_json(args.output, failure)
        print(json.dumps(_cli_summary(failure), ensure_ascii=False, sort_keys=True))
        raise SystemExit(1) from None


def gate_detector_metrics(
    *,
    metrics_path: Path,
    min_map50: float = DEFAULT_MIN_MAP50,
    min_ingredient_recall: float = DEFAULT_MIN_INGREDIENT_RECALL,
    min_supplement_facts_recall: float = DEFAULT_MIN_SUPPLEMENT_FACTS_RECALL,
    min_key_class_recall: float = DEFAULT_MIN_KEY_CLASS_RECALL,
) -> dict[str, Any]:
    """Evaluate detector metrics against promotion thresholds.

    Args:
        metrics_path: Detector eval summary JSON.
        min_map50: Minimum overall mAP50.
        min_ingredient_recall: Minimum ingredient_amounts recall.
        min_supplement_facts_recall: Minimum supplement_facts recall.
        min_key_class_recall: Minimum recall for every key class.

    Returns:
        Redacted detector promotion gate summary.

    Raises:
        DetectorGateError: If metrics schema or required fields are missing.
        ValueError: If thresholds are invalid.
    """
    thresholds = {
        "min_map50": min_map50,
        "min_ingredient_recall": min_ingredient_recall,
        "min_supplement_facts_recall": min_supplement_facts_recall,
        "min_key_class_recall": min_key_class_recall,
    }
    _validate_thresholds(thresholds)
    metrics = _read_metrics(metrics_path)
    overall_map50 = _metric(metrics.get("overall"), "mAP50", "overall")
    per_class = metrics.get("per_class")
    if not isinstance(per_class, dict):
        raise DetectorGateError("Detector metrics require per_class object.")

    class_recalls: dict[str, float | None] = {}
    blockers: list[dict[str, Any]] = []
    if overall_map50 < min_map50:
        blockers.append(
            {
                "metric": "overall.mAP50",
                "actual": round(overall_map50, 6),
                "required": min_map50,
            }
        )
    for class_name in KEY_CLASS_NAMES:
        raw_class_metrics = per_class.get(class_name)
        if raw_class_metrics is None:
            class_recalls[class_name] = None
            blockers.append({"metric": f"per_class.{class_name}.recall", "actual": None, "required": min_key_class_recall})
            continue
        recall = _metric(raw_class_metrics, "recall", f"per_class.{class_name}")
        class_recalls[class_name] = recall
        required = _required_recall(
            class_name,
            min_ingredient_recall=min_ingredient_recall,
            min_supplement_facts_recall=min_supplement_facts_recall,
            min_key_class_recall=min_key_class_recall,
        )
        if recall < required:
            blockers.append(
                {
                    "metric": f"per_class.{class_name}.recall",
                    "actual": round(recall, 6),
                    "required": required,
                }
            )

    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not blockers else "blocked",
        "source_metrics_name": metrics_path.name,
        "source_doc_urls": list(SOURCE_DOC_URLS),
        "thresholds": thresholds,
        "overall": {"mAP50": round(overall_map50, 6)},
        "per_class_recall": {
            class_name: None if recall is None else round(recall, 6)
            for class_name, recall in class_recalls.items()
        },
        "blockers": blockers,
        "promotion_allowed": not blockers,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
    }


def _read_metrics(metrics_path: Path) -> dict[str, Any]:
    """Read and validate detector metrics object."""
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    if not isinstance(metrics, dict):
        raise DetectorGateError("Detector metrics must be a JSON object.")
    if metrics.get("schema_version") != METRICS_SCHEMA_VERSION:
        raise DetectorGateError("Unsupported detector metrics schema.")
    return metrics


def _validate_thresholds(thresholds: dict[str, float]) -> None:
    """Validate numeric gate thresholds."""
    for name, value in thresholds.items():
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be in the 0..1 range.")


def _metric(raw_metrics: object, key: str, context: str) -> float:
    """Read one normalized metric value."""
    if not isinstance(raw_metrics, dict):
        raise DetectorGateError(f"{context} metrics must be an object.")
    value = raw_metrics.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise DetectorGateError(f"{context}.{key} must be numeric.")
    metric = float(value)
    if not math.isfinite(metric) or not 0 <= metric <= 1:
        raise DetectorGateError(f"{context}.{key} must be in the 0..1 range.")
    return metric


def _required_recall(
    class_name: str,
    *,
    min_ingredient_recall: float,
    min_supplement_facts_recall: float,
    min_key_class_recall: float,
) -> float:
    """Return class-specific recall threshold."""
    if class_name == "ingredient_amounts":
        return min_ingredient_recall
    if class_name == "supplement_facts":
        return min_supplement_facts_recall
    return min_key_class_recall


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _cli_summary(gate: dict[str, Any]) -> dict[str, Any]:
    """Return compact safe CLI summary."""
    return {
        "status": gate.get("status"),
        "promotion_allowed": gate.get("promotion_allowed"),
        "blocker_count": len(gate.get("blockers", []))
        if isinstance(gate.get("blockers"), list)
        else None,
    }


def _failure_summary(*, error: Exception, metrics_name: str) -> dict[str, Any]:
    """Build a redacted failure summary."""
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "failed",
        "promotion_allowed": False,
        "source_metrics_name": metrics_name,
        "error_type": type(error).__name__,
        "error": str(error),
        "source_doc_urls": list(SOURCE_DOC_URLS),
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
    }


if __name__ == "__main__":
    main()
