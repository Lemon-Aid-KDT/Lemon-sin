"""Tests for supplement operator post-completion command planning."""

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

planner = importlib.import_module("scripts.build_supplement_operator_post_completion_command_plan")


def _write_work_order(path: Path, payload: dict[str, Any]) -> Path:
    """Write a work-order fixture.

    Args:
        path: Destination path.
        payload: JSON payload.

    Returns:
        Written path.
    """
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _work_order_payload(
    *,
    queue_key: str = "brand_product_review",
    batch_status: str = "pending",
    blank_row_count: int = 50,
    pending_row_count: int = 0,
    invalid_row_count: int = 0,
    missing_row_count: int = 0,
) -> dict[str, Any]:
    """Build a minimal safe next-batch work-order payload.

    Args:
        queue_key: Operator review queue key.
        batch_status: Current batch status.
        blank_row_count: Blank row count.
        pending_row_count: Pending row count.
        invalid_row_count: Invalid row count.
        missing_row_count: Missing row count.

    Returns:
        Work-order payload.
    """
    return {
        "schema_version": planner.WORK_ORDER_SCHEMA_VERSION,
        "batch_key": f"{queue_key}:001",
        "queue_key": queue_key,
        "batch_status": batch_status,
        "blank_row_count": blank_row_count,
        "pending_row_count": pending_row_count,
        "invalid_row_count": invalid_row_count,
        "missing_row_count": missing_row_count,
    }


def test_plan_blocks_pending_brand_batch_and_lists_brand_gates(tmp_path: Path) -> None:
    """Verify pending brand review batches expose only blocked post-completion steps."""
    work_order_path = _write_work_order(tmp_path / "work-order.json", _work_order_payload())

    plan = planner.build_post_completion_command_plan(
        input_paths={"work_order": work_order_path}
    )

    assert plan["post_completion_execution_allowed"] is False
    assert plan["operator_required_before_execution"] is True
    assert plan["blocked_reason_codes"] == [
        "batch_not_complete",
        "blank_rows_remaining",
    ]
    script_keys = [step["script_key"] for step in plan["steps"]]
    assert script_keys[:3] == [
        "preflight_supplement_operator_review_batch_file",
        "reconcile_supplement_operator_review_batch_files",
        "preflight_supplement_operator_review_batch_progress",
    ]
    assert "apply_supplement_brand_review_decisions" in script_keys
    assert "gate_supplement_product_db_apply" in script_keys
    assert plan["db_write_performed"] is False
    assert plan["external_provider_call_performed"] is False
    assert plan["source_rows_read"] is False


def test_plan_allows_complete_pii_batch_without_teacher_ocr_call(tmp_path: Path) -> None:
    """Verify complete PII batches can proceed to gate steps without provider calls."""
    work_order_path = _write_work_order(
        tmp_path / "work-order.json",
        _work_order_payload(
            queue_key="review_pii_screening",
            batch_status="complete",
            blank_row_count=0,
        ),
    )

    plan = planner.build_post_completion_command_plan(
        input_paths={"work_order": work_order_path}
    )

    assert plan["post_completion_execution_allowed"] is True
    assert plan["operator_required_before_execution"] is False
    assert plan["blocked_reason_codes"] == []
    script_keys = [step["script_key"] for step in plan["steps"]]
    assert "apply_supplement_review_pii_screening_decisions" in script_keys
    assert "gate_supplement_ocr_benchmark" in script_keys
    assert plan["external_provider_call_performed"] is False
    assert plan["training_execution_performed_by_script"] is False


def test_plan_rejects_raw_or_path_like_work_order_payload(tmp_path: Path) -> None:
    """Verify unsafe raw keys and paths cannot enter command-plan artifacts."""
    payload = {
        **_work_order_payload(batch_status="complete", blank_row_count=0),
        "raw_ocr_text": "do not expose",
    }
    work_order_path = _write_work_order(tmp_path / "work-order.json", payload)

    with pytest.raises(planner.PostCompletionPlanError, match="Unsafe key"):
        planner.build_post_completion_command_plan(
            input_paths={"work_order": work_order_path}
        )


def test_post_completion_plan_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    """Verify CLI writes redacted JSON and Markdown artifacts."""
    work_order_path = _write_work_order(
        tmp_path / "work-order.json",
        _work_order_payload(
            queue_key="yolo_section_annotation",
            batch_status="complete",
            blank_row_count=0,
        ),
    )
    output_path = tmp_path / "plan.json"
    markdown_path = tmp_path / "plan.md"

    planner.main(
        [
            "--work-order",
            str(work_order_path),
            "--output",
            str(output_path),
            "--markdown-output",
            str(markdown_path),
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert payload["schema_version"] == planner.SCHEMA_VERSION
    assert payload["post_completion_execution_allowed"] is True
    assert "promote_supplement_yolo_annotation_template" in markdown
    assert "/Users/" not in markdown
    assert "/Volumes/" not in markdown
    assert "raw_ocr_text" not in markdown
