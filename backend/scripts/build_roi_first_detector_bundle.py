"""Build an ROI-first eval bundle from a trained section detector.

The bundle mirrors ``build_roi_first_oracle_bundle`` but replaces CLOVA/teacher
boxes with predictions from a trained Ultralytics detector. It writes cropped
images plus the original reviewed ``ground-truth.todo.jsonl`` rows so the existing
``paddleocr_clova_eval.py`` and structured gate can score the detector-driven
ROI-first path without storing raw OCR text or provider payloads.

Ultralytics reference:
    https://docs.ultralytics.com/modes/predict/
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

CROP_PAD = 16
CLASS_NAMES = (
    "product_identity",
    "supplement_facts",
    "ingredient_amounts",
    "precautions",
    "allergen_warning",
    "intake_method",
    "other_ingredients",
    "functional_claims",
)
GT_TO_SECTION = {
    "ingredients": "ingredient_amounts",
    "intake_method": "intake_method",
    "precautions": "precautions",
    "allergen_warnings": "allergen_warning",
    "functional_claims": "functional_claims",
    "product_name": "product_identity",
    "manufacturer": "product_identity",
}
SUPPORTED_SECTION_POLICIES = frozenset({"all", "expected"})


def _holdout_fixtures(splits: Path, eval_split: str) -> set[str]:
    """Return fixture ids for the requested split.

    Args:
        splits: Line-delimited split assignment JSON file.
        eval_split: Split name to select, typically ``holdout``.

    Returns:
        Set of fixture ids assigned to the requested split.
    """
    out: set[str] = set()
    for line in splits.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("split") == eval_split and row.get("fixture_id"):
            out.add(str(row["fixture_id"]))
    return out


def _ready_rows(bundle_dir: Path, fixture_ids: set[str]) -> list[dict[str, Any]]:
    """Return benchmark-ready GT rows for the selected fixture ids.

    Args:
        bundle_dir: Source ground-truth bundle with ``ground-truth.todo.jsonl``.
        fixture_ids: Fixture ids allowed by split assignment.

    Returns:
        Rows with reviewed structured GT and relative image paths.
    """
    rows = [
        json.loads(line)
        for line in (bundle_dir / "ground-truth.todo.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [
        row
        for row in rows
        if row.get("fixture_id") in fixture_ids
        and row.get("ready_for_benchmark_after_review") is True
        and isinstance(row.get("expected"), dict)
        and row.get("image_path")
    ]


def _expected_sections(expected: dict[str, Any]) -> set[str]:
    """Return section class names implied by non-empty structured GT fields.

    Args:
        expected: Reviewed structured GT object.

    Returns:
        Set of detector section names. Falls back to ``ingredient_amounts`` when
        the GT object has no mapped fields.
    """
    sections: set[str] = set()
    for key, section in GT_TO_SECTION.items():
        value = expected.get(key)
        if (isinstance(value, list | dict) and value) or (isinstance(value, str) and value.strip()):
            sections.add(section)
    return sections or {"ingredient_amounts"}


def _predict_boxes(
    *,
    model: Any,
    image_path: Path,
    imgsz: int,
    conf: float,
    iou: float,
    device: str,
) -> list[dict[str, Any]]:
    """Run detector prediction and return sanitized pixel boxes.

    Args:
        model: Ultralytics ``YOLO`` model.
        image_path: Image to predict.
        imgsz: Inference image size.
        conf: Confidence threshold.
        iou: NMS IoU threshold.
        device: Ultralytics device string.

    Returns:
        List of sanitized box dictionaries with class name, confidence, and
        ``xyxy`` pixel coordinates.
    """
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
        cls_id = int(cls_value)
        class_name = str(names.get(cls_id, CLASS_NAMES[cls_id] if 0 <= cls_id < len(CLASS_NAMES) else cls_id))
        out.append(
            {
                "class_id": cls_id,
                "class_name": class_name,
                "confidence": round(float(conf_value), 4),
                "xyxy": [round(float(v), 2) for v in coords],
            }
        )
    return out


def _crop_or_fallback(
    *,
    source: Path,
    destination: Path,
    boxes: list[dict[str, Any]],
) -> tuple[str, float | None]:
    """Crop source image to the union of predicted boxes, or copy full image.

    Args:
        source: Source image path.
        destination: Destination image path.
        boxes: Filtered predicted boxes.

    Returns:
        Tuple of ``(mode, crop_area_ratio)``. Mode is ``cropped`` or
        ``fallback_full_image``.
    """
    with Image.open(source) as raw:
        rgb = raw.convert("RGB")
        width, height = rgb.size
        if not boxes:
            rgb.save(destination, quality=92)
            return "fallback_full_image", None
        x0 = max(0, int(min(box["xyxy"][0] for box in boxes)) - CROP_PAD)
        y0 = max(0, int(min(box["xyxy"][1] for box in boxes)) - CROP_PAD)
        x1 = min(width, int(max(box["xyxy"][2] for box in boxes)) + CROP_PAD)
        y1 = min(height, int(max(box["xyxy"][3] for box in boxes)) + CROP_PAD)
        if x1 <= x0 or y1 <= y0:
            rgb.save(destination, quality=92)
            return "fallback_full_image", None
        rgb.crop((x0, y0, x1, y1)).save(destination, quality=92)
        return "cropped", ((x1 - x0) * (y1 - y0)) / (width * height)


def build_bundle(
    *,
    source_bundle: Path,
    splits: Path,
    eval_split: str,
    model_path: Path,
    output_bundle: Path,
    imgsz: int,
    conf: float,
    iou: float,
    device: str,
    section_policy: str,
) -> dict[str, Any]:
    """Build a detector-cropped ROI-first evaluation bundle.

    Args:
        source_bundle: Full-image reviewed GT bundle.
        splits: Split assignment JSONL.
        eval_split: Split to evaluate.
        model_path: Trained section detector weights.
        output_bundle: Destination bundle directory.
        imgsz: Ultralytics inference image size.
        conf: Confidence threshold.
        iou: NMS IoU threshold.
        device: Ultralytics device string.
        section_policy: ``all`` uses every predicted section box; ``expected``
            keeps only classes mapped from the structured GT. ``all`` is closer
            to production because it avoids using GT to choose sections.

    Returns:
        Redacted summary artifact.
    """
    if section_policy not in SUPPORTED_SECTION_POLICIES:
        raise ValueError(f"unsupported section_policy={section_policy}")
    from ultralytics import YOLO  # noqa: PLC0415

    fixture_ids = _holdout_fixtures(splits, eval_split)
    rows = _ready_rows(source_bundle, fixture_ids)
    if output_bundle.exists():
        shutil.rmtree(output_bundle)
    (output_bundle / "images").mkdir(parents=True, exist_ok=True)

    model = YOLO(str(model_path))
    kept_rows: list[dict[str, Any]] = []
    stats = {
        "fixtures": 0,
        "cropped": 0,
        "fallback_full_image": 0,
        "failed": 0,
        "predicted_boxes_total": 0,
        "kept_boxes_total": 0,
        "crop_area_ratio_sum": 0.0,
    }
    class_counts: dict[str, int] = {}
    for row in rows:
        image_rel = Path(str(row["image_path"]))
        source = source_bundle / image_rel
        destination = output_bundle / "images" / image_rel.name
        try:
            predicted = _predict_boxes(model=model, image_path=source, imgsz=imgsz, conf=conf, iou=iou, device=device)
            stats["predicted_boxes_total"] += len(predicted)
            if section_policy == "expected":
                allowed = _expected_sections(row["expected"])
                kept = [box for box in predicted if box["class_name"] in allowed]
            else:
                kept = predicted
            stats["kept_boxes_total"] += len(kept)
            for box in kept:
                name = str(box["class_name"])
                class_counts[name] = class_counts.get(name, 0) + 1
            mode, area_ratio = _crop_or_fallback(source=source, destination=destination, boxes=kept)
            stats[mode] += 1
            if area_ratio is not None:
                stats["crop_area_ratio_sum"] += area_ratio
            kept_row = dict(row)
            kept_row["image_path"] = f"images/{image_rel.name}"
            kept_rows.append(kept_row)
            stats["fixtures"] += 1
        except Exception:
            stats["failed"] += 1

    with (output_bundle / "ground-truth.todo.jsonl").open("w", encoding="utf-8") as handle:
        for row in kept_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {
        "schema_version": "roi-first-detector-bundle-summary-v1",
        "eval_split": eval_split,
        "section_policy": section_policy,
        "model_artifact": model_path.name,
        "imgsz": imgsz,
        "conf": conf,
        "iou": iou,
        "device": device,
        "fixtures": stats["fixtures"],
        "cropped": stats["cropped"],
        "fallback_full_image": stats["fallback_full_image"],
        "failed": stats["failed"],
        "predicted_boxes_total": stats["predicted_boxes_total"],
        "kept_boxes_total": stats["kept_boxes_total"],
        "kept_boxes_by_class": dict(sorted(class_counts.items())),
        "mean_crop_area_ratio": (
            round(stats["crop_area_ratio_sum"] / stats["cropped"], 4) if stats["cropped"] else None
        ),
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
    }
    (output_bundle / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    """Run the detector ROI bundle builder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-bundle", required=True, type=Path)
    parser.add_argument("--splits", required=True, type=Path)
    parser.add_argument("--eval-split", default="holdout")
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output-bundle", required=True, type=Path)
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--conf", type=float, default=0.05)
    parser.add_argument("--iou", type=float, default=0.7)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--section-policy", choices=sorted(SUPPORTED_SECTION_POLICIES), default="all")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print(
            json.dumps(
                {
                    "apply_requested": False,
                    "source_bundle": str(args.source_bundle),
                    "model_artifact": args.model.name,
                    "section_policy": args.section_policy,
                },
                ensure_ascii=False,
            )
        )
        return 0
    summary = build_bundle(
        source_bundle=args.source_bundle,
        splits=args.splits,
        eval_split=args.eval_split,
        model_path=args.model,
        output_bundle=args.output_bundle,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        section_policy=args.section_policy,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
