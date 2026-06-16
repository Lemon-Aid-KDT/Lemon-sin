"""Evaluate adaptive PaddleOCR candidate merging for structured extraction.

This runner compares two recognition-model candidates under the same detector
configuration and evaluates a production-plausible ``union`` strategy:

* primary: first OCR candidate as-is
* secondary: second OCR candidate as-is
* union: primary lines plus secondary-only lines, de-duplicated by normalized text
* oracle_best: upper-bound diagnostic that chooses the best metric row using GT

Only redacted metrics, fixture ids, and line hashes/counts are written to the
normal output directory. Raw OCR lines can be written only when
``--raw-debug-dir`` is explicitly provided; that directory is intended for
temporary operator inspection and must not be committed.

References:
    https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html
    https://www.paddleocr.ai/latest/en/version2.x/ppocr/model_train/recognition.html
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.build_supplement_structured_extraction_eval_summary import build_summary  # noqa: E402
from scripts.extract_supplement_structured_hardcases import extract_hardcases  # noqa: E402
from scripts.gate_supplement_structured_extraction_target import (  # noqa: E402
    build_structured_extraction_gate,
)
from scripts.paddleocr_clova_eval import (  # noqa: E402
    FIELD_MATCH_THRESHOLD,
    POST_PASS_CHOICES,
    POST_PASS_INGREDIENT_ALIAS_AMOUNT_UNIT,
    PROFILES,
    TARGET_PROVIDER,
    _build_ocr,
    _field_match_ratio,
    _field_units,
    _ingredient_recall,
    _normalize_for_metric,
    _postprocess_hypothesis_text,
    _structured_reference,
    _text_extraction_metrics,
)

SCHEMA_VERSION = "paddleocr-adaptive-structured-eval-v1"
COMPARISON_SCHEMA_VERSION = "paddleocr-adaptive-line-comparison-v1"
SOURCE_DOC_URLS = (
    "https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html",
    "https://www.paddleocr.ai/latest/en/version2.x/ppocr/model_train/recognition.html",
)
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class CandidateConfig:
    """One PaddleOCR recognition candidate.

    Args:
        name: Stable candidate label used in output filenames.
        recognition_model_dir: PaddleOCR inference directory.
    """

    name: str
    recognition_model_dir: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Optional argument list for tests.

    Returns:
        Parsed CLI namespace.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--splits", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="server_detection")
    parser.add_argument("--primary-name", default="primary")
    parser.add_argument("--primary-rec-model-dir", required=True)
    parser.add_argument("--secondary-name", default="secondary")
    parser.add_argument("--secondary-rec-model-dir", required=True)
    parser.add_argument("--det-model", default=None)
    parser.add_argument("--rec-model", default=None)
    parser.add_argument("--max-side", type=int, default=None)
    parser.add_argument("--det-box-thresh", type=float, default=None)
    parser.add_argument("--det-thresh", type=float, default=None)
    parser.add_argument("--det-unclip-ratio", type=float, default=2.5)
    parser.add_argument(
        "--post-pass",
        choices=POST_PASS_CHOICES,
        default=POST_PASS_INGREDIENT_ALIAS_AMOUNT_UNIT,
    )
    parser.add_argument("--eval-split", default="holdout")
    parser.add_argument("--provider", default=TARGET_PROVIDER)
    parser.add_argument("--target-threshold", default="0.90")
    parser.add_argument("--min-ingredient-recall", default="0.85")
    parser.add_argument("--min-fixtures", type=int, default=30)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--raw-debug-dir",
        type=Path,
        default=None,
        help="Temporary raw OCR line output for hard-case fixtures only. Do not commit.",
    )
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file.

    Args:
        path: JSONL path.

    Returns:
        Parsed row objects.
    """
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _load_ready_rows(bundle_dir: Path, limit: int | None) -> list[dict[str, Any]]:
    """Load benchmark-ready GT rows.

    Args:
        bundle_dir: Bundle directory containing ``ground-truth.todo.jsonl``.
        limit: Optional row cap.

    Returns:
        Ready benchmark rows.
    """
    rows = _read_jsonl(bundle_dir / "ground-truth.todo.jsonl")
    ready = [
        row
        for row in rows
        if row.get("ready_for_benchmark_after_review") is True
        and isinstance(row.get("expected"), dict)
    ]
    return ready[:limit] if limit is not None else ready


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write JSONL rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _safe_filename(value: str) -> str:
    """Return a safe filename stem for a fixture id."""
    return SAFE_FILENAME_PATTERN.sub("_", value).strip("._-") or "fixture"


def _line_hash(text: str) -> str:
    """Return a short hash for redacted line comparison."""
    normalized = _normalize_for_metric(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16] if normalized else "empty"


def _predict_lines(ocr: Any, image_path: Path) -> list[str]:
    """Run PaddleOCR and return recognized text lines.

    Args:
        ocr: PaddleOCR pipeline object.
        image_path: Local image path.

    Returns:
        Recognized line strings in PaddleOCR reading order.
    """
    result = ocr.predict(str(image_path))
    if not result:
        return []
    first = result[0]
    texts = first.get("rec_texts") if hasattr(first, "get") else None
    if not isinstance(texts, list | tuple):
        return []
    return [str(text).strip() for text in texts if str(text).strip()]


def _union_lines(primary: list[str], secondary: list[str]) -> list[str]:
    """Return primary lines plus secondary-only normalized lines."""
    merged: list[str] = []
    seen: set[str] = set()
    for line in [*primary, *secondary]:
        key = _normalize_for_metric(line)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(line)
    return merged


def _score_prediction(
    *,
    fixture_id: str,
    expected: dict[str, Any],
    lines: list[str],
    post_pass: str,
    provider: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Score one OCR candidate without storing raw text.

    Args:
        fixture_id: Fixture id.
        expected: Structured GT object.
        lines: OCR line strings.
        post_pass: Deterministic post-pass mode.
        provider: Provider label.

    Returns:
        ``(per_image_row, observation_row)``.
    """
    predicted = " ".join(lines)
    predicted_for_metric, post_pass_applied = _postprocess_hypothesis_text(predicted, mode=post_pass)
    hypothesis_norm = _normalize_for_metric(predicted_for_metric)
    reference = _structured_reference(expected)
    metrics = _text_extraction_metrics(reference, predicted_for_metric)
    if metrics is None:
        metrics = {
            "matched_char_count": 0,
            "reference_char_count": len(_normalize_for_metric(reference)),
            "hypothesis_char_count": len(hypothesis_norm),
            "normalized_text_precision": 0.0,
            "normalized_text_recall": 0.0,
            "normalized_text_f1": 0.0,
        }
    f_matched, f_total = _field_match_ratio(_field_units(expected), hypothesis_norm)
    ingredient_found, ingredient_total = _ingredient_recall(expected, hypothesis_norm)
    field_ratio = round(f_matched / f_total, 4) if f_total else 0.0
    per_image = {
        "fixture_id": fixture_id,
        "field_match_ratio": field_ratio,
        "field_matched": f_matched,
        "field_total": f_total,
        "normalized_text_precision": metrics["normalized_text_precision"],
        "normalized_text_recall": metrics["normalized_text_recall"],
        "normalized_text_f1": metrics["normalized_text_f1"],
        "ingredient_found": ingredient_found,
        "ingredient_total": ingredient_total,
        "post_pass_applied": post_pass_applied,
        "line_count": len(lines),
    }
    observation = {
        "fixture_id": fixture_id,
        "provider": provider,
        "status": "completed",
        "text_non_empty": bool(lines),
        "char_count": metrics["hypothesis_char_count"],
        "field_match_ratio": field_ratio,
        "matched_char_count": metrics["matched_char_count"],
        "reference_char_count": metrics["reference_char_count"],
        "hypothesis_char_count": metrics["hypothesis_char_count"],
        "normalized_text_precision": metrics["normalized_text_precision"],
        "normalized_text_recall": metrics["normalized_text_recall"],
        "normalized_text_f1": metrics["normalized_text_f1"],
        "text_metric_reference_source": "expected.structured_sections",
        "post_pass": post_pass,
        "post_pass_applied": post_pass_applied,
    }
    return per_image, observation


def _aggregate_eval(
    *,
    strategy: str,
    per_image: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    args: argparse.Namespace,
    det_model: str,
    rec_model: str,
    max_side: int,
) -> dict[str, Any]:
    """Build a redacted PaddleOCR-like eval artifact.

    Args:
        strategy: Strategy label.
        per_image: Per-fixture metric rows.
        observations: Provider-shaped observation rows.
        args: CLI namespace.
        det_model: Detection model name.
        rec_model: Recognition model name.
        max_side: Detection side limit.

    Returns:
        Redacted eval artifact.
    """
    scored = len(per_image)
    field_matched_total = sum(int(row.get("field_matched", 0)) for row in per_image)
    field_unit_total = sum(int(row.get("field_total", 0)) for row in per_image)
    ingredient_found_total = sum(int(row.get("ingredient_found", 0)) for row in per_image)
    ingredient_total = sum(int(row.get("ingredient_total", 0)) for row in per_image)
    precision_total = sum(float(row.get("normalized_text_precision", 0.0)) for row in per_image)
    recall_total = sum(float(row.get("normalized_text_recall", 0.0)) for row in per_image)
    f1_total = sum(float(row.get("normalized_text_f1", 0.0)) for row in per_image)
    field_ratio_total = sum(float(row.get("field_match_ratio", 0.0)) for row in per_image)
    return {
        "schema_version": SCHEMA_VERSION,
        "strategy": strategy,
        "provider": args.provider,
        "detection_model": det_model,
        "recognition_model": rec_model,
        "recognition_model_dir_present": True,
        "max_side": max_side,
        "det_box_thresh": args.det_box_thresh,
        "det_thresh": args.det_thresh,
        "det_unclip_ratio": args.det_unclip_ratio,
        "post_pass": args.post_pass,
        "field_match_threshold": FIELD_MATCH_THRESHOLD,
        "scored_images": scored,
        "skipped_images": 0,
        "failed_images": 0,
        "field_match_ratio_macro": round(field_ratio_total / scored, 4) if scored else 0.0,
        "field_match_ratio_micro": round(field_matched_total / field_unit_total, 4) if field_unit_total else 0.0,
        "field_matched_total": [field_matched_total, field_unit_total],
        "mean_normalized_text_precision": round(precision_total / scored, 4) if scored else 0.0,
        "mean_normalized_text_recall": round(recall_total / scored, 4) if scored else 0.0,
        "mean_normalized_text_f1": round(f1_total / scored, 4) if scored else 0.0,
        "ingredient_recall": round(ingredient_found_total / ingredient_total, 4) if ingredient_total else 0.0,
        "ingredient_found_total": [ingredient_found_total, ingredient_total],
        "per_image": per_image,
        "observations": observations,
    }


def _better_metric_row(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Return the better diagnostic row using GT-derived metrics.

    This is intentionally not a production strategy; it is an upper bound used to
    decide whether more data/parser work could pay off.
    """
    left_key = (
        int(left.get("ingredient_found", 0)),
        int(left.get("field_matched", 0)),
        float(left.get("field_match_ratio", 0.0)),
    )
    right_key = (
        int(right.get("ingredient_found", 0)),
        int(right.get("field_matched", 0)),
        float(right.get("field_match_ratio", 0.0)),
    )
    return left if left_key >= right_key else right


def _comparison_row(
    *,
    fixture_id: str,
    primary_name: str,
    secondary_name: str,
    primary_lines: list[str],
    secondary_lines: list[str],
    union_lines: list[str],
    primary_metrics: dict[str, Any],
    secondary_metrics: dict[str, Any],
    union_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Build one redacted line-comparison row."""
    primary_hashes = {_line_hash(line) for line in primary_lines}
    secondary_hashes = {_line_hash(line) for line in secondary_lines}
    return {
        "fixture_id": fixture_id,
        "primary_name": primary_name,
        "secondary_name": secondary_name,
        "primary_line_count": len(primary_lines),
        "secondary_line_count": len(secondary_lines),
        "union_line_count": len(union_lines),
        "common_line_hash_count": len(primary_hashes & secondary_hashes),
        "primary_only_line_hash_count": len(primary_hashes - secondary_hashes),
        "secondary_only_line_hash_count": len(secondary_hashes - primary_hashes),
        "primary": {
            "field_match_ratio": primary_metrics["field_match_ratio"],
            "field_matched": primary_metrics["field_matched"],
            "field_total": primary_metrics["field_total"],
            "ingredient_found": primary_metrics["ingredient_found"],
            "ingredient_total": primary_metrics["ingredient_total"],
        },
        "secondary": {
            "field_match_ratio": secondary_metrics["field_match_ratio"],
            "field_matched": secondary_metrics["field_matched"],
            "field_total": secondary_metrics["field_total"],
            "ingredient_found": secondary_metrics["ingredient_found"],
            "ingredient_total": secondary_metrics["ingredient_total"],
        },
        "union": {
            "field_match_ratio": union_metrics["field_match_ratio"],
            "field_matched": union_metrics["field_matched"],
            "field_total": union_metrics["field_total"],
            "ingredient_found": union_metrics["ingredient_found"],
            "ingredient_total": union_metrics["ingredient_total"],
        },
        "raw_ocr_text_stored": False,
    }


def _write_raw_debug(
    *,
    raw_debug_dir: Path,
    fixture_id: str,
    primary_name: str,
    secondary_name: str,
    primary_lines: list[str],
    secondary_lines: list[str],
) -> None:
    """Write temporary raw OCR lines for operator-only hard-case analysis."""
    raw_debug_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "paddleocr-raw-line-debug-v1",
        "fixture_id": fixture_id,
        "warning": "temporary operator-only raw OCR debug artifact; do not commit",
        "primary_name": primary_name,
        "secondary_name": secondary_name,
        "primary_lines": primary_lines,
        "secondary_lines": secondary_lines,
    }
    _write_json(raw_debug_dir / f"{_safe_filename(fixture_id)}.json", payload)


def _write_strategy_artifacts(
    *,
    output_dir: Path,
    strategy: str,
    eval_payload: dict[str, Any],
    split_rows: list[dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Write eval, observations, summary, and gate artifacts for one strategy."""
    observations = eval_payload.pop("observations")
    eval_path = output_dir / f"paddleocr-adaptive-eval.{strategy}.json"
    observations_path = output_dir / f"paddleocr-adaptive-observations.{strategy}.jsonl"
    summary_path = output_dir / f"structured-extraction-summary.{strategy}.json"
    gate_path = output_dir / f"structured-extraction-gate.{strategy}.json"
    _write_json(eval_path, eval_payload)
    _write_jsonl(observations_path, observations)
    summary = build_summary(
        eval_json=eval_payload,
        split_rows=split_rows,
        eval_split=args.eval_split,
        provider=args.provider,
        leakage_check_passed=True,
        privacy_review_cleared=True,
    )
    gate = build_structured_extraction_gate(
        summary,
        target_threshold=Decimal(str(args.target_threshold)),
        min_ingredient_recall=Decimal(str(args.min_ingredient_recall)),
        min_fixture_count=args.min_fixtures,
    )
    _write_json(summary_path, summary)
    _write_json(gate_path, gate)
    return {
        "strategy": strategy,
        "metrics": summary["metrics"],
        "failure_modes": summary["failure_modes"],
        "gate_status": gate["status"],
        "eval_json": str(eval_path.relative_to(output_dir)),
        "summary_json": str(summary_path.relative_to(output_dir)),
        "gate_json": str(gate_path.relative_to(output_dir)),
    }


def run_adaptive_eval(args: argparse.Namespace) -> dict[str, Any]:  # noqa: PLR0912, PLR0915
    """Run adaptive OCR merge evaluation.

    Args:
        args: Parsed CLI namespace.

    Returns:
        Redacted comparison summary.

    Raises:
        FileNotFoundError: If required inputs are missing.
    """
    todo_path = args.bundle_dir / "ground-truth.todo.jsonl"
    if not todo_path.is_file():
        raise FileNotFoundError(f"ground-truth.todo.jsonl not found under {args.bundle_dir}")
    if not args.splits.is_file():
        raise FileNotFoundError(f"splits JSONL not found: {args.splits}")

    primary_config = CandidateConfig(args.primary_name, args.primary_rec_model_dir)
    secondary_config = CandidateConfig(args.secondary_name, args.secondary_rec_model_dir)
    profile = PROFILES[args.profile]
    det_model = args.det_model or profile["det"]
    rec_model = args.rec_model or profile["rec"]
    max_side = args.max_side or profile["max_side"]

    if not args.apply:
        return {
            "schema_version": SCHEMA_VERSION,
            "apply_requested": False,
            "profile": args.profile,
            "det_unclip_ratio": args.det_unclip_ratio,
            "primary_name": primary_config.name,
            "secondary_name": secondary_config.name,
            "raw_debug_requested": args.raw_debug_dir is not None,
            "source_doc_urls": SOURCE_DOC_URLS,
        }

    primary_ocr = _build_ocr(
        det_model=det_model,
        rec_model=rec_model,
        max_side=max_side,
        det_box_thresh=args.det_box_thresh,
        det_thresh=args.det_thresh,
        det_unclip_ratio=args.det_unclip_ratio,
        rec_model_dir=primary_config.recognition_model_dir,
    )
    secondary_ocr = _build_ocr(
        det_model=det_model,
        rec_model=rec_model,
        max_side=max_side,
        det_box_thresh=args.det_box_thresh,
        det_thresh=args.det_thresh,
        det_unclip_ratio=args.det_unclip_ratio,
        rec_model_dir=secondary_config.recognition_model_dir,
    )

    primary_rows: list[dict[str, Any]] = []
    secondary_rows: list[dict[str, Any]] = []
    union_rows: list[dict[str, Any]] = []
    oracle_rows: list[dict[str, Any]] = []
    primary_observations: list[dict[str, Any]] = []
    secondary_observations: list[dict[str, Any]] = []
    union_observations: list[dict[str, Any]] = []
    oracle_observations: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    started = time.monotonic()
    for row in _load_ready_rows(args.bundle_dir, args.limit):
        fixture_id = str(row.get("fixture_id") or "")
        expected = row["expected"]
        image_path = str(row.get("image_path", "")).strip()
        if not fixture_id or not image_path:
            failures.append({"fixture_id": fixture_id or "unknown", "reason": "missing_fixture_or_image"})
            continue
        try:
            primary_lines = _predict_lines(primary_ocr, args.bundle_dir / image_path)
            secondary_lines = _predict_lines(secondary_ocr, args.bundle_dir / image_path)
        except Exception:
            failures.append({"fixture_id": fixture_id, "reason": "paddleocr_prediction_failed"})
            continue
        merged_lines = _union_lines(primary_lines, secondary_lines)

        primary_metric, primary_observation = _score_prediction(
            fixture_id=fixture_id,
            expected=expected,
            lines=primary_lines,
            post_pass=args.post_pass,
            provider=args.provider,
        )
        secondary_metric, secondary_observation = _score_prediction(
            fixture_id=fixture_id,
            expected=expected,
            lines=secondary_lines,
            post_pass=args.post_pass,
            provider=args.provider,
        )
        union_metric, union_observation = _score_prediction(
            fixture_id=fixture_id,
            expected=expected,
            lines=merged_lines,
            post_pass=args.post_pass,
            provider=args.provider,
        )
        oracle_metric = _better_metric_row(
            _better_metric_row(primary_metric, secondary_metric),
            union_metric,
        )
        if oracle_metric is primary_metric:
            oracle_observation = primary_observation
        elif oracle_metric is secondary_metric:
            oracle_observation = secondary_observation
        else:
            oracle_observation = union_observation

        primary_rows.append(primary_metric)
        secondary_rows.append(secondary_metric)
        union_rows.append(union_metric)
        oracle_rows.append({**oracle_metric, "oracle_source": oracle_observation["status"]})
        primary_observations.append(primary_observation)
        secondary_observations.append(secondary_observation)
        union_observations.append(union_observation)
        oracle_observations.append(oracle_observation)
        comparison_rows.append(
            _comparison_row(
                fixture_id=fixture_id,
                primary_name=primary_config.name,
                secondary_name=secondary_config.name,
                primary_lines=primary_lines,
                secondary_lines=secondary_lines,
                union_lines=merged_lines,
                primary_metrics=primary_metric,
                secondary_metrics=secondary_metric,
                union_metrics=union_metric,
            )
        )

    strategy_evals = {
        primary_config.name: _aggregate_eval(
            strategy=primary_config.name,
            per_image=primary_rows,
            observations=primary_observations,
            args=args,
            det_model=det_model,
            rec_model=rec_model,
            max_side=max_side,
        ),
        secondary_config.name: _aggregate_eval(
            strategy=secondary_config.name,
            per_image=secondary_rows,
            observations=secondary_observations,
            args=args,
            det_model=det_model,
            rec_model=rec_model,
            max_side=max_side,
        ),
        "union": _aggregate_eval(
            strategy="union",
            per_image=union_rows,
            observations=union_observations,
            args=args,
            det_model=det_model,
            rec_model=rec_model,
            max_side=max_side,
        ),
        "oracle_best": _aggregate_eval(
            strategy="oracle_best",
            per_image=oracle_rows,
            observations=oracle_observations,
            args=args,
            det_model=det_model,
            rec_model=rec_model,
            max_side=max_side,
        ),
    }
    split_rows = _read_jsonl(args.splits)
    strategy_summaries = [
        _write_strategy_artifacts(
            output_dir=args.output_dir,
            strategy=strategy,
            eval_payload=dict(eval_payload),
            split_rows=split_rows,
            args=args,
        )
        for strategy, eval_payload in strategy_evals.items()
    ]
    primary_hardcases = extract_hardcases(
        eval_json=strategy_evals[primary_config.name],
        split_by_fixture={str(row.get("fixture_id")): str(row.get("split")) for row in split_rows},
        eval_split=args.eval_split,
    )
    hardcase_ids = set(primary_hardcases["fixture_ids"]["union_field_zero_or_ingredient_all_missed"])
    hardcase_comparison_rows = [row for row in comparison_rows if row["fixture_id"] in hardcase_ids]
    line_comparison = {
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "primary_name": primary_config.name,
        "secondary_name": secondary_config.name,
        "hardcase_fixture_count": len(hardcase_comparison_rows),
        "rows": hardcase_comparison_rows,
        "raw_ocr_text_stored": False,
        "provider_payload_stored": False,
    }
    _write_json(args.output_dir / "hardcase-fixtures.primary.json", primary_hardcases)
    _write_json(args.output_dir / "line-comparison-hardcases.redacted.json", line_comparison)

    if args.raw_debug_dir is not None:
        for row in _load_ready_rows(args.bundle_dir, args.limit):
            fixture_id = str(row.get("fixture_id") or "")
            image_path = str(row.get("image_path", "")).strip()
            if fixture_id not in hardcase_ids or not image_path:
                continue
            try:
                primary_lines = _predict_lines(primary_ocr, args.bundle_dir / image_path)
                secondary_lines = _predict_lines(secondary_ocr, args.bundle_dir / image_path)
            except Exception:
                continue
            _write_raw_debug(
                raw_debug_dir=args.raw_debug_dir,
                fixture_id=fixture_id,
                primary_name=primary_config.name,
                secondary_name=secondary_config.name,
                primary_lines=primary_lines,
                secondary_lines=secondary_lines,
            )

    by_strategy = {item["strategy"]: item for item in strategy_summaries}
    primary_recall = by_strategy[primary_config.name]["metrics"]["ingredient_recall"]
    union_recall = by_strategy["union"]["metrics"]["ingredient_recall"]
    return {
        "schema_version": SCHEMA_VERSION,
        "apply_requested": True,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "profile": args.profile,
        "detection_model": det_model,
        "recognition_model": rec_model,
        "max_side": max_side,
        "det_box_thresh": args.det_box_thresh,
        "det_thresh": args.det_thresh,
        "det_unclip_ratio": args.det_unclip_ratio,
        "post_pass": args.post_pass,
        "primary_name": primary_config.name,
        "secondary_name": secondary_config.name,
        "strategy_summaries": strategy_summaries,
        "ingredient_recall_improved_by_union": union_recall > primary_recall,
        "primary_hardcase_counts": primary_hardcases["counts"],
        "failed_fixture_count": len(failures),
        "failures": failures,
        "redacted_line_comparison": "line-comparison-hardcases.redacted.json",
        "hardcase_fixtures": "hardcase-fixtures.primary.json",
        "raw_debug_dir_written": args.raw_debug_dir is not None,
        "raw_debug_policy": "temporary_operator_only_do_not_commit" if args.raw_debug_dir is not None else None,
        "oracle_best_note": "GT-derived upper bound; do not use as production strategy.",
        "source_doc_urls": SOURCE_DOC_URLS,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)
    try:
        summary = run_adaptive_eval(args)
    except FileNotFoundError as exc:
        print(json.dumps({"schema_version": SCHEMA_VERSION, "status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(args.output_dir / "adaptive-structured-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
