"""Export safe review decision templates for Naver Tampermonkey review rows.

The output is an operator/UI contract, not an importable decision batch. It
contains stable review identifiers, bounded candidate hints, and the required
human decision fields. It never stores raw OCR text, raw provider payloads,
request headers, image bytes, local paths, free-text review notes, or secrets.
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

from scripts import validate_naver_tampermonkey_review_decisions as validator  # noqa: E402

SCHEMA_VERSION = "naver-tampermonkey-review-decision-template-v1"
EXPECTED_INPUT_SCHEMA_VERSION = "naver-tampermonkey-review-ingest-v1"
DEFAULT_MAX_CANDIDATES = 12
MAX_TEXT_LENGTH = validator.MAX_TEXT_LENGTH
MAX_INGREDIENT_NAME_LENGTH = 160
LOCAL_PATH_MARKERS = validator.LOCAL_PATH_MARKERS
REVIEW_DECISION_CONTRACT = {
    "allowed_statuses": sorted(validator.ALLOWED_DECISION_STATUSES),
    "approved_required_fields": [
        "status",
        "reviewer_id",
        "reviewed_at",
        "display_name",
        "ingredients",
        *validator.APPROVED_ATTESTATIONS,
    ],
    "rejected_or_needs_changes_required_fields": [
        "status",
        "reviewer_id",
        "reviewed_at",
        "reason_codes",
    ],
    "approved_attestations_required": list(validator.APPROVED_ATTESTATIONS),
    "free_text_notes_allowed": False,
    "raw_ocr_text_allowed": False,
    "provider_payload_allowed": False,
    "local_path_literals_allowed": False,
    "clinical_recommendations_allowed": False,
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for exporting review templates."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--summary",
        type=Path,
        default=None,
        help="Optional summary JSON path. Defaults to <output>.summary.json.",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=DEFAULT_MAX_CANDIDATES,
        help="Maximum safe ingredient candidate hints per review row.",
    )
    return parser.parse_args()


def main() -> None:
    """Write review decision templates and a redacted summary."""
    args = parse_args()
    output_path = args.output.expanduser().resolve()
    summary_path = (
        args.summary.expanduser().resolve()
        if args.summary is not None
        else output_path.with_suffix(output_path.suffix + ".summary.json")
    )
    input_path = args.input.expanduser().resolve()
    try:
        rows, summary = export_review_decision_template_rows(
            input_path=input_path,
            max_candidates=args.max_candidates,
        )
        _reject_unsafe_payload({"rows": rows, "summary": summary})

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failure = _failure_summary(input_path=input_path, output_path=output_path, error=exc)
        try:
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(
                json.dumps(failure, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        print(json.dumps(failure, ensure_ascii=False, indent=2, sort_keys=True))
        raise SystemExit(1) from None


def export_review_decision_template_rows(
    *,
    input_path: Path,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Return safe review decision template rows for a review ingest artifact.

    Args:
        input_path: Review ingest JSONL path.
        max_candidates: Maximum candidate hints retained per row.

    Returns:
        Template rows and a redacted summary.

    Raises:
        ValueError: If any input row is unsafe, not a review ingest row, or not
            eligible for human review.
    """
    candidate_limit = _candidate_limit(max_candidates)
    input_rows = _read_input_rows(input_path)
    rows = [_template_row(row, max_candidates=candidate_limit) for row in input_rows]
    total_candidates = sum(
        len(row["candidate_context"]["ingredient_candidates"])  # type: ignore[index]
        for row in rows
    )
    rows_with_candidates = sum(
        1
        for row in rows
        if row["candidate_context"]["ingredient_candidates"]  # type: ignore[index]
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "input_name": input_path.name,
        "row_count": len(rows),
        "rows_with_candidate_hints": rows_with_candidates,
        "total_candidate_hints": total_candidates,
        "max_candidates_per_row": candidate_limit,
        "decision_batch_importable": False,
        "requires_human_review": True,
        "raw_artifacts_stored": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "raw_model_response_stored": False,
        "local_path_literals_stored": False,
        "free_text_review_notes_stored": False,
        "clinical_recommendations_stored": False,
    }
    _reject_unsafe_payload({"rows": rows, "summary": summary})
    return rows, summary


def _failure_summary(
    *,
    input_path: Path,
    output_path: Path,
    error: BaseException,
) -> dict[str, object]:
    """Return a redacted CLI failure summary."""
    summary = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "error",
        "input_name": input_path.name,
        "input_path_hash": _sha256_text(str(input_path.expanduser())),
        "output_name": output_path.name,
        "output_path_hash": _sha256_text(str(output_path.expanduser())),
        "error_code": _safe_error_code(error),
        "error_message": _safe_public_error_message(error),
        "row_count": 0,
        "rows_with_candidate_hints": 0,
        "total_candidate_hints": 0,
        "decision_batch_importable": False,
        "requires_human_review": True,
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


def _template_row(row: dict[str, object], *, max_candidates: int) -> dict[str, object]:
    """Return one safe review template row."""
    _validate_review_row(row)
    category_key = _required_safe_token(row, "category_key")
    template = {
        "schema_version": SCHEMA_VERSION,
        "review_task_id": _required_str(row, "review_task_id"),
        "fixture_id": _required_str(row, "fixture_id"),
        "category_key": category_key,
        "review_decision_contract": REVIEW_DECISION_CONTRACT,
        "candidate_context": {
            "ingredient_candidates": _candidate_ingredients(
                row.get("ingredient_candidates"),
                max_candidates=max_candidates,
            ),
            "ocr_observation_count": _non_negative_int(row.get("ocr_observation_count")),
            "ingredient_candidate_count": _non_negative_int(row.get("ingredient_candidate_count")),
        },
    }
    _reject_unsafe_payload(template)
    return template


def _candidate_ingredients(value: object, *, max_candidates: int) -> list[dict[str, object]]:
    """Return bounded ingredient candidate hints for human review."""
    if not isinstance(value, list):
        return []
    candidates: list[dict[str, object]] = []
    for item in value:
        if len(candidates) >= max_candidates:
            break
        if not isinstance(item, dict):
            continue
        display_name = _optional_string(
            item.get("display_name"),
            max_length=MAX_INGREDIENT_NAME_LENGTH,
        )
        if display_name is None:
            continue
        candidate = {
            "display_name": display_name,
            "nutrient_code": _optional_safe_token(item.get("nutrient_code")),
            "amount": _optional_non_negative_number(item.get("amount")),
            "unit": _optional_string(item.get("unit"), max_length=40),
            "confidence": _optional_confidence(item.get("confidence")),
            "source": _optional_safe_token(item.get("source")),
            "provider": _optional_safe_token(item.get("provider")),
        }
        candidates.append({key: val for key, val in candidate.items() if val is not None})
    return candidates


def _validate_review_row(row: dict[str, object]) -> None:
    """Validate the review ingest row before template export."""
    _reject_unsafe_payload(row)
    if row.get("schema_version") != EXPECTED_INPUT_SCHEMA_VERSION:
        raise ValueError("Review template input rows must use review ingest schema.")
    if row.get("requires_human_review") is not True:
        raise ValueError("Review template rows must require human review.")
    if row.get("is_clinical_recommendation") is not False:
        raise ValueError("Review template rows must not be clinical recommendations.")
    if row.get("clinical_recommendation_forbidden") is not True:
        raise ValueError("Review template rows must keep clinical recommendation forbidden.")


def _read_input_rows(path: Path) -> list[dict[str, object]]:
    """Read input JSONL rows and reject unsafe payloads."""
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("JSONL rows must be objects.")
        _reject_unsafe_payload(row)
        review_task_id = _required_str(row, "review_task_id")
        if review_task_id in seen:
            raise ValueError(f"Duplicate review_task_id: {review_task_id}")
        seen.add(review_task_id)
        rows.append(row)
    return rows


def _candidate_limit(value: int) -> int:
    """Return a bounded positive candidate limit."""
    if value < 0:
        raise ValueError("max_candidates must be non-negative.")
    return min(value, validator.MAX_INGREDIENTS_PER_PRODUCT)


def _required_str(row: dict[str, object], key: str) -> str:
    """Return a required non-empty string field."""
    value = row.get(key)
    text = _optional_string(value)
    if text is None:
        raise ValueError(f"Row requires string field: {key}")
    return text


def _required_safe_token(row: dict[str, object], key: str) -> str:
    """Return a required bounded token field."""
    value = _optional_safe_token(row.get(key))
    if value is None:
        raise ValueError(f"Row requires safe token field: {key}")
    return value


def _optional_safe_token(value: object) -> str | None:
    """Return a bounded safe token or None."""
    return validator._safe_token(value)


def _optional_string(value: object, *, max_length: int = MAX_TEXT_LENGTH) -> str | None:
    """Return a bounded string while rejecting local path literals."""
    if not isinstance(value, str) or not value.strip():
        return None
    stripped = value.strip()
    if any(marker in stripped for marker in LOCAL_PATH_MARKERS):
        raise ValueError("Payload contains local path literal.")
    return stripped[:max_length]


def _optional_non_negative_number(value: object) -> float | None:
    """Return a non-negative number or None."""
    if isinstance(value, int | float) and value >= 0:
        return float(value)
    return None


def _optional_confidence(value: object) -> float | None:
    """Return a bounded confidence value or None."""
    if isinstance(value, int | float) and 0 <= value <= 1:
        return float(value)
    return None


def _non_negative_int(value: object) -> int:
    """Return a non-negative integer, defaulting missing values to zero."""
    return value if isinstance(value, int) and value >= 0 else 0


def _reject_unsafe_payload(value: object) -> None:
    """Reject raw keys, local path literals, and sensitive literal keys recursively."""
    validator._reject_unsafe_payload(value)


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
