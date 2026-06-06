"""Evaluate PaddleOCR text extraction against the CLOVA pseudo-ground-truth.

Standalone harness that runs in the Python 3.12 PaddleOCR venv (``.venv-paddle``)
— it does NOT import the backend package (which requires py3.13). For each
benchmark-ready review image in the ground-truth bundle, it runs the local
PaddleOCR pipeline and scores the extracted text against the CLOVA-built GT.

Two metric families are reported:

* ``field_match_ratio`` (HEADLINE, operator-selected 95% target metric): for each
  structured GT field unit (product name, each ingredient display-name, each
  amount+unit, intake-method text), check whether it is present in the PaddleOCR
  text via a fuzzy partial match (rapidfuzz ``partial_ratio``). Precision-immune:
  PaddleOCR reading *extra* label text never lowers it, which is the correct
  framing for a structured-only pseudo-GT.
* LCS ``normalized_text_precision``/``recall``/``f1`` (mirrors the backend
  collector ``_normalized_text_extraction_metrics``) — kept for the formal
  eval-summary/gate chain. ``precision`` is structurally bounded below 1 against a
  structured-only reference; ``recall`` is the meaningful LCS signal.

Profiles select the detector/recognizer/resolution. PP-OCRv5 has no Korean server
recognizer, so the ``server`` profile is server-detector + Korean mobile-recognizer
at higher resolution (better text-region detection). Run only when no other heavy
model (e.g. the Ollama CLOVA-GT job) is loaded — the server detector on large
images is memory-hungry on CPU.

Outputs (1) a redacted JSON results file (numeric scores only) and, optionally,
(2) a flat observation JSONL compatible with
``merge_paddleocr_text_observations_into_benchmark.py`` so the formal py3.13
eval/gate chain can run. No raw OCR text is written to disk. Dry-run by default;
pass ``--apply`` to score.

References:
    https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from decimal import Decimal
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz
from rapidfuzz.distance import LCSseq

MAX_METRIC_CHARS = 12000
TARGET_PROVIDER = "paddleocr_local"
FIELD_MATCH_THRESHOLD = 85.0  # rapidfuzz partial_ratio (0-100) for field presence.

PROFILES: dict[str, dict[str, Any]] = {
    "mobile": {
        "det": "PP-OCRv5_mobile_det",
        "rec": "korean_PP-OCRv5_mobile_rec",
        "max_side": 2048,
    },
    "server": {
        # No Korean server recognizer exists in PP-OCRv5; use server detector +
        # Korean mobile recognizer at higher resolution for better detection.
        "det": "PP-OCRv5_server_det",
        "rec": "korean_PP-OCRv5_mobile_rec",
        "max_side": 3072,
    },
}


def _normalize_for_metric(text: str) -> str:
    """Return NFKC + lowercase + alphanumeric-only text (mirrors the backend metric)."""
    normalized = unicodedata.normalize("NFKC", text).lower()
    return "".join(char for char in normalized if char.isalnum())


def _metric_float(value: Decimal) -> float:
    """Return a 4-decimal float from a Decimal metric (mirrors the backend metric)."""
    return float(value.quantize(Decimal("0.0001")))


def _text_extraction_metrics(reference: str, hypothesis: str) -> dict[str, Any] | None:
    """Return LCS-based precision/recall/F1 for one image, or None when skipped.

    Args:
        reference: Structured-section ground-truth text.
        hypothesis: PaddleOCR predicted text.

    Returns:
        Numeric metric mapping, or None when the reference is empty or either
        string exceeds the metric character cap.
    """
    reference_chars = _normalize_for_metric(reference)
    hypothesis_chars = _normalize_for_metric(hypothesis)
    if not reference_chars:
        return None
    if len(reference_chars) > MAX_METRIC_CHARS or len(hypothesis_chars) > MAX_METRIC_CHARS:
        return None
    matched = LCSseq.similarity(reference_chars, hypothesis_chars)
    precision = Decimal(matched) / Decimal(len(hypothesis_chars)) if hypothesis_chars else Decimal(0)
    recall = Decimal(matched) / Decimal(len(reference_chars))
    denom = precision + recall
    f1 = (Decimal(2) * precision * recall / denom) if denom else Decimal(0)
    return {
        "matched_char_count": matched,
        "reference_char_count": len(reference_chars),
        "hypothesis_char_count": len(hypothesis_chars),
        "normalized_text_precision": _metric_float(precision),
        "normalized_text_recall": _metric_float(recall),
        "normalized_text_f1": _metric_float(f1),
    }


def _append_text(parts: list[str], value: Any) -> None:
    """Append one scalar expected value to the reference text parts."""
    if isinstance(value, str) and value.strip():
        parts.append(value.strip())
    elif isinstance(value, int | float) and not isinstance(value, bool):
        parts.append(str(value))


def _structured_reference(expected: dict[str, Any]) -> str:
    """Return the structured-section reference text (mirrors the backend builder)."""
    parts: list[str] = []
    _append_text(parts, expected.get("product_name"))
    _append_text(parts, expected.get("manufacturer"))
    for ingredient in expected.get("ingredients", []) or []:
        if not isinstance(ingredient, dict):
            continue
        for key in ("display_name", "original_name"):
            _append_text(parts, ingredient.get(key))
        _append_text(parts, ingredient.get("amount"))
        _append_text(parts, ingredient.get("unit"))
    intake = expected.get("intake_method")
    if isinstance(intake, dict):
        _append_text(parts, intake.get("text"))
    else:
        _append_text(parts, intake)
    for key in ("precautions", "allergen_warnings", "functional_claims", "label_sections"):
        value = expected.get(key)
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, dict):
                _append_text(parts, item.get("text"))
                _append_text(parts, item.get("section_type"))
            else:
                _append_text(parts, item)
    return " ".join(parts)


def _field_units(expected: dict[str, Any]) -> list[str]:
    """Return the GT field units scored by ``field_match_ratio``.

    Args:
        expected: GT ``expected`` object.

    Returns:
        Non-empty field-unit strings (product name, manufacturer, each ingredient
        display-name, each amount+unit pair, intake-method text).
    """
    units: list[str] = []
    for key in ("product_name", "manufacturer"):
        value = expected.get(key)
        if isinstance(value, str) and value.strip():
            units.append(value.strip())
    for ingredient in expected.get("ingredients", []) or []:
        if not isinstance(ingredient, dict):
            continue
        name = ingredient.get("display_name")
        if isinstance(name, str) and name.strip():
            units.append(name.strip())
        amount_unit = " ".join(
            str(ingredient[k])
            for k in ("amount", "unit")
            if ingredient.get(k) not in (None, "")
        )
        if amount_unit.strip():
            units.append(amount_unit.strip())
    intake = expected.get("intake_method")
    intake_text = intake.get("text") if isinstance(intake, dict) else intake
    if isinstance(intake_text, str) and intake_text.strip():
        units.append(intake_text.strip())
    return units


def _field_match_ratio(units: list[str], hypothesis_norm: str) -> tuple[int, int]:
    """Return ``(matched, total)`` GT field units present in the PaddleOCR text.

    A unit matches when its normalized form scores ``>= FIELD_MATCH_THRESHOLD`` via
    rapidfuzz ``partial_ratio`` against the normalized hypothesis (precision-immune).

    Args:
        units: GT field-unit strings.
        hypothesis_norm: Normalized PaddleOCR text.

    Returns:
        ``(matched_unit_count, total_unit_count)``.
    """
    total = 0
    matched = 0
    for unit in units:
        unit_norm = _normalize_for_metric(unit)
        if not unit_norm:
            continue
        total += 1
        if hypothesis_norm and fuzz.partial_ratio(unit_norm, hypothesis_norm) >= FIELD_MATCH_THRESHOLD:
            matched += 1
    return matched, total


def _ingredient_recall(expected: dict[str, Any], hypothesis_norm: str) -> tuple[int, int]:
    """Return ``(found, total)`` GT ingredient display-names present (substring)."""
    names = [
        _normalize_for_metric(str(item["display_name"]))
        for item in expected.get("ingredients", []) or []
        if isinstance(item, dict) and item.get("display_name")
    ]
    found = sum(1 for name in names if name and name in hypothesis_norm)
    return found, len(names)


def _build_ocr(
    *,
    det_model: str,
    rec_model: str,
    max_side: int,
    det_box_thresh: float | None = None,
    det_thresh: float | None = None,
    det_unclip_ratio: float | None = None,
    rec_model_dir: str | None = None,
):
    """Construct a PaddleOCR pipeline with explicit det/rec models and size bound.

    The optional detection-sensitivity knobs (``det_box_thresh``/``det_thresh``/
    ``det_unclip_ratio``) are a no-training accuracy lever: lower thresholds and a
    larger unclip ratio recover more text regions (amounts, intake lines, small
    print), which lifts ``field_match_ratio`` against a structured-only GT. When
    all three are ``None`` the call is identical to the PaddleOCR defaults.

    Args:
        det_model: PaddleOCR detection model name.
        rec_model: PaddleOCR recognition model name.
        max_side: Max image side length before detection (memory bound).
        det_box_thresh: Optional detection box score threshold.
        det_thresh: Optional detection pixel binarization threshold.
        det_unclip_ratio: Optional detection box expansion ratio.

    Returns:
        A configured PaddleOCR pipeline.
    """
    from paddleocr import PaddleOCR  # noqa: PLC0415

    det_kwargs: dict[str, Any] = {}
    if det_box_thresh is not None:
        det_kwargs["text_det_box_thresh"] = det_box_thresh
    if det_thresh is not None:
        det_kwargs["text_det_thresh"] = det_thresh
    if det_unclip_ratio is not None:
        det_kwargs["text_det_unclip_ratio"] = det_unclip_ratio
    if rec_model_dir is not None:
        det_kwargs["text_recognition_model_dir"] = rec_model_dir
    return PaddleOCR(
        lang="korean",
        use_textline_orientation=False,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        text_detection_model_name=det_model,
        text_recognition_model_name=rec_model,
        text_det_limit_side_len=max_side,
        text_det_limit_type="max",
        **det_kwargs,
    )


def _predict_text(ocr: Any, image_path: Path) -> str:
    """Run PaddleOCR on one image and return its joined recognized text."""
    result = ocr.predict(str(image_path))
    if not result:
        return ""
    first = result[0]
    texts = first.get("rec_texts") if hasattr(first, "get") else None
    return " ".join(texts) if texts else ""


def evaluate(
    *,
    bundle_dir: Path,
    limit: int | None,
    det_model: str,
    rec_model: str,
    max_side: int,
    det_box_thresh: float | None = None,
    det_thresh: float | None = None,
    det_unclip_ratio: float | None = None,
    rec_model_dir: str | None = None,
) -> dict[str, Any]:
    """Score PaddleOCR text extraction over the ready GT rows.

    Args:
        bundle_dir: GT review bundle directory.
        limit: Optional cap on scored images.
        det_model: PaddleOCR detection model name.
        rec_model: PaddleOCR recognition model name.
        max_side: Max image side length before detection (memory bound).
        det_box_thresh: Optional detection box score threshold.
        det_thresh: Optional detection pixel binarization threshold.
        det_unclip_ratio: Optional detection box expansion ratio.

    Returns:
        Redacted results: aggregates, per-image numeric scores, and per-image
        observation records (provider-shaped) for the formal eval chain.
    """
    todo = bundle_dir / "ground-truth.todo.jsonl"
    rows = [
        json.loads(line)
        for line in todo.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ready = [
        r
        for r in rows
        if r.get("ready_for_benchmark_after_review") is True and isinstance(r.get("expected"), dict)
    ]
    if limit is not None:
        ready = ready[:limit]
    ocr = _build_ocr(
        det_model=det_model,
        rec_model=rec_model,
        max_side=max_side,
        det_box_thresh=det_box_thresh,
        det_thresh=det_thresh,
        det_unclip_ratio=det_unclip_ratio,
        rec_model_dir=rec_model_dir,
    )
    per_image: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    sums = {"normalized_text_precision": 0.0, "normalized_text_recall": 0.0, "normalized_text_f1": 0.0}
    field_ratio_sum = 0.0
    field_matched_total = 0
    field_unit_total = 0
    scored = 0
    skipped = 0
    failed = 0
    recall_found = 0
    recall_total = 0
    for row in ready:
        expected = row["expected"]
        fixture_id = row.get("fixture_id")
        image_path = str(row.get("image_path", "")).strip()
        if not image_path:
            failed += 1
            continue
        try:
            predicted = _predict_text(ocr, bundle_dir / image_path)
        except Exception:  # per-row isolation: count and continue (no raw error text stored)
            failed += 1
            continue
        hypothesis_norm = _normalize_for_metric(predicted)
        reference = _structured_reference(expected)
        metrics = _text_extraction_metrics(reference, predicted)
        f_matched, f_total = _field_match_ratio(_field_units(expected), hypothesis_norm)
        found, total = _ingredient_recall(expected, hypothesis_norm)
        recall_found += found
        recall_total += total
        field_matched_total += f_matched
        field_unit_total += f_total
        if metrics is None:
            skipped += 1
            continue
        scored += 1
        for key in sums:
            sums[key] += metrics[key]
        image_field_ratio = round(f_matched / f_total, 4) if f_total else 0.0
        field_ratio_sum += image_field_ratio
        per_image.append(
            {
                "fixture_id": fixture_id,
                "field_match_ratio": image_field_ratio,
                "field_matched": f_matched,
                "field_total": f_total,
                "normalized_text_precision": metrics["normalized_text_precision"],
                "normalized_text_recall": metrics["normalized_text_recall"],
                "normalized_text_f1": metrics["normalized_text_f1"],
                "ingredient_found": found,
                "ingredient_total": total,
            }
        )
        observations.append(
            {
                "fixture_id": fixture_id,
                "provider": TARGET_PROVIDER,
                "status": "completed",
                "text_non_empty": bool(predicted.strip()),
                "char_count": metrics["hypothesis_char_count"],
                "field_match_ratio": image_field_ratio,
                "matched_char_count": metrics["matched_char_count"],
                "reference_char_count": metrics["reference_char_count"],
                "hypothesis_char_count": metrics["hypothesis_char_count"],
                "normalized_text_precision": metrics["normalized_text_precision"],
                "normalized_text_recall": metrics["normalized_text_recall"],
                "normalized_text_f1": metrics["normalized_text_f1"],
                "text_metric_reference_source": "expected.structured_sections",
            }
        )
    return {
        "schema_version": "paddleocr-clova-eval-v3",
        "provider": TARGET_PROVIDER,
        "detection_model": det_model,
        "recognition_model": rec_model,
        "recognition_model_dir": rec_model_dir,
        "max_side": max_side,
        "det_box_thresh": det_box_thresh,
        "det_thresh": det_thresh,
        "det_unclip_ratio": det_unclip_ratio,
        "field_match_threshold": FIELD_MATCH_THRESHOLD,
        "scored_images": scored,
        "skipped_images": skipped,
        "failed_images": failed,
        "field_match_ratio_macro": round(field_ratio_sum / scored, 4) if scored else 0.0,
        "field_match_ratio_micro": round(field_matched_total / field_unit_total, 4) if field_unit_total else 0.0,
        "field_matched_total": [field_matched_total, field_unit_total],
        "mean_normalized_text_precision": round(sums["normalized_text_precision"] / scored, 4) if scored else 0.0,
        "mean_normalized_text_recall": round(sums["normalized_text_recall"] / scored, 4) if scored else 0.0,
        "mean_normalized_text_f1": round(sums["normalized_text_f1"] / scored, 4) if scored else 0.0,
        "ingredient_recall": round(recall_found / recall_total, 4) if recall_total else 0.0,
        "ingredient_found_total": [recall_found, recall_total],
        "per_image": per_image,
        "observations": observations,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--observations-output",
        type=Path,
        default=None,
        help="Optional flat observation JSONL for the formal merge/eval/gate chain.",
    )
    parser.add_argument("--profile", choices=sorted(PROFILES), default="mobile")
    parser.add_argument("--det-model", default=None, help="Override the profile detection model.")
    parser.add_argument("--rec-model", default=None, help="Override the profile recognition model.")
    parser.add_argument(
        "--rec-model-dir",
        default=None,
        help="Local PaddleOCR inference model dir for a fine-tuned recognizer (e.g. best_accuracy/inference).",
    )
    parser.add_argument("--max-side", type=int, default=None, help="Override the profile max side.")
    parser.add_argument(
        "--det-box-thresh",
        type=float,
        default=None,
        help="Detection box score threshold (lower = more text regions; no-training recall lever).",
    )
    parser.add_argument(
        "--det-thresh",
        type=float,
        default=None,
        help="Detection pixel binarization threshold (lower = more text regions).",
    )
    parser.add_argument(
        "--det-unclip-ratio",
        type=float,
        default=None,
        help="Detection box expansion ratio (higher = larger boxes, fewer truncated lines).",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not (args.bundle_dir / "ground-truth.todo.jsonl").is_file():
        raise SystemExit(f"ERROR: ground-truth.todo.jsonl not found under {args.bundle_dir}")
    profile = PROFILES[args.profile]
    det_model = args.det_model or profile["det"]
    rec_model = args.rec_model or profile["rec"]
    max_side = args.max_side or profile["max_side"]
    if not args.apply:
        print(
            json.dumps(
                {"apply_requested": False, "profile": args.profile, "det": det_model, "rec": rec_model}
            )
        )
        return 0
    results = evaluate(
        bundle_dir=args.bundle_dir,
        limit=args.limit,
        det_model=det_model,
        rec_model=rec_model,
        max_side=max_side,
        det_box_thresh=args.det_box_thresh,
        det_thresh=args.det_thresh,
        det_unclip_ratio=args.det_unclip_ratio,
        rec_model_dir=args.rec_model_dir,
    )
    observations = results.pop("observations")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.observations_output is not None:
        args.observations_output.parent.mkdir(parents=True, exist_ok=True)
        args.observations_output.write_text(
            "".join(json.dumps(obs, ensure_ascii=False) + "\n" for obs in observations),
            encoding="utf-8",
        )
    print(
        json.dumps(
            {k: v for k, v in results.items() if k != "per_image"}, ensure_ascii=False, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
