"""Mine experimental other-ingredients pseudo-labels with PaddleOCR.

This worker script scans candidate images with PaddleOCR and proposes a single
section-level ``other_ingredients`` box only when an explicit heading keyword is
recognized. The output is intentionally experimental:

* ``machine_proposed`` labels are marked ``human_reviewed=false``.
* ``promotion_allowed=false`` prevents treating these boxes as production-valid.
* Raw OCR text and provider payloads are never written.

References:
    https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

SCHEMA_VERSION = "other-ingredients-machine-proposals-v2"
SUMMARY_SCHEMA_VERSION = "other-ingredients-machine-proposal-summary-v2"
TARGET_CLASS = "other_ingredients"
TARGET_CLASS_ID = 6
POLYGON_MIN_POINT_LENGTH = 2
SOURCE_DOC_URLS = ("https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html",)

KEYWORD_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("other_ingredients_en", re.compile(r"\bother\s+ingredients?\b", re.IGNORECASE)),
    ("inactive_ingredients_en", re.compile(r"\binactive\s+ingredients?\b", re.IGNORECASE)),
    (
        "non_medicinal_ingredients_en",
        re.compile(r"\bnon[-\s]?medicinal\s+ingredients?\b", re.IGNORECASE),
    ),
    ("korean_other_ingredients", re.compile(r"(기타\s*원료|기타\s*성분|부\s*원료|부\s*성분)")),
)
STOP_HEADING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsupplement\s+facts\b", re.IGNORECASE),
    re.compile(r"\bdirections?\b|\bsuggested\s+use\b|\bserving\s+size\b", re.IGNORECASE),
    re.compile(r"\bwarning\b|\bcaution\b|\ballergen\b", re.IGNORECASE),
    re.compile(r"(섭취|주의|알레르기|영양|원재료명)"),
)


class ProposalScanError(ValueError):
    """Raised when proposal scan input or output is unsafe."""


@dataclass(frozen=True)
class OCRLine:
    """One OCR text line and normalized polygon bounds.

    Args:
        text: OCR text in memory only.
        score: Optional bounded OCR confidence.
        x0: Normalized left coordinate.
        y0: Normalized top coordinate.
        x1: Normalized right coordinate.
        y1: Normalized bottom coordinate.
    """

    text: str
    score: float | None
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def x_center(self) -> float:
        """Return normalized x center."""
        return (self.x0 + self.x1) / 2

    @property
    def y_center(self) -> float:
        """Return normalized y center."""
        return (self.y0 + self.y1) / 2


@dataclass(frozen=True)
class ProposalBox:
    """Normalized proposal box in corner format."""

    x0: float
    y0: float
    x1: float
    y1: float

    def to_yolo(self) -> dict[str, float]:
        """Return normalized YOLO xywh geometry.

        Returns:
            Rounded normalized xywh mapping.
        """
        return {
            "x_center": round((self.x0 + self.x1) / 2, 6),
            "y_center": round((self.y0 + self.y1) / 2, 6),
            "width": round(max(0.0, self.x1 - self.x0), 6),
            "height": round(max(0.0, self.y1 - self.y0), 6),
            "area": round(max(0.0, self.x1 - self.x0) * max(0.0, self.y1 - self.y0), 6),
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument list for tests.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--image-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--device", default="gpu:0")
    parser.add_argument("--det-model", default="PP-OCRv5_server_det")
    parser.add_argument("--rec-model", default="korean_PP-OCRv5_mobile_rec")
    parser.add_argument("--max-side", type=int, default=3072)
    parser.add_argument("--det-box-thresh", type=float, default=0.3)
    parser.add_argument("--det-thresh", type=float, default=0.2)
    parser.add_argument("--det-unclip-ratio", type=float, default=2.0)
    parser.add_argument("--follow-window", type=float, default=0.16)
    parser.add_argument("--max-follow-lines", type=int, default=5)
    parser.add_argument("--panel-padding", type=float, default=0.012)
    parser.add_argument("--min-proposals", type=int, default=18)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the PaddleOCR proposal scanner.

    Args:
        argv: Optional argument list for tests.
    """
    args = parse_args(argv)
    try:
        result = scan_proposals(
            manifest_path=args.manifest,
            image_dir=args.image_dir,
            limit=args.limit,
            device=args.device,
            det_model=args.det_model,
            rec_model=args.rec_model,
            max_side=args.max_side,
            det_box_thresh=args.det_box_thresh,
            det_thresh=args.det_thresh,
            det_unclip_ratio=args.det_unclip_ratio,
            follow_window=args.follow_window,
            max_follow_lines=args.max_follow_lines,
            panel_padding=args.panel_padding,
            min_proposals=args.min_proposals,
        )
        _write_json(args.output, result)
        print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
    except (ProposalScanError, OSError, json.JSONDecodeError) as exc:
        failure = {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "absolute_paths_stored": False,
        }
        _write_json(args.output, {"summary": failure, "proposals": [], "failures": []})
        print(json.dumps(failure, ensure_ascii=False, sort_keys=True))
        raise SystemExit(1) from None


def scan_proposals(
    *,
    manifest_path: Path,
    image_dir: Path,
    limit: int,
    device: str | None,
    det_model: str,
    rec_model: str,
    max_side: int,
    det_box_thresh: float,
    det_thresh: float,
    det_unclip_ratio: float,
    follow_window: float,
    max_follow_lines: int,
    panel_padding: float,
    min_proposals: int,
) -> dict[str, Any]:
    """Scan candidate images and return redacted pseudo-label proposals.

    Args:
        manifest_path: Candidate manifest file.
        image_dir: Directory containing candidate images.
        limit: Optional scan cap. ``0`` means all.
        device: PaddleOCR device such as ``gpu:0`` or ``cpu``.
        det_model: PaddleOCR text detection model name.
        rec_model: PaddleOCR text recognition model name.
        max_side: Maximum image side for text detection.
        det_box_thresh: PaddleOCR detection box threshold.
        det_thresh: PaddleOCR detection pixel threshold.
        det_unclip_ratio: PaddleOCR detection box expansion ratio.
        follow_window: Normalized vertical window for continuation lines.
        max_follow_lines: Maximum continuation lines to union.
        panel_padding: Normalized padding added to proposal boxes.
        min_proposals: Minimum proposal count needed to unblock merge.

    Returns:
        Redacted proposal artifact.

    Raises:
        ProposalScanError: If manifest shape or thresholds are invalid.
    """
    _validate_thresholds(
        limit=limit,
        max_side=max_side,
        follow_window=follow_window,
        max_follow_lines=max_follow_lines,
        panel_padding=panel_padding,
        min_proposals=min_proposals,
    )
    manifest = _load_manifest(manifest_path)
    items = manifest["items"]
    if limit:
        items = items[:limit]
    ocr = _build_ocr(
        device=device,
        det_model=det_model,
        rec_model=rec_model,
        max_side=max_side,
        det_box_thresh=det_box_thresh,
        det_thresh=det_thresh,
        det_unclip_ratio=det_unclip_ratio,
    )
    proposals: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for item in items:
        image_path = image_dir / _string_field(item, "image_filename")
        if not image_path.is_file():
            failures.append(_failure(item, "image_missing"))
            continue
        lines = _predict_lines(ocr, image_path)
        proposal = _proposal_for_item(
            item,
            lines=lines,
            follow_window=follow_window,
            max_follow_lines=max_follow_lines,
            panel_padding=panel_padding,
        )
        if proposal is None:
            failures.append(_failure(item, "explicit_keyword_not_found"))
            continue
        proposals.append(proposal)
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "ready_for_experimental_merge"
        if len(proposals) >= min_proposals
        else "blocked_not_enough_visible_other_ingredients",
        "target_class": TARGET_CLASS,
        "candidate_count": manifest.get("candidate_count"),
        "scanned_count": len(items),
        "proposal_count": len(proposals),
        "failure_count": len(failures),
        "minimum_needed": min_proposals,
        "human_reviewed": False,
        "machine_proposed": True,
        "promotion_allowed": False,
        "source_doc_urls": list(SOURCE_DOC_URLS),
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
        "matched_keyword_lines_stored": False,
    }
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "summary": summary,
        "proposals": proposals,
        "failures": failures,
    }
    _assert_redacted(artifact)
    return artifact


def _build_ocr(
    *,
    device: str | None,
    det_model: str,
    rec_model: str,
    max_side: int,
    det_box_thresh: float,
    det_thresh: float,
    det_unclip_ratio: float,
) -> Any:
    """Construct a PaddleOCR pipeline with explicit GPU/device settings."""
    from paddleocr import PaddleOCR  # noqa: PLC0415

    kwargs: dict[str, Any] = {
        "lang": "korean",
        "use_textline_orientation": False,
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "text_detection_model_name": det_model,
        "text_recognition_model_name": rec_model,
        "text_det_limit_side_len": max_side,
        "text_det_limit_type": "max",
        "text_det_box_thresh": det_box_thresh,
        "text_det_thresh": det_thresh,
        "text_det_unclip_ratio": det_unclip_ratio,
    }
    if device:
        kwargs["device"] = device
    return PaddleOCR(**kwargs)


def _predict_lines(ocr: Any, image_path: Path) -> list[OCRLine]:
    """Run PaddleOCR and return in-memory OCR lines with normalized geometry."""
    with Image.open(image_path) as image:
        image_width, image_height = image.size
    prediction = ocr.predict(str(image_path))
    mapping = _first_prediction_mapping(prediction)
    texts = mapping.get("rec_texts")
    scores = mapping.get("rec_scores")
    polys = mapping.get("rec_polys") or mapping.get("dt_polys") or mapping.get("polys")
    if not isinstance(texts, list) or not isinstance(polys, list):
        return []
    lines: list[OCRLine] = []
    for index, text in enumerate(texts):
        if not isinstance(text, str) or not text.strip() or index >= len(polys):
            continue
        score = scores[index] if isinstance(scores, list) and index < len(scores) else None
        lines.append(
            _line_from_poly(
                text=text,
                score=score if isinstance(score, int | float) else None,
                poly=polys[index],
                image_width=image_width,
                image_height=image_height,
            )
        )
    return sorted(lines, key=lambda line: (line.y0, line.x0))


def _proposal_for_item(
    item: dict[str, Any],
    *,
    lines: list[OCRLine],
    follow_window: float,
    max_follow_lines: int,
    panel_padding: float,
) -> dict[str, Any] | None:
    """Return one redacted proposal for a candidate item."""
    for index, line in enumerate(lines):
        bucket = _keyword_bucket(line.text)
        if bucket is None:
            continue
        selected = [line]
        anchor_y = line.y_center
        for candidate in lines[index + 1 :]:
            if len(selected) >= max_follow_lines + 1:
                break
            if candidate.y_center - anchor_y > follow_window:
                break
            if _is_stop_heading(candidate.text) and selected:
                break
            if candidate.y0 >= line.y0:
                selected.append(candidate)
        box = _union_lines(selected, padding=panel_padding)
        yolo = box.to_yolo()
        if yolo["width"] <= 0 or yolo["height"] <= 0:
            return None
        return {
            "source_ref": _string_field(item, "source_ref"),
            "source_ref_hash": _string_field(item, "source_ref_hash"),
            "fixture_id": _string_field(item, "fixture_id"),
            "split": item.get("split", "train"),
            "target_class": TARGET_CLASS,
            "class_id": TARGET_CLASS_ID,
            "label": {
                "class_id": TARGET_CLASS_ID,
                "label": TARGET_CLASS,
                "x_center": yolo["x_center"],
                "y_center": yolo["y_center"],
                "width": yolo["width"],
                "height": yolo["height"],
            },
            "box_area": yolo["area"],
            "line_count": len(selected),
            "match_bucket": bucket,
            "machine_proposed": True,
            "human_reviewed": False,
            "promotion_allowed": False,
            "raw_ocr_text_stored": False,
        }
    return None


def _line_from_poly(
    *,
    text: str,
    score: float | None,
    poly: object,
    image_width: int,
    image_height: int,
) -> OCRLine:
    """Convert PaddleOCR polygon output to a normalized line."""
    points = _poly_points(poly)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    if not xs or not ys:
        raise ProposalScanError("OCR polygon is empty.")
    return OCRLine(
        text=text,
        score=score if score is not None and 0 <= score <= 1 else None,
        x0=_clip(min(xs) / image_width),
        y0=_clip(min(ys) / image_height),
        x1=_clip(max(xs) / image_width),
        y1=_clip(max(ys) / image_height),
    )


def _poly_points(poly: object) -> list[tuple[float, float]]:
    """Return numeric points from common list/numpy polygon shapes."""
    tolist = getattr(poly, "tolist", None)
    if callable(tolist):
        poly = tolist()
    if not isinstance(poly, list):
        raise ProposalScanError("OCR polygon must be a list-like value.")
    points: list[tuple[float, float]] = []
    for point in poly:
        if not isinstance(point, list | tuple) or len(point) < POLYGON_MIN_POINT_LENGTH:
            continue
        x, y = point[0], point[1]
        if isinstance(x, int | float) and isinstance(y, int | float):
            points.append((float(x), float(y)))
    return points


def _union_lines(lines: list[OCRLine], *, padding: float) -> ProposalBox:
    """Return a padded normalized union of OCR line boxes."""
    return ProposalBox(
        x0=_clip(min(line.x0 for line in lines) - padding),
        y0=_clip(min(line.y0 for line in lines) - padding),
        x1=_clip(max(line.x1 for line in lines) + padding),
        y1=_clip(max(line.y1 for line in lines) + padding),
    )


def _keyword_bucket(text: str) -> str | None:
    """Return the explicit keyword bucket for one OCR line."""
    normalized = " ".join(text.strip().split())
    for bucket, pattern in KEYWORD_PATTERNS:
        if pattern.search(normalized):
            return bucket
    return None


def _is_stop_heading(text: str) -> bool:
    """Return whether a continuation line looks like a new section heading."""
    normalized = " ".join(text.strip().split())
    return any(pattern.search(normalized) for pattern in STOP_HEADING_PATTERNS)


def _first_prediction_mapping(prediction: object) -> dict[str, Any]:
    """Return the first PaddleOCR prediction as a mapping."""
    first: object | None = None
    if isinstance(prediction, list | tuple) and prediction:
        first = prediction[0]
    elif isinstance(prediction, dict):
        first = prediction
    if isinstance(first, dict):
        return first
    for method_name in ("json", "to_dict"):
        method = getattr(first, method_name, None)
        if callable(method):
            value = method()
            if isinstance(value, dict):
                return value
    return {}


def _load_manifest(path: Path) -> dict[str, Any]:
    """Load and validate candidate manifest."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProposalScanError("manifest must be a JSON object.")
    items = payload.get("items")
    if not isinstance(items, list):
        raise ProposalScanError("manifest items must be a list.")
    payload["items"] = items
    return payload


def _failure(item: dict[str, Any], reason: str) -> dict[str, Any]:
    """Build one redacted failure row."""
    return {
        "source_ref_hash": item.get("source_ref_hash"),
        "fixture_id": item.get("fixture_id"),
        "reason": reason,
    }


def _string_field(row: dict[str, Any], key: str) -> str:
    """Return one required string field."""
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProposalScanError(f"{key} must be a non-empty string.")
    return value


def _validate_thresholds(
    *,
    limit: int,
    max_side: int,
    follow_window: float,
    max_follow_lines: int,
    panel_padding: float,
    min_proposals: int,
) -> None:
    """Validate scan thresholds before loading models."""
    if limit < 0 or max_side <= 0 or max_follow_lines < 0 or min_proposals < 0:
        raise ProposalScanError("integer thresholds must be non-negative.")
    for name, value in {"follow_window": follow_window, "panel_padding": panel_padding}.items():
        if not math.isfinite(value) or value < 0 or value > 1:
            raise ProposalScanError(f"{name} must be in the normalized 0..1 range.")


def _clip(value: float) -> float:
    """Clip a normalized coordinate."""
    return min(1.0, max(0.0, value))


def _write_json(path: Path, payload: object) -> None:
    """Write JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _assert_redacted(payload: object) -> None:
    """Reject raw OCR text, provider payloads, and absolute paths in output."""
    dumped = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    forbidden_markers = (
        "/Users/",
        "/Volumes/",
        "/private/",
        "\\Users\\",
        "file://",
        '"matched_keyword_lines":',
        '"rec_texts"',
        '"rec_polys"',
        '"provider_payload"',
        '"raw_ocr_text":',
    )
    matches = [marker for marker in forbidden_markers if marker in dumped]
    if matches:
        raise ProposalScanError(
            "proposal artifact contains unsafe raw data marker: "
            f"{matches[0]}"
        )


if __name__ == "__main__":
    main()
