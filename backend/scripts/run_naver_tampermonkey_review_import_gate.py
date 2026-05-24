"""Run the Naver Tampermonkey review-to-import safety gate.

The gate executes the existing read-only handoff steps in order:

1. apply structured review decisions to review ingest rows,
2. validate the merged review decisions,
3. export approved DB import candidates,
4. build a dry-run ORM import plan.

It does not open a database session, execute SQL, run OCR, call an LLM, or send
data externally. Every generated artifact remains privacy-bounded and is written
under the requested output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts import apply_naver_tampermonkey_review_decisions as apply_decisions  # noqa: E402
from scripts import dry_run_naver_tampermonkey_approved_db_import as dry_run_import  # noqa: E402
from scripts import export_naver_tampermonkey_approved_db_import as approved_export  # noqa: E402
from scripts import validate_naver_tampermonkey_review_decisions as validator  # noqa: E402

SCHEMA_VERSION = "naver-tampermonkey-review-import-gate-v1"
RAW_FORBIDDEN_KEYS = validator.RAW_FORBIDDEN_KEYS
LITERAL_FORBIDDEN_KEYS = validator.LITERAL_FORBIDDEN_KEYS
LOCAL_PATH_MARKERS = validator.LOCAL_PATH_MARKERS


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the review import gate runner."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-ingest", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--artifact-prefix",
        default="review-import-gate",
        help="Safe filename prefix for generated artifacts.",
    )
    parser.add_argument("--overwrite-existing", action="store_true")
    parser.add_argument("--allow-unmatched-decisions", action="store_true")
    parser.add_argument(
        "--require-reviewed",
        action="store_true",
        help="Fail unless every review row has a decision.",
    )
    parser.add_argument(
        "--require-all-approved",
        action="store_true",
        help="Fail unless every reviewed row is approved for DB import.",
    )
    return parser.parse_args()


def main() -> None:
    """Run all review import gates and write a final summary."""
    args = parse_args()
    review_ingest_path = args.review_ingest.expanduser().resolve()
    decisions_path = args.decisions.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    try:
        summary = run_review_import_gate(
            review_ingest_path=review_ingest_path,
            decisions_path=decisions_path,
            output_dir=output_dir,
            artifact_prefix=args.artifact_prefix,
            overwrite_existing=args.overwrite_existing,
            allow_unmatched_decisions=args.allow_unmatched_decisions,
            require_reviewed=args.require_reviewed,
            require_all_approved=args.require_all_approved,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failure = _failure_summary(
            review_ingest_path=review_ingest_path,
            decisions_path=decisions_path,
            output_dir=output_dir,
            error=exc,
        )
        print(json.dumps(failure, ensure_ascii=False, indent=2, sort_keys=True))
        raise SystemExit(1) from None


def run_review_import_gate(
    *,
    review_ingest_path: Path,
    decisions_path: Path,
    output_dir: Path,
    artifact_prefix: str = "review-import-gate",
    overwrite_existing: bool = False,
    allow_unmatched_decisions: bool = False,
    require_reviewed: bool = False,
    require_all_approved: bool = False,
) -> dict[str, object]:
    """Run the full review-to-import gate and write generated artifacts.

    Args:
        review_ingest_path: Input ``naver-tampermonkey-review-ingest-v1`` JSONL.
        decisions_path: Structured decision JSONL keyed by review task id.
        output_dir: Directory for generated privacy-safe artifacts.
        artifact_prefix: Safe filename prefix for output files.
        overwrite_existing: Whether apply step may replace existing decisions.
        allow_unmatched_decisions: Whether decisions absent from review ingest are ignored.
        require_reviewed: Whether every output review row must have a decision.
        require_all_approved: Whether every review row must export as approved.

    Returns:
        Final gate summary.

    Raises:
        ValueError: If any step fails validation or unsafe payload checks.
    """
    safe_prefix = _safe_artifact_prefix(artifact_prefix)
    output_dir.mkdir(parents=True, exist_ok=True)

    applied_path = output_dir / f"{safe_prefix}-review-ingest-with-decisions.jsonl"
    applied_summary_path = output_dir / f"{safe_prefix}-review-ingest-with-decisions.summary.json"
    validation_summary_path = output_dir / f"{safe_prefix}-review-decision-validation.summary.json"
    approved_path = output_dir / f"{safe_prefix}-approved-db-import.jsonl"
    approved_summary_path = output_dir / f"{safe_prefix}-approved-db-import.summary.json"
    dry_run_path = output_dir / f"{safe_prefix}-approved-db-import-dry-run.jsonl"
    dry_run_summary_path = output_dir / f"{safe_prefix}-approved-db-import-dry-run.summary.json"
    gate_summary_path = output_dir / f"{safe_prefix}-summary.json"

    applied_rows, applied_summary = apply_decisions.apply_review_decisions(
        review_ingest_path=review_ingest_path,
        decisions_path=decisions_path,
        output_name=applied_path.name,
        overwrite_existing=overwrite_existing,
        allow_unmatched_decisions=allow_unmatched_decisions,
        require_reviewed=require_reviewed,
    )
    _reject_unsafe_payload({"rows": applied_rows, "summary": applied_summary})
    _write_jsonl(applied_path, applied_rows)
    _write_json(applied_summary_path, applied_summary)

    validation_summary = validator.validate_review_decisions(
        input_path=applied_path,
        require_reviewed=require_reviewed,
    )
    _write_json(validation_summary_path, validation_summary)

    approved_rows, approved_summary = approved_export.export_approved_db_import_rows(
        input_path=applied_path,
        require_all_approved=require_all_approved,
    )
    _reject_unsafe_payload({"rows": approved_rows, "summary": approved_summary})
    _write_jsonl(approved_path, approved_rows)
    _write_json(approved_summary_path, approved_summary)

    dry_run_rows, dry_run_summary = dry_run_import.build_dry_run_import_plan(
        input_path=approved_path,
    )
    _reject_unsafe_payload({"rows": dry_run_rows, "summary": dry_run_summary})
    _write_jsonl(dry_run_path, dry_run_rows)
    _write_json(dry_run_summary_path, dry_run_summary)

    gate_summary = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "review_ingest_name": review_ingest_path.name,
        "decisions_name": decisions_path.name,
        "artifact_prefix": safe_prefix,
        "artifacts": {
            "applied_review_ingest": applied_path.name,
            "applied_summary": applied_summary_path.name,
            "validation_summary": validation_summary_path.name,
            "approved_db_import": approved_path.name,
            "approved_summary": approved_summary_path.name,
            "dry_run_plan": dry_run_path.name,
            "dry_run_summary": dry_run_summary_path.name,
        },
        "review_row_count": applied_summary["review_row_count"],
        "decision_row_count": applied_summary["decision_row_count"],
        "matched_decision_count": applied_summary["matched_decision_count"],
        "pending_count": validation_summary["pending_count"],
        "approved_row_count": approved_summary["approved_row_count"],
        "planned_product_upsert_count": dry_run_summary["planned_product_upsert_count"],
        "planned_ingredient_row_count": dry_run_summary["planned_ingredient_row_count"],
        "require_reviewed": require_reviewed,
        "require_all_approved": require_all_approved,
        "dry_run_only": True,
        "db_write_performed": False,
        "external_transfer_performed": False,
        "raw_artifacts_stored": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "raw_model_response_stored": False,
        "local_path_literals_stored": False,
        "free_text_review_notes_stored": False,
        "clinical_recommendations_stored": False,
    }
    _reject_unsafe_payload(gate_summary)
    _write_json(gate_summary_path, gate_summary)
    return gate_summary


def _failure_summary(
    *,
    review_ingest_path: Path,
    decisions_path: Path,
    output_dir: Path,
    error: BaseException,
) -> dict[str, object]:
    """Return a redacted CLI failure summary without filesystem literals."""
    summary = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "error",
        "review_ingest_name": review_ingest_path.name,
        "review_ingest_path_hash": _sha256_text(str(review_ingest_path.expanduser())),
        "decisions_name": decisions_path.name,
        "decisions_path_hash": _sha256_text(str(decisions_path.expanduser())),
        "output_dir_name": output_dir.name,
        "output_dir_path_hash": _sha256_text(str(output_dir.expanduser())),
        "error_code": _safe_error_code(error),
        "error_message": _safe_public_error_message(error),
        "review_row_count": 0,
        "decision_row_count": 0,
        "matched_decision_count": 0,
        "pending_count": 0,
        "approved_row_count": 0,
        "planned_product_upsert_count": 0,
        "planned_ingredient_row_count": 0,
        "dry_run_only": True,
        "db_write_performed": False,
        "external_transfer_performed": False,
        "raw_artifacts_stored": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "raw_model_response_stored": False,
        "local_path_literals_stored": False,
        "free_text_review_notes_stored": False,
        "clinical_recommendations_stored": False,
    }
    _reject_unsafe_payload(summary)
    return summary


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    """Write JSONL rows after final unsafe-payload rejection."""
    _reject_unsafe_payload(rows)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_json(path: Path, value: dict[str, object]) -> None:
    """Write a JSON object after final unsafe-payload rejection."""
    _reject_unsafe_payload(value)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _safe_artifact_prefix(value: str) -> str:
    """Return a conservative filename prefix for generated artifacts."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("artifact_prefix must be non-empty.")
    if any(marker in stripped for marker in LOCAL_PATH_MARKERS):
        raise ValueError("artifact_prefix contains local path literal.")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
    if any(char not in allowed for char in stripped):
        raise ValueError("artifact_prefix must contain only safe filename characters.")
    return stripped[:80]


def _reject_unsafe_payload(value: object) -> None:
    """Reject raw keys, local path literals, and sensitive literal keys recursively."""
    if isinstance(value, dict):
        lowered_keys = {str(key).lower() for key in value}
        forbidden = RAW_FORBIDDEN_KEYS.intersection(lowered_keys)
        literal_forbidden = LITERAL_FORBIDDEN_KEYS.intersection(lowered_keys)
        if forbidden:
            raise ValueError(f"Payload contains forbidden raw field(s): {sorted(forbidden)}")
        if literal_forbidden:
            raise ValueError(
                f"Payload contains forbidden literal field(s): {sorted(literal_forbidden)}"
            )
        for nested in value.values():
            _reject_unsafe_payload(nested)
    elif isinstance(value, list | tuple):
        for item in value:
            _reject_unsafe_payload(item)
    elif isinstance(value, str) and any(marker in value for marker in LOCAL_PATH_MARKERS):
        raise ValueError("Payload contains local path literal.")


def _sha256_text(value: str) -> str:
    """Return a SHA-256 digest for a UTF-8 text value."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_error_code(exc: BaseException) -> str:
    """Return a bounded non-sensitive CLI error code."""
    if isinstance(exc, OSError):
        return "local_file_operation_error"
    if isinstance(exc, json.JSONDecodeError):
        return "json_decode_error"
    return "validation_error"


def _safe_public_error_message(exc: BaseException) -> str:
    """Return a bounded public error message without filesystem details."""
    if isinstance(exc, OSError):
        message = "Local file operation failed."
    elif isinstance(exc, json.JSONDecodeError):
        message = "JSON decode failed."
    else:
        message = str(exc).strip()
    if (
        not message
        or any(marker in message for marker in LOCAL_PATH_MARKERS)
        or "/" in message
        or "\\" in message
    ):
        return "Validation failed."
    return message[:200]


if __name__ == "__main__":
    main()
