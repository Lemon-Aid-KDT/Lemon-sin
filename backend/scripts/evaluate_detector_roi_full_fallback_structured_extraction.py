"""Evaluate structured extraction with detector ROI plus full-image fallback.

This evaluator keeps the existing ``paddleocr_clova_eval`` metric contract but
changes the hypothesis source. It always runs full-image OCR, additionally runs
OCR on detector-predicted section crops, and builds a field-level merged
hypothesis in memory. Detector crop text is preferred for fields mapped to that
section; full-image OCR is used as the fallback when a crop is missing, too
small, or OCR-empty.

Only redacted numeric outputs are written. Raw OCR text, provider payloads,
absolute image paths, and crop datasets are not persisted.

References:
    https://docs.ultralytics.com/modes/predict/
    https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from PIL import Image

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from scripts.paddleocr_clova_eval import (  # noqa: E402
    FIELD_MATCH_THRESHOLD,
    PREPROCESS_MODES,
    PROFILES,
    TARGET_PROVIDER,
    _build_ocr,
    _field_match_ratio,
    _field_units,
    _ingredient_recall,
    _normalize_for_metric,
    _predict_text,
    _structured_reference,
    _text_extraction_metrics,
)

SECTION_CLASS_NAMES = (
    "product_identity",
    "supplement_facts",
    "ingredient_amounts",
    "precautions",
    "allergen_warning",
    "intake_method",
    "other_ingredients",
    "functional_claims",
)
FIELD_SECTION_PRIORITY = {
    "ingredients": ("ingredient_amounts", "supplement_facts", "other_ingredients"),
    "intake_method": ("intake_method",),
    "precautions": ("precautions",),
    "allergen_warnings": ("allergen_warning",),
    "functional_claims": ("functional_claims",),
    "product_identity": ("product_identity",),
}
DEFAULT_CROP_PAD = 12
DEFAULT_MIN_SECTION_AREA_RATIO = 0.0025
XYXY_COORD_COUNT = 4


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument list for tests.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-bundle", required=True, type=Path)
    parser.add_argument("--splits", required=True, type=Path)
    parser.add_argument("--eval-split", default="holdout")
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument(
        "--predicted-boxes-jsonl",
        type=Path,
        default=None,
        help=(
            "Optional redacted detector box JSONL keyed by fixture_id. "
            "When provided, Ultralytics is not imported and detector.predict is skipped."
        ),
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--observations-output", type=Path, default=None)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="mobile")
    parser.add_argument("--det-model", default=None)
    parser.add_argument("--rec-model", default=None)
    parser.add_argument("--rec-model-dir", default=None)
    parser.add_argument("--max-side", type=int, default=None)
    parser.add_argument("--det-box-thresh", type=float, default=None)
    parser.add_argument("--det-thresh", type=float, default=None)
    parser.add_argument("--det-unclip-ratio", type=float, default=None)
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--conf", type=float, default=0.05)
    parser.add_argument("--iou", type=float, default=0.7)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--crop-pad", type=int, default=DEFAULT_CROP_PAD)
    parser.add_argument("--preprocess-mode", choices=PREPROCESS_MODES, default="none")
    parser.add_argument(
        "--min-section-area-ratio",
        type=float,
        default=DEFAULT_MIN_SECTION_AREA_RATIO,
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def evaluate(  # noqa: PLR0915
    *,
    source_bundle: Path,
    splits: Path,
    eval_split: str,
    model_path: Path,
    limit: int | None,
    det_model: str,
    rec_model: str,
    max_side: int,
    det_box_thresh: float | None,
    det_thresh: float | None,
    det_unclip_ratio: float | None,
    rec_model_dir: str | None,
    imgsz: int,
    conf: float,
    iou: float,
    device: str,
    crop_pad: int,
    min_section_area_ratio: float,
    predicted_boxes_jsonl: Path | None,
    preprocess_mode: str,
) -> dict[str, Any]:
    """Run detector ROI plus full-image fallback structured evaluation.

    Args:
        source_bundle: Reviewed ground-truth bundle directory.
        splits: Benchmark split assignment JSONL.
        eval_split: Split to evaluate.
        model_path: Ultralytics detector weights.
        limit: Optional fixture cap.
        det_model: PaddleOCR text detection model name.
        rec_model: PaddleOCR text recognition model name.
        max_side: PaddleOCR detection max image side.
        det_box_thresh: Optional PaddleOCR box threshold.
        det_thresh: Optional PaddleOCR pixel threshold.
        det_unclip_ratio: Optional PaddleOCR unclip ratio.
        rec_model_dir: Optional fine-tuned recognition model directory.
        imgsz: Ultralytics detector inference size.
        conf: Ultralytics confidence threshold.
        iou: Ultralytics NMS IoU threshold.
        device: Ultralytics device string.
        crop_pad: Pixel padding for section crops.
        min_section_area_ratio: Minimum normalized section crop area for OCR.
        preprocess_mode: Temporary PaddleOCR input preprocessing mode.

    Returns:
        Redacted eval result compatible with structured summary builder.
    """
    rows = _ready_rows(source_bundle=source_bundle, splits=splits, eval_split=eval_split)
    if limit is not None:
        rows = rows[:limit]
    predicted_boxes_by_fixture = (
        _read_predicted_boxes_jsonl(predicted_boxes_jsonl)
        if predicted_boxes_jsonl is not None
        else None
    )
    detector = None
    if predicted_boxes_by_fixture is None:
        from ultralytics import YOLO  # noqa: PLC0415

        detector = YOLO(str(model_path))
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
    recall_found = 0
    recall_total = 0
    scored = 0
    skipped = 0
    failed = 0
    aggregate_stats: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()

    with TemporaryDirectory(prefix="lemon-roi-fallback-") as tmp:
        tmp_dir = Path(tmp)
        for row in rows:
            image_rel = str(row.get("image_path", "")).strip()
            expected = row.get("expected")
            fixture_id = row.get("fixture_id")
            if not image_rel or not isinstance(expected, dict):
                failed += 1
                continue
            image_path = source_bundle / image_rel
            try:
                full_text = _predict_text(
                    ocr,
                    image_path,
                    preprocess_mode=preprocess_mode,
                    tmp_dir=tmp_dir,
                )
                if predicted_boxes_by_fixture is not None:
                    predicted_boxes = predicted_boxes_by_fixture.get(str(fixture_id), [])
                else:
                    predicted_boxes = _predict_boxes(
                        model=detector,
                        image_path=image_path,
                        imgsz=imgsz,
                        conf=conf,
                        iou=iou,
                        device=device,
                    )
                section_texts, section_stats = _section_crop_texts(
                    ocr=ocr,
                    image_path=image_path,
                    boxes=predicted_boxes,
                    tmp_dir=tmp_dir,
                    crop_pad=crop_pad,
                    min_section_area_ratio=min_section_area_ratio,
                    preprocess_mode=preprocess_mode,
                )
                merged_text, merge_stats = _merged_hypothesis(
                    full_text=full_text,
                    section_texts=section_texts,
                )
            except Exception:
                failed += 1
                continue

            aggregate_stats.update(section_stats)
            aggregate_stats.update(merge_stats)
            for box in predicted_boxes:
                class_counts[box["class_name"]] += 1
            hypothesis_norm = _normalize_for_metric(merged_text)
            metrics = _text_extraction_metrics(_structured_reference(expected), merged_text)
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
                    "detector_box_count": len(predicted_boxes),
                    "section_crop_count": section_stats["section_crop_count"],
                    "full_fallback_field_count": merge_stats["full_fallback_field_count"],
                    "crop_preferred_field_count": merge_stats["crop_preferred_field_count"],
                }
            )
            observations.append(
                {
                    "fixture_id": fixture_id,
                    "provider": TARGET_PROVIDER,
                    "status": "completed",
                    "text_non_empty": bool(merged_text.strip()),
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
        "evaluation_mode": "detector_roi_full_fallback",
        "provider": TARGET_PROVIDER,
        "detector_model_artifact": model_path.name,
        "detector_boxes_source": (
            str(predicted_boxes_jsonl.name)
            if predicted_boxes_jsonl is not None
            else "ultralytics_predict"
        ),
        "detection_model": det_model,
        "recognition_model": rec_model,
        "recognition_model_dir": rec_model_dir,
        "recognition_model_dir_present": rec_model_dir is not None,
        "max_side": max_side,
        "det_box_thresh": det_box_thresh,
        "det_thresh": det_thresh,
        "det_unclip_ratio": det_unclip_ratio,
        "preprocess_mode": preprocess_mode,
        "imgsz": imgsz,
        "conf": conf,
        "iou": iou,
        "device": device,
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
        "detector_boxes_by_class": dict(sorted(class_counts.items())),
        "roi_merge_stats": dict(sorted(aggregate_stats.items())),
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
        "per_image": per_image,
        "observations": observations,
    }


def _ready_rows(*, source_bundle: Path, splits: Path, eval_split: str) -> list[dict[str, Any]]:
    """Return reviewed GT rows selected by split assignment."""
    fixture_ids = {
        str(row["fixture_id"])
        for row in _read_jsonl(splits)
        if row.get("split") == eval_split and row.get("fixture_id")
    }
    rows = _read_jsonl(source_bundle / "ground-truth.todo.jsonl")
    return [
        row
        for row in rows
        if row.get("fixture_id") in fixture_ids
        and row.get("ready_for_benchmark_after_review") is True
        and isinstance(row.get("expected"), dict)
        and row.get("image_path")
    ]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSONL object rows."""
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_predicted_boxes_jsonl(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Read redacted detector boxes keyed by fixture_id.

    Args:
        path: JSONL file containing ``fixture_id`` and ``boxes`` fields.

    Returns:
        Mapping from fixture id to redacted detector box dictionaries.

    Raises:
        ValueError: If a row does not contain the expected redacted structure.
    """
    boxes_by_fixture: dict[str, list[dict[str, Any]]] = {}
    for row in _read_jsonl(path):
        fixture_id = str(row.get("fixture_id", "")).strip()
        boxes = row.get("boxes")
        if not fixture_id or not isinstance(boxes, list):
            raise ValueError("Predicted boxes JSONL rows must contain fixture_id and boxes.")
        clean_boxes: list[dict[str, Any]] = []
        for box in boxes:
            if not isinstance(box, dict):
                raise ValueError("Predicted boxes must be objects.")
            class_name = str(box.get("class_name", ""))
            xyxy = box.get("xyxy")
            if (
                class_name not in SECTION_CLASS_NAMES
                or not isinstance(xyxy, list)
                or len(xyxy) != XYXY_COORD_COUNT
            ):
                raise ValueError("Predicted box contains unsupported class_name or xyxy.")
            clean_boxes.append(
                {
                    "class_id": int(box.get("class_id", SECTION_CLASS_NAMES.index(class_name))),
                    "class_name": class_name,
                    "confidence": float(box.get("confidence", 0.0)),
                    "xyxy": [float(value) for value in xyxy],
                }
            )
        boxes_by_fixture[fixture_id] = clean_boxes
    return boxes_by_fixture


def _predict_boxes(
    *,
    model: Any,
    image_path: Path,
    imgsz: int,
    conf: float,
    iou: float,
    device: str,
) -> list[dict[str, Any]]:
    """Run Ultralytics prediction and return redacted pixel boxes."""
    results = model.predict(str(image_path), imgsz=imgsz, conf=conf, iou=iou, device=device, verbose=False)
    if not results:
        return []
    result = results[0]
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return []
    xyxy = boxes.xyxy.cpu().tolist()
    cls_ids = boxes.cls.cpu().tolist()
    confs = boxes.conf.cpu().tolist()
    names = getattr(result, "names", {}) or {}
    out: list[dict[str, Any]] = []
    for coords, cls_value, conf_value in zip(xyxy, cls_ids, confs, strict=True):
        class_id = int(cls_value)
        class_name = str(
            names.get(
                class_id,
                SECTION_CLASS_NAMES[class_id] if 0 <= class_id < len(SECTION_CLASS_NAMES) else class_id,
            )
        )
        if class_name not in SECTION_CLASS_NAMES:
            continue
        out.append(
            {
                "class_id": class_id,
                "class_name": class_name,
                "confidence": float(conf_value),
                "xyxy": [float(value) for value in coords],
            }
        )
    return out


def _section_crop_texts(
    *,
    ocr: Any,
    image_path: Path,
    boxes: list[dict[str, Any]],
    tmp_dir: Path,
    crop_pad: int,
    min_section_area_ratio: float,
    preprocess_mode: str,
) -> tuple[dict[str, str], Counter[str]]:
    """OCR detector section crops without persisting crop datasets."""
    section_texts: dict[str, str] = {}
    stats: Counter[str] = Counter()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for box in boxes:
        grouped.setdefault(str(box["class_name"]), []).append(box)
    with Image.open(image_path) as raw:
        rgb = raw.convert("RGB")
        width, height = rgb.size
        for class_name, section_boxes in grouped.items():
            crop_box = _union_crop_box(
                boxes=section_boxes,
                image_width=width,
                image_height=height,
                crop_pad=crop_pad,
            )
            if crop_box is None:
                stats["section_crop_invalid"] += 1
                continue
            x0, y0, x1, y1 = crop_box
            area_ratio = ((x1 - x0) * (y1 - y0)) / (width * height)
            if area_ratio < min_section_area_ratio:
                stats["section_crop_area_rejected"] += 1
                continue
            crop_path = tmp_dir / f"{class_name}.jpg"
            rgb.crop(crop_box).save(crop_path, quality=92)
            text = _predict_text(
                ocr,
                crop_path,
                preprocess_mode=preprocess_mode,
                tmp_dir=tmp_dir,
            )
            stats["section_crop_count"] += 1
            stats[f"section_crop_{class_name}"] += 1
            if text.strip():
                section_texts[class_name] = text
                stats["section_crop_text_non_empty"] += 1
            else:
                stats["section_crop_text_empty"] += 1
    return section_texts, stats


def _union_crop_box(
    *,
    boxes: list[dict[str, Any]],
    image_width: int,
    image_height: int,
    crop_pad: int,
) -> tuple[int, int, int, int] | None:
    """Return padded union pixel crop box."""
    if not boxes:
        return None
    x0 = max(0, int(min(box["xyxy"][0] for box in boxes)) - crop_pad)
    y0 = max(0, int(min(box["xyxy"][1] for box in boxes)) - crop_pad)
    x1 = min(image_width, int(max(box["xyxy"][2] for box in boxes)) + crop_pad)
    y1 = min(image_height, int(max(box["xyxy"][3] for box in boxes)) + crop_pad)
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def _merged_hypothesis(*, full_text: str, section_texts: dict[str, str]) -> tuple[str, Counter[str]]:
    """Merge section OCR and full-image OCR with field-level fallback."""
    parts: list[str] = []
    stats: Counter[str] = Counter()
    for field_name, section_names in FIELD_SECTION_PRIORITY.items():
        crop_text = " ".join(
            section_texts[section_name]
            for section_name in section_names
            if section_texts.get(section_name, "").strip()
        ).strip()
        if crop_text:
            parts.append(crop_text)
            stats["crop_preferred_field_count"] += 1
            stats[f"crop_preferred_{field_name}"] += 1
        elif full_text.strip():
            parts.append(full_text)
            stats["full_fallback_field_count"] += 1
            stats[f"full_fallback_{field_name}"] += 1
        else:
            stats["empty_field_count"] += 1
            stats[f"empty_{field_name}"] += 1
    return " ".join(parts), stats


def main(argv: list[str] | None = None) -> int:
    """Run detector ROI plus full-image fallback evaluator."""
    args = parse_args(argv)
    profile = PROFILES[args.profile]
    det_model = args.det_model or profile["det"]
    rec_model = args.rec_model or profile["rec"]
    max_side = args.max_side or profile["max_side"]
    if not args.apply:
        print(
            json.dumps(
                {
                    "apply_requested": False,
                    "eval_split": args.eval_split,
                    "detector_model_artifact": args.model.name,
                    "profile": args.profile,
                    "mode": "detector_roi_full_fallback",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    results = evaluate(
        source_bundle=args.source_bundle,
        splits=args.splits,
        eval_split=args.eval_split,
        model_path=args.model,
        limit=args.limit,
        det_model=det_model,
        rec_model=rec_model,
        max_side=max_side,
        det_box_thresh=args.det_box_thresh,
        det_thresh=args.det_thresh,
        det_unclip_ratio=args.det_unclip_ratio,
        rec_model_dir=args.rec_model_dir,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        crop_pad=args.crop_pad,
        min_section_area_ratio=args.min_section_area_ratio,
        predicted_boxes_jsonl=args.predicted_boxes_jsonl,
        preprocess_mode=args.preprocess_mode,
    )
    observations = results.pop("observations")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.observations_output is not None:
        args.observations_output.parent.mkdir(parents=True, exist_ok=True)
        args.observations_output.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in observations),
            encoding="utf-8",
        )
    print(
        json.dumps(
            {key: value for key, value in results.items() if key != "per_image"},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
