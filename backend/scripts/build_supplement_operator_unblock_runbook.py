"""Build a redacted runbook for unblocking supplement operator review.

The supplement taxonomy/OCR/YOLO/PaddleOCR pipeline cannot proceed while human
brand, PII, or YOLO annotation batches are blank. This script summarizes the
current review queues, the next batch to edit, and the post-completion gate
sequence from already-redacted artifacts. It never reads source images, raw OCR,
provider payloads, local source paths, database records, or product folder
names.

References:
    https://docs.ultralytics.com/datasets/detect/
    https://docs.ultralytics.com/tasks/detect/
    https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html
    https://cloud.google.com/vision/docs/ocr
    https://api.ncloud-docs.com/docs/en/ai-application-service-ocr
    https://docs.sqlalchemy.org/en/21/orm/queryguide/select.html
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from scripts import (  # noqa: E402
    build_supplement_learning_completion_audit as completion_audit,
)
from scripts import build_supplement_operator_next_batch_work_order as work_order  # noqa: E402
from scripts import (  # noqa: E402
    build_supplement_operator_post_completion_command_plan as post_completion,
)
from scripts import (  # noqa: E402
    preflight_supplement_operator_review_batch_progress as progress_preflight,
)

SCHEMA_VERSION = "supplement-operator-unblock-runbook-v1"
BATCH_PROGRESS_SCHEMA = progress_preflight.SCHEMA_VERSION
WORK_ORDER_SCHEMA = work_order.SCHEMA_VERSION
POST_COMPLETION_SCHEMA = post_completion.SCHEMA_VERSION
COMPLETION_AUDIT_SCHEMA = completion_audit.SCHEMA_VERSION
OPTIONAL_GATE_SCHEMAS = {
    "brand_db_import_gate": "supplement-brand-db-import-gate-v1",
    "ocr_benchmark_gate": "supplement-ocr-benchmark-gate-v1",
    "yolo_section_dataset_gate": "supplement-yolo-section-dataset-gate-v1",
}
GATE_ALLOWED_FLAG_KEYS = (
    "db_import_apply_allowed_now",
    "product_import_manifest_allowed",
    "teacher_ocr_benchmark_allowed",
    "external_teacher_ocr_eval_allowed",
    "paddleocr_training_allowed_now",
    "dataset_materialization_ready",
    "section_yolo_training_allowed_now",
    "model_promotion_allowed_now",
)
GATE_COUNT_KEYS = (
    "blank_decision_count",
    "pii_blank_decision_count",
    "blank_box_row_count",
    "pending_operator_action_count",
    "pii_pending_operator_action_count",
    "approved_decision_count",
    "cleared_no_personal_data_count",
    "reviewed_box_row_count",
    "benchmark_fixture_count",
    "promoted_item_count",
)
QUEUE_SEQUENCE: tuple[dict[str, str], ...] = (
    {
        "queue_key": "brand_product_review",
        "title": "brand and product review",
        "unblocks": "taxonomy product/category DB import",
    },
    {
        "queue_key": "review_pii_screening",
        "title": "review image PII screening",
        "unblocks": "manual OCR ground truth and teacher OCR comparison",
    },
    {
        "queue_key": "yolo_section_annotation",
        "title": "supplement section bbox annotation",
        "unblocks": "YOLO section dataset and PaddleOCR improvement loop",
    },
)
UNSAFE_TRUE_FLAGS = completion_audit.UNSAFE_TRUE_FLAGS


class OperatorUnblockRunbookError(ValueError):
    """Raised when the unblock runbook inputs cannot be trusted."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional test argument list.

    Returns:
        Parsed CLI namespace.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-progress", type=Path, required=True)
    parser.add_argument("--next-work-order", type=Path, required=True)
    parser.add_argument("--post-completion-plan", type=Path, required=True)
    parser.add_argument("--completion-audit", type=Path, required=True)
    parser.add_argument("--brand-db-import-gate", type=Path, default=None)
    parser.add_argument("--ocr-benchmark-gate", type=Path, default=None)
    parser.add_argument("--yolo-section-dataset-gate", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Write a redacted unblock runbook JSON and optional Markdown.

    Args:
        argv: Optional test argument list.
    """
    args = parse_args(argv)
    input_paths = {
        "batch_progress": args.batch_progress.expanduser().resolve(),
        "next_work_order": args.next_work_order.expanduser().resolve(),
        "post_completion_plan": args.post_completion_plan.expanduser().resolve(),
        "completion_audit": args.completion_audit.expanduser().resolve(),
    }
    optional_inputs = {
        "brand_db_import_gate": args.brand_db_import_gate,
        "ocr_benchmark_gate": args.ocr_benchmark_gate,
        "yolo_section_dataset_gate": args.yolo_section_dataset_gate,
    }
    for key, path in optional_inputs.items():
        if path is not None:
            input_paths[key] = path.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    markdown_output = (
        args.markdown_output.expanduser().resolve() if args.markdown_output is not None else None
    )
    try:
        runbook = build_operator_unblock_runbook(input_paths=input_paths)
        _write_json(output_path, runbook)
        if markdown_output is not None:
            markdown_output.parent.mkdir(parents=True, exist_ok=True)
            markdown_output.write_text(build_markdown(runbook), encoding="utf-8")
        print(json.dumps(_cli_summary(runbook), ensure_ascii=False, sort_keys=True))
    except (OSError, json.JSONDecodeError, OperatorUnblockRunbookError) as exc:
        failure = _failure_summary(input_paths=input_paths, output_path=output_path, error=exc)
        _write_json(output_path, failure)
        print(json.dumps(failure, ensure_ascii=False, sort_keys=True))
        raise SystemExit(1) from None


def build_operator_unblock_runbook(*, input_paths: Mapping[str, Path]) -> dict[str, Any]:
    """Build the operator unblock runbook.

    Args:
        input_paths: Redacted summary artifact paths.

    Returns:
        Redacted runbook payload.

    Raises:
        OperatorUnblockRunbookError: If an input is missing, unsafe, or unsupported.
    """
    required_paths = {
        "batch_progress": _required_input(input_paths, "batch_progress"),
        "next_work_order": _required_input(input_paths, "next_work_order"),
        "post_completion_plan": _required_input(input_paths, "post_completion_plan"),
        "completion_audit": _required_input(input_paths, "completion_audit"),
    }
    progress = _load_json_object(required_paths["batch_progress"])
    next_work_order = _load_json_object(required_paths["next_work_order"])
    post_plan = _load_json_object(required_paths["post_completion_plan"])
    audit = _load_json_object(required_paths["completion_audit"])

    _require_schema(progress, BATCH_PROGRESS_SCHEMA)
    _require_schema(next_work_order, WORK_ORDER_SCHEMA)
    _require_schema(post_plan, POST_COMPLETION_SCHEMA)
    _require_schema(audit, COMPLETION_AUDIT_SCHEMA)
    for payload in (progress, next_work_order, post_plan, audit):
        _reject_unsafe_payload(payload)
        _reject_unsafe_true_flags(payload)
    gate_summaries = _optional_gate_summaries(input_paths)

    queue_summaries = _queue_summaries(progress)
    sequence = _operator_sequence(queue_summaries=queue_summaries, completion_audit=audit)
    runbook = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": _runbook_status(progress=progress, completion_audit=audit),
        "objective_completion_allowed": audit.get("objective_completion_allowed") is True,
        "current_next_batch_key": _safe_string(next_work_order.get("batch_key")),
        "current_next_queue_key": _safe_string(next_work_order.get("queue_key")),
        "current_next_batch_file_name": _safe_string(next_work_order.get("batch_file_name")),
        "source_editable_file_name": _safe_string(next_work_order.get("source_editable_file_name")),
        "total_blank_row_count": _non_negative_int(progress.get("total_blank_row_count")),
        "requirement_summary": {
            "verified": _non_negative_int(audit.get("verified_requirement_count")),
            "pending": _non_negative_int(audit.get("pending_requirement_count")),
            "blocked": _non_negative_int(audit.get("blocked_requirement_count")),
            "incomplete_requirement_keys": _safe_string_list(
                audit.get("incomplete_requirement_keys")
            ),
        },
        "gate_summaries": gate_summaries,
        "queue_summaries": queue_summaries,
        "operator_sequence": sequence,
        "current_post_completion_execution_allowed": post_plan.get(
            "post_completion_execution_allowed"
        )
        is True,
        "current_post_completion_blocker_codes": _safe_string_list(
            post_plan.get("blocked_reason_codes")
        ),
        "current_post_completion_steps": _post_completion_steps(post_plan),
        "input_names": {key: path.name for key, path in sorted(input_paths.items())},
        "input_path_hashes": {
            key: progress_preflight._sha256_text(str(path.expanduser()))
            for key, path in sorted(input_paths.items())
        },
        "db_write_performed": False,
        "external_provider_call_performed": False,
        "llm_call_performed": False,
        "training_execution_performed_by_script": False,
        "source_rows_read": False,
        "source_image_read_performed": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
        "product_dir_literals_stored": False,
        "local_path_literals_stored": False,
        "source_doc_urls": _source_doc_urls(progress, audit, *gate_summaries),
    }
    _reject_unsafe_payload(runbook)
    _reject_unsafe_true_flags(runbook)
    return runbook


def build_markdown(runbook: Mapping[str, Any]) -> str:
    """Build a redacted Markdown runbook.

    Args:
        runbook: Unblock runbook payload.

    Returns:
        Markdown report.
    """
    _reject_unsafe_payload(runbook)
    _reject_unsafe_true_flags(runbook)
    summary = runbook.get("requirement_summary")
    if not isinstance(summary, Mapping):
        summary = {}
    lines = [
        "# Supplement Operator Unblock Runbook",
        "",
        f"- Schema: `{SCHEMA_VERSION}`",
        f"- Status: `{_safe_string(runbook.get('status'))}`",
        f"- Completion allowed: `{str(runbook.get('objective_completion_allowed') is True).lower()}`",
        f"- Next batch: `{_safe_string(runbook.get('current_next_batch_key'))}`",
        f"- Next batch file: `{_safe_string(runbook.get('current_next_batch_file_name'))}`",
        f"- Source editable file: `{_safe_string(runbook.get('source_editable_file_name'))}`",
        f"- Total blank rows: `{_non_negative_int(runbook.get('total_blank_row_count'))}`",
        f"- Requirements: `{_non_negative_int(summary.get('verified'))}` verified / "
        f"`{_non_negative_int(summary.get('pending'))}` pending / "
        f"`{_non_negative_int(summary.get('blocked'))}` blocked",
        "",
        "## Queue Summary",
        "",
        "| Queue | Status | Batches | Blank | Valid | Next batch | Reason counts |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in _mapping_rows(runbook.get("queue_summaries")):
        lines.append(
            "| "
            + " | ".join(
                (
                    _md_cell(row.get("queue_key")),
                    f"`{_safe_string(row.get('status'))}`",
                    str(_non_negative_int(row.get("batch_count"))),
                    str(_non_negative_int(row.get("blank_row_count"))),
                    str(_non_negative_int(row.get("valid_row_count"))),
                    _md_cell(row.get("next_batch_key")),
                    _md_cell(_reason_counts_text(row.get("reason_counts"))),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Gate Summary",
            "",
            "| Gate | Status | Key counts | Allowed flags | Next steps |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in _mapping_rows(runbook.get("gate_summaries")):
        lines.append(
            "| "
            + " | ".join(
                (
                    _md_cell(row.get("gate_key")),
                    f"`{_safe_string(row.get('status'))}`",
                    _md_cell(_reason_counts_text(row.get("key_counts"))),
                    _md_cell(_bool_flags_text(row.get("allowed_flags"))),
                    _md_cell(", ".join(_safe_string_list(row.get("next_steps"))[:5])),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Unblock Sequence",
            "",
            "| Order | Queue | Action | Unblocks |",
            "| ---: | --- | --- | --- |",
        ]
    )
    for row in _mapping_rows(runbook.get("operator_sequence")):
        lines.append(
            "| "
            + " | ".join(
                (
                    str(_non_negative_int(row.get("order"))),
                    _md_cell(row.get("queue_key")),
                    _md_cell(row.get("next_action")),
                    _md_cell(row.get("unblocks")),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Current Post-Completion Gates",
            "",
        ]
    )
    for row in _mapping_rows(runbook.get("current_post_completion_steps")):
        lines.append(
            f"- `{_non_negative_int(row.get('order'))}` "
            f"`{_safe_string(row.get('script_key'))}`: {_safe_string(row.get('purpose'))}"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Source images read: `false`",
            "- DB write performed: `false`",
            "- OCR provider call performed: `false`",
            "- LLM call performed: `false`",
            "- Training execution performed: `false`",
            "- Raw OCR/provider payload stored: `false`",
            "",
            "## Source Docs",
            "",
        ]
    )
    lines.extend(f"- {url}" for url in runbook.get("source_doc_urls", []))
    return "\n".join(lines) + "\n"


def _queue_summaries(progress: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Aggregate batch progress rows by queue.

    Args:
        progress: Batch progress payload.

    Returns:
        Redacted queue summary rows.
    """
    batches = progress.get("batches")
    if not isinstance(batches, list):
        raise OperatorUnblockRunbookError("Batch progress is missing batches.")
    summaries: dict[str, dict[str, Any]] = {}
    for batch in batches:
        if not isinstance(batch, Mapping):
            raise OperatorUnblockRunbookError("Batch progress has invalid batch rows.")
        queue_key = _safe_string(batch.get("queue_key"))
        if not queue_key:
            raise OperatorUnblockRunbookError("Batch row is missing queue_key.")
        summary = summaries.setdefault(
            queue_key,
            {
                "queue_key": queue_key,
                "status": "complete",
                "batch_count": 0,
                "blank_row_count": 0,
                "valid_row_count": 0,
                "invalid_row_count": 0,
                "missing_row_count": 0,
                "next_batch_key": "",
                "reason_counts": {},
            },
        )
        summary["batch_count"] += 1
        summary["blank_row_count"] += _non_negative_int(batch.get("blank_row_count"))
        summary["valid_row_count"] += _non_negative_int(batch.get("valid_row_count"))
        summary["invalid_row_count"] += _non_negative_int(batch.get("invalid_row_count"))
        summary["missing_row_count"] += _non_negative_int(batch.get("missing_row_count"))
        if _safe_string(batch.get("batch_status")) != "complete":
            summary["status"] = "pending_operator_review"
            if not summary["next_batch_key"]:
                summary["next_batch_key"] = _safe_string(batch.get("batch_key"))
        for reason_key, count in _reason_counts(batch.get("reason_counts")).items():
            summary["reason_counts"][reason_key] = (
                summary["reason_counts"].get(reason_key, 0) + count
            )
    ordered = []
    for item in QUEUE_SEQUENCE:
        queue_key = item["queue_key"]
        if queue_key in summaries:
            ordered.append(summaries.pop(queue_key))
    ordered.extend(summaries[key] for key in sorted(summaries))
    return ordered


def _optional_gate_summaries(input_paths: Mapping[str, Path]) -> list[dict[str, Any]]:
    """Load optional downstream gate summaries.

    Args:
        input_paths: Input path mapping with optional gate keys.

    Returns:
        Redacted gate summary rows.

    Raises:
        OperatorUnblockRunbookError: If a provided gate is unsafe or unsupported.
    """
    summaries = []
    for gate_key, expected_schema in OPTIONAL_GATE_SCHEMAS.items():
        path = input_paths.get(gate_key)
        if path is None:
            continue
        if not path.exists():
            raise OperatorUnblockRunbookError(f"Input does not exist: {gate_key}")
        payload = _load_json_object(path)
        _require_schema(payload, expected_schema)
        _reject_unsafe_payload(payload)
        _reject_unsafe_true_flags(payload)
        summaries.append(_gate_summary(gate_key=gate_key, path=path, payload=payload))
    return summaries


def _gate_summary(*, gate_key: str, path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a redacted downstream gate row.

    Args:
        gate_key: Stable gate key.
        path: Gate file path.
        payload: Gate JSON payload.

    Returns:
        Redacted gate row.
    """
    return {
        "gate_key": gate_key,
        "input_name": path.name,
        "schema_version": _safe_string(payload.get("schema_version")),
        "status": _safe_string(payload.get("status")),
        "key_counts": _selected_counts(payload, GATE_COUNT_KEYS),
        "allowed_flags": _selected_bool_flags(payload, GATE_ALLOWED_FLAG_KEYS),
        "next_steps": _safe_string_list(payload.get("next_steps"))[:10],
        "source_doc_urls": _safe_string_list(payload.get("source_doc_urls")),
    }


def _operator_sequence(
    *,
    queue_summaries: Sequence[Mapping[str, Any]],
    completion_audit: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build high-level operator unblock sequence.

    Args:
        queue_summaries: Queue summary rows.
        completion_audit: Completion audit payload.

    Returns:
        Ordered operator sequence rows.
    """
    summaries_by_queue = {
        _safe_string(row.get("queue_key")): row
        for row in queue_summaries
        if _safe_string(row.get("queue_key"))
    }
    sequence = []
    for index, item in enumerate(QUEUE_SEQUENCE, start=1):
        summary = summaries_by_queue.get(item["queue_key"], {})
        sequence.append(
            {
                "order": index,
                "queue_key": item["queue_key"],
                "title": item["title"],
                "status": _safe_string(summary.get("status")) or "blocked_missing_queue_summary",
                "next_batch_key": _safe_string(summary.get("next_batch_key")),
                "next_action": _queue_next_action(item["queue_key"], summary),
                "blank_row_count": _non_negative_int(summary.get("blank_row_count")),
                "unblocks": item["unblocks"],
            }
        )
    incomplete = _safe_string_list(completion_audit.get("incomplete_requirement_keys"))
    if incomplete:
        sequence.append(
            {
                "order": len(sequence) + 1,
                "queue_key": "post_operator_gates",
                "title": "post-operator gates",
                "status": "blocked_until_operator_batches_complete",
                "next_batch_key": "",
                "next_action": "run_post_completion_gates_in_order",
                "blank_row_count": 0,
                "unblocks": "remaining requirement gates: " + ", ".join(incomplete[:8]),
            }
        )
    return sequence


def _post_completion_steps(post_plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Extract safe post-completion step summaries.

    Args:
        post_plan: Post-completion command plan.

    Returns:
        Step summary rows.
    """
    steps = post_plan.get("steps")
    if not isinstance(steps, list):
        return []
    result = []
    for step in steps[:40]:
        if not isinstance(step, Mapping):
            continue
        result.append(
            {
                "order": _non_negative_int(step.get("order")),
                "script_key": _safe_string(step.get("script_key")),
                "gate_policy": _safe_string(step.get("gate_policy")),
                "purpose": _safe_string(step.get("purpose")),
            }
        )
    return result


def _runbook_status(*, progress: Mapping[str, Any], completion_audit: Mapping[str, Any]) -> str:
    """Return the overall runbook status.

    Args:
        progress: Batch progress payload.
        completion_audit: Completion audit payload.

    Returns:
        Stable status string.
    """
    if completion_audit.get("objective_completion_allowed") is True:
        return "complete_verified"
    if _non_negative_int(progress.get("total_blank_row_count")) > 0:
        return "blocked_by_operator_review"
    return _safe_string(completion_audit.get("overall_status")) or "blocked_by_missing_evidence"


def _queue_next_action(queue_key: str, summary: Mapping[str, Any]) -> str:
    """Return a safe queue-specific next action.

    Args:
        queue_key: Queue key.
        summary: Queue summary.

    Returns:
        Action code.
    """
    if _non_negative_int(summary.get("blank_row_count")) <= 0:
        return "run_queue_post_completion_gates"
    if queue_key == "brand_product_review":
        return "complete_brand_product_human_review"
    if queue_key == "review_pii_screening":
        return "complete_review_image_pii_screening"
    if queue_key == "yolo_section_annotation":
        return "complete_supplement_section_bbox_review"
    return "complete_operator_review"


def _source_doc_urls(*payloads: Mapping[str, Any]) -> list[str]:
    """Collect source documentation URLs from safe input payloads.

    Args:
        payloads: Payloads that may contain source_doc_urls.

    Returns:
        Unique safe URLs.
    """
    urls = []
    for payload in payloads:
        for url in _safe_string_list(payload.get("source_doc_urls")):
            if url.startswith("https://") and url not in urls:
                urls.append(url)
    return urls


def _load_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object.

    Args:
        path: JSON file path.

    Returns:
        JSON object.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise OperatorUnblockRunbookError("Expected a JSON object input.")
    return payload


def _required_input(input_paths: Mapping[str, Path], key: str) -> Path:
    """Return a required existing input path.

    Args:
        input_paths: Input path mapping.
        key: Required key.

    Returns:
        Existing path.
    """
    path = input_paths.get(key)
    if path is None:
        raise OperatorUnblockRunbookError(f"Missing required input: {key}")
    if not path.exists():
        raise OperatorUnblockRunbookError(f"Input does not exist: {key}")
    return path


def _require_schema(payload: Mapping[str, Any], expected: str) -> None:
    """Validate schema version.

    Args:
        payload: Input payload.
        expected: Expected schema version.
    """
    if payload.get("schema_version") != expected:
        raise OperatorUnblockRunbookError("Unsupported schema version.")


def _reject_unsafe_payload(payload: Any) -> None:
    """Reject raw OCR/provider/path payload leakage.

    Args:
        payload: Payload to scan.
    """
    try:
        completion_audit._reject_unsafe_payload(payload)
    except completion_audit.CompletionAuditError as exc:
        raise OperatorUnblockRunbookError(str(exc)) from exc


def _reject_unsafe_true_flags(payload: Any) -> None:
    """Reject true values for dangerous side-effect flags.

    Args:
        payload: Payload to scan recursively.
    """
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if key in UNSAFE_TRUE_FLAGS and value is True:
                raise OperatorUnblockRunbookError("Unsafe side-effect flag is true.")
            _reject_unsafe_true_flags(value)
    elif isinstance(payload, list):
        for item in payload:
            _reject_unsafe_true_flags(item)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write indented JSON.

    Args:
        path: Destination path.
        payload: JSON payload.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _failure_summary(
    *,
    input_paths: Mapping[str, Path],
    output_path: Path,
    error: Exception,
) -> dict[str, Any]:
    """Build a redacted failure summary.

    Args:
        input_paths: Input path mapping.
        output_path: Output path.
        error: Raised exception.

    Returns:
        Failure summary.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "failed",
        "error_type": type(error).__name__,
        "input_names": {key: path.name for key, path in sorted(input_paths.items())},
        "output_name": output_path.name,
        "objective_completion_allowed": False,
        "db_write_performed": False,
        "external_provider_call_performed": False,
        "llm_call_performed": False,
        "training_execution_performed_by_script": False,
        "source_image_read_performed": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
    }


def _cli_summary(runbook: Mapping[str, Any]) -> dict[str, Any]:
    """Return compact redacted CLI summary.

    Args:
        runbook: Runbook payload.

    Returns:
        CLI summary.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "status": runbook.get("status"),
        "objective_completion_allowed": runbook.get("objective_completion_allowed"),
        "current_next_batch_key": runbook.get("current_next_batch_key"),
        "total_blank_row_count": runbook.get("total_blank_row_count"),
    }


def _mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    """Return mapping rows from a list-like value.

    Args:
        value: Candidate list.

    Returns:
        Mapping rows.
    """
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, Mapping)]


def _reason_counts(value: Any) -> dict[str, int]:
    """Return safe reason counts.

    Args:
        value: Candidate reason count mapping.

    Returns:
        Reason counts.
    """
    if not isinstance(value, Mapping):
        return {}
    return {
        _safe_string(key): _non_negative_int(count)
        for key, count in value.items()
        if _safe_string(key)
    }


def _reason_counts_text(value: Any) -> str:
    """Return compact reason-count text.

    Args:
        value: Candidate reason count mapping.

    Returns:
        Compact text.
    """
    counts = _reason_counts(value)
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def _selected_counts(payload: Mapping[str, Any], keys: Sequence[str]) -> dict[str, int]:
    """Return present non-negative integer counts.

    Args:
        payload: Gate payload.
        keys: Candidate count keys.

    Returns:
        Present count mapping.
    """
    result = {}
    for key in keys:
        if key in payload:
            result[key] = _non_negative_int(payload.get(key))
    return result


def _selected_bool_flags(payload: Mapping[str, Any], keys: Sequence[str]) -> dict[str, bool]:
    """Return present boolean gate flags.

    Args:
        payload: Gate payload.
        keys: Candidate flag keys.

    Returns:
        Present boolean mapping.
    """
    return {key: payload.get(key) is True for key in keys if key in payload}


def _bool_flags_text(value: Any) -> str:
    """Return compact boolean flag text.

    Args:
        value: Candidate flag mapping.

    Returns:
        Compact text.
    """
    if not isinstance(value, Mapping):
        return ""
    flags = {
        _safe_string(key): bool(flag)
        for key, flag in value.items()
        if _safe_string(key)
    }
    return ", ".join(f"{key}={str(flags[key]).lower()}" for key in sorted(flags))


def _safe_string(value: Any) -> str:
    """Return a bounded safe string.

    Args:
        value: Candidate value.

    Returns:
        Safe string.
    """
    if not isinstance(value, str):
        return ""
    return value.strip()[:320]


def _safe_string_list(value: Any) -> list[str]:
    """Return bounded safe string list.

    Args:
        value: Candidate list.

    Returns:
        Safe strings.
    """
    if not isinstance(value, list):
        return []
    return [_safe_string(item) for item in value[:60] if _safe_string(item)]


def _non_negative_int(value: Any) -> int:
    """Return a non-negative integer.

    Args:
        value: Candidate value.

    Returns:
        Integer >= 0.
    """
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def _md_cell(value: Any) -> str:
    """Escape Markdown table cells.

    Args:
        value: Cell value.

    Returns:
        Escaped cell.
    """
    return _safe_string(value).replace("|", "/")


if __name__ == "__main__":
    main()
