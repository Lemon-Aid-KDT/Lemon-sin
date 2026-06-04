"""Tests for supplement operator next-batch work orders."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[4]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

work_order = importlib.import_module("scripts.build_supplement_operator_next_batch_work_order")


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    """Write a JSON fixture.

    Args:
        path: Destination path.
        payload: JSON payload.

    Returns:
        Written path.
    """
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return path


def _readiness() -> dict[str, Any]:
    """Return a readiness fixture.

    Returns:
        Readiness payload.
    """
    return {
        "schema_version": "supplement-learning-pipeline-readiness-v1",
        "overall_status": "in_progress_blocked_by_missing_or_invalid_artifacts",
        "stages": [
            {
                "stage_key": "brand_product_review",
                "status": "pending_operator_review",
                "next_operator_action": "complete_brand_product_human_review",
            },
            {
                "stage_key": "review_pii_screening",
                "status": "pending_operator_review",
                "next_operator_action": "apply_pii_screening_decisions",
            },
            {
                "stage_key": "yolo_section_annotation",
                "status": "pending_operator_review",
                "next_operator_action": "complete_supplement_section_bbox_review",
            },
        ],
        "db_write_performed": False,
        "external_provider_call_performed": False,
        "llm_call_performed": False,
        "training_execution_performed_by_script": False,
        "source_image_read_performed": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
    }


def _progress() -> dict[str, Any]:
    """Return a batch-progress fixture.

    Returns:
        Batch progress payload.
    """
    return {
        "schema_version": "supplement-operator-review-batch-progress-preflight-v1",
        "batch_count": 2,
        "complete_batch_count": 0,
        "pending_batch_count": 2,
        "invalid_batch_count": 0,
        "all_batches_complete": False,
        "next_incomplete_batch_key": "brand_product_review:001",
        "total_expected_row_count": 51,
        "total_valid_row_count": 0,
        "total_blank_row_count": 51,
        "total_pending_row_count": 0,
        "total_invalid_row_count": 0,
        "total_missing_row_count": 0,
        "batches": [
            {
                "batch_key": "brand_product_review:001",
                "queue_key": "brand_product_review",
                "batch_status": "pending",
                "row_index_start": 1,
                "row_index_end": 50,
                "expected_row_count": 50,
                "valid_row_count": 0,
                "blank_row_count": 50,
                "pending_row_count": 0,
                "invalid_row_count": 0,
                "missing_row_count": 0,
                "reason_counts": {"blank_decision": 50},
                "db_write_performed": False,
                "external_provider_call_performed": False,
                "llm_call_performed": False,
                "training_execution_performed_by_script": False,
                "source_image_read_performed": False,
                "raw_ocr_text_stored": False,
                "raw_provider_payload_stored": False,
                "absolute_paths_stored": False,
                "product_dir_literals_stored": False,
                "local_path_literals_stored": False,
            },
            {
                "batch_key": "review_pii_screening:001",
                "queue_key": "review_pii_screening",
                "batch_status": "pending",
                "row_index_start": 1,
                "row_index_end": 1,
                "expected_row_count": 1,
                "valid_row_count": 0,
                "blank_row_count": 1,
                "pending_row_count": 0,
                "invalid_row_count": 0,
                "missing_row_count": 0,
                "reason_counts": {"blank_decision": 1},
                "db_write_performed": False,
                "external_provider_call_performed": False,
                "llm_call_performed": False,
                "training_execution_performed_by_script": False,
                "source_image_read_performed": False,
                "raw_ocr_text_stored": False,
                "raw_provider_payload_stored": False,
                "absolute_paths_stored": False,
                "product_dir_literals_stored": False,
                "local_path_literals_stored": False,
            },
        ],
        "db_write_performed": False,
        "external_provider_call_performed": False,
        "llm_call_performed": False,
        "training_execution_performed_by_script": False,
        "source_image_read_performed": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
        "product_dir_literals_stored": False,
        "local_path_literals_stored": False,
    }


def _workpack() -> dict[str, Any]:
    """Return a workpack fixture.

    Returns:
        Workpack payload.
    """
    return {
        "schema_version": "supplement-operator-review-workpack-v1",
        "status": "ok",
        "batch_count": 2,
        "workpack_file_count": 3,
        "next_batch_key": "brand_product_review:001",
        "batch_workpacks": [
            {
                "batch_key": "brand_product_review:001",
                "queue_key": "brand_product_review",
                "workpack_file_name": "brand_product_review-001.md",
                "batch_file_name": "brand_product_review-001.jsonl",
                "batch_review_file_name": "brand_product_review-001.review.csv",
                "source_editable_file_name": "decisions.todo.jsonl",
                "row_index_start": 1,
                "row_index_end": 50,
                "pending_row_count": 50,
                "bundle_file_names": [
                    "decisions.todo.jsonl",
                    "review-index.html",
                    "README.md",
                    "review.csv",
                ],
                "contact_sheet_available": True,
                "contact_sheet_dir_name": "brand-detail-contact-sheet-001",
                "contact_sheet_file_names": [
                    "brand-detail-contact-sheet.html",
                    "README.md",
                    "brand-detail-contact-sheet.summary.json",
                ],
                "contact_sheet_reviewable_row_count": 50,
                "contact_sheet_rows_with_thumbnails": 50,
                "contact_sheet_rows_without_thumbnails": 0,
                "contact_sheet_thumbnail_count": 127,
                "operator_checklist": [
                    "fill_reviewed_manufacturer",
                    "fill_reviewed_product_name",
                    "set_approve_or_reject_decision",
                ],
                "source_rows_read": False,
                "source_image_read_performed": False,
                "db_write_performed": False,
                "external_provider_call_performed": False,
                "llm_call_performed": False,
                "training_execution_performed_by_script": False,
                "raw_ocr_text_stored": False,
                "raw_provider_payload_stored": False,
                "absolute_paths_stored": False,
                "product_dir_literals_stored": False,
                "local_path_literals_stored": False,
            }
        ],
        "source_rows_read": False,
        "source_image_read_performed": False,
        "db_write_performed": False,
        "external_provider_call_performed": False,
        "llm_call_performed": False,
        "training_execution_performed_by_script": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
        "product_dir_literals_stored": False,
        "local_path_literals_stored": False,
    }


def _input_paths(tmp_path: Path) -> dict[str, Path]:
    """Write default input fixtures.

    Args:
        tmp_path: Temporary directory.

    Returns:
        Input path mapping.
    """
    return {
        "readiness": _write_json(tmp_path / "readiness.json", _readiness()),
        "batch_progress": _write_json(tmp_path / "progress.json", _progress()),
        "workpack_summary": _write_json(tmp_path / "workpack.json", _workpack()),
    }


def test_build_next_batch_work_order_selects_pending_batch(tmp_path: Path) -> None:
    """Verify the next incomplete batch is summarized without row payloads."""
    summary = work_order.build_next_batch_work_order(input_paths=_input_paths(tmp_path))
    markdown = work_order.build_work_order_markdown(summary)
    dumped = json.dumps(summary, ensure_ascii=False) + markdown

    assert summary["schema_version"] == "supplement-operator-review-next-work-order-v1"
    assert summary["status"] == "pending_operator_review"
    assert summary["batch_key"] == "brand_product_review:001"
    assert summary["queue_key"] == "brand_product_review"
    assert summary["workpack_file_name"] == "brand_product_review-001.md"
    assert summary["batch_file_name"] == "brand_product_review-001.jsonl"
    assert summary["batch_review_file_name"] == "brand_product_review-001.review.csv"
    assert summary["contact_sheet_available"] is True
    assert summary["contact_sheet_dir_name"] == "brand-detail-contact-sheet-001"
    assert summary["contact_sheet_thumbnail_count"] == 127
    assert summary["blank_row_count"] == 50
    assert summary["total_blank_row_count"] == 51
    assert summary["reason_counts"] == {"blank_decision": 50}
    assert (
        "extract_reviewed_brand_decisions_for_partial_manifest_preview"
        in summary["post_completion_gates"]
    )
    assert "rerun_brand_decision_preflight" in summary["post_completion_gates"]
    assert "brand_product_review-001.jsonl" in markdown
    assert "brand_product_review-001.review.csv" in markdown
    assert "brand-detail-contact-sheet-001" in markdown
    assert "brand-detail-contact-sheet.html" in markdown
    assert "Rows with thumbnails" in markdown
    assert "extract_reviewed_brand_decisions_for_partial_manifest_preview" in markdown
    assert str(tmp_path) not in dumped
    assert "/Volumes/" not in dumped
    assert "raw provider" not in dumped.casefold()


def test_build_next_batch_work_order_includes_pii_reviewed_extract_gate(
    tmp_path: Path,
) -> None:
    """Verify PII batches instruct reviewed-only extraction before apply."""
    paths = _input_paths(tmp_path)
    progress = _progress()
    progress["next_incomplete_batch_key"] = "review_pii_screening:001"
    progress["batches"][0]["batch_status"] = "complete"
    progress["batches"][0]["valid_row_count"] = 50
    progress["batches"][0]["blank_row_count"] = 0
    _write_json(paths["batch_progress"], progress)

    workpack = _workpack()
    workpack["next_batch_key"] = "review_pii_screening:001"
    workpack["batch_workpacks"] = [
        {
            "batch_key": "review_pii_screening:001",
            "queue_key": "review_pii_screening",
            "workpack_file_name": "review_pii_screening-001.md",
            "batch_file_name": "review_pii_screening-001.jsonl",
            "source_editable_file_name": "decisions.todo.jsonl",
            "row_index_start": 1,
            "row_index_end": 1,
            "pending_row_count": 1,
            "bundle_file_names": ["decisions.todo.jsonl", "review-index.html", "README.md"],
            "operator_checklist": ["screen_review_image", "set_pii_decision"],
            "source_rows_read": False,
            "source_image_read_performed": False,
            "db_write_performed": False,
            "external_provider_call_performed": False,
            "llm_call_performed": False,
            "training_execution_performed_by_script": False,
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "absolute_paths_stored": False,
            "product_dir_literals_stored": False,
            "local_path_literals_stored": False,
        }
    ]
    _write_json(paths["workpack_summary"], workpack)

    summary = work_order.build_next_batch_work_order(input_paths=paths)
    markdown = work_order.build_work_order_markdown(summary)

    assert summary["batch_key"] == "review_pii_screening:001"
    assert summary["queue_key"] == "review_pii_screening"
    assert (
        "extract_reviewed_pii_decisions_for_partial_teacher_ocr_preview"
        in summary["post_completion_gates"]
    )
    assert "extract_reviewed_pii_decisions_for_partial_teacher_ocr_preview" in markdown


def test_build_next_batch_work_order_includes_yolo_reviewed_extract_gate(
    tmp_path: Path,
) -> None:
    """Verify YOLO batches instruct reviewed-only extraction before promotion."""
    paths = _input_paths(tmp_path)
    progress = _progress()
    progress["batch_count"] = 3
    progress["complete_batch_count"] = 2
    progress["pending_batch_count"] = 1
    progress["next_incomplete_batch_key"] = "yolo_section_annotation:001"
    progress["batches"][0]["batch_status"] = "complete"
    progress["batches"][0]["valid_row_count"] = 50
    progress["batches"][0]["blank_row_count"] = 0
    progress["batches"][1]["batch_status"] = "complete"
    progress["batches"][1]["valid_row_count"] = 1
    progress["batches"][1]["blank_row_count"] = 0
    progress["batches"].append(
        {
            "batch_key": "yolo_section_annotation:001",
            "queue_key": "yolo_section_annotation",
            "batch_status": "pending",
            "row_index_start": 1,
            "row_index_end": 10,
            "expected_row_count": 10,
            "valid_row_count": 0,
            "blank_row_count": 10,
            "pending_row_count": 0,
            "invalid_row_count": 0,
            "missing_row_count": 0,
            "reason_counts": {"blank_decision": 10},
            "db_write_performed": False,
            "external_provider_call_performed": False,
            "llm_call_performed": False,
            "training_execution_performed_by_script": False,
            "source_image_read_performed": False,
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "absolute_paths_stored": False,
            "product_dir_literals_stored": False,
            "local_path_literals_stored": False,
        }
    )
    _write_json(paths["batch_progress"], progress)

    workpack = _workpack()
    workpack["next_batch_key"] = "yolo_section_annotation:001"
    workpack["batch_workpacks"] = [
        {
            "batch_key": "yolo_section_annotation:001",
            "queue_key": "yolo_section_annotation",
            "workpack_file_name": "yolo_section_annotation-001.md",
            "batch_file_name": "yolo_section_annotation-001.jsonl",
            "source_editable_file_name": "annotation.todo.jsonl",
            "row_index_start": 1,
            "row_index_end": 10,
            "pending_row_count": 10,
            "bundle_file_names": [
                "annotation.todo.jsonl",
                "review-index.html",
                "README.md",
                "label-studio-tasks.json",
            ],
            "operator_checklist": ["draw_section_boxes", "set_training_export_allowed"],
            "source_rows_read": False,
            "source_image_read_performed": False,
            "db_write_performed": False,
            "external_provider_call_performed": False,
            "llm_call_performed": False,
            "training_execution_performed_by_script": False,
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "absolute_paths_stored": False,
            "product_dir_literals_stored": False,
            "local_path_literals_stored": False,
        }
    ]
    _write_json(paths["workpack_summary"], workpack)

    summary = work_order.build_next_batch_work_order(input_paths=paths)
    markdown = work_order.build_work_order_markdown(summary)

    assert summary["batch_key"] == "yolo_section_annotation:001"
    assert summary["queue_key"] == "yolo_section_annotation"
    assert (
        "extract_reviewed_yolo_annotations_for_partial_dataset_preview"
        in summary["post_completion_gates"]
    )
    assert "extract_reviewed_yolo_annotations_for_partial_dataset_preview" in markdown


def test_build_next_batch_work_order_rejects_batch_key_mismatch(tmp_path: Path) -> None:
    """Verify mismatched progress/workpack next batch keys fail closed."""
    paths = _input_paths(tmp_path)
    payload = _workpack()
    payload["next_batch_key"] = "review_pii_screening:001"
    _write_json(paths["workpack_summary"], payload)

    try:
        work_order.build_next_batch_work_order(input_paths=paths)
    except work_order.WorkOrderError as exc:
        assert "batch_key mismatch" in str(exc)
    else:
        raise AssertionError("mismatched next batch should fail closed")


def test_build_next_batch_work_order_rejects_unsafe_artifact(tmp_path: Path) -> None:
    """Verify unsafe payload keys are rejected before output generation."""
    paths = _input_paths(tmp_path)
    payload = _progress()
    payload["raw_ocr_text"] = "sensitive OCR"
    _write_json(paths["batch_progress"], payload)

    try:
        work_order.build_next_batch_work_order(input_paths=paths)
    except work_order.WorkOrderError as exc:
        assert "Unsafe" in str(exc)
    else:
        raise AssertionError("unsafe progress payload should fail closed")


def test_next_batch_work_order_cli_writes_json_and_markdown(
    tmp_path: Path,
    capsys: Any,
) -> None:
    """Verify CLI writes redacted JSON and Markdown artifacts."""
    paths = _input_paths(tmp_path)
    output_path = tmp_path / "work-order.json"
    markdown_path = tmp_path / "work-order.md"

    work_order.main(
        [
            "--readiness",
            str(paths["readiness"]),
            "--batch-progress",
            str(paths["batch_progress"]),
            "--workpack-summary",
            str(paths["workpack_summary"]),
            "--output",
            str(output_path),
            "--markdown-output",
            str(markdown_path),
        ]
    )

    captured = capsys.readouterr().out
    written = json.loads(output_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert written["batch_key"] == "brand_product_review:001"
    assert written["source_rows_read"] is False
    assert "brand_product_review:001" in markdown
    assert '"blank_row_count": 50' in captured
