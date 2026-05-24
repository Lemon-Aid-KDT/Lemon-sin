"""Tests for the Naver Tampermonkey review import gate runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import run_naver_tampermonkey_review_import_gate as gate_runner


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    """Write JSONL test rows."""
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _review_row(**overrides: object) -> dict[str, object]:
    """Return a minimal review ingest row."""
    row: dict[str, object] = {
        "schema_version": "naver-tampermonkey-review-ingest-v1",
        "review_task_id": "d" * 64,
        "fixture_id": "naver-tm-detail-000001",
        "source": "naver_tampermonkey",
        "section": "detail",
        "product": {
            "product_id": "1234567890",
            "product_dir_hash": "c" * 64,
        },
        "category_key": "omega_3",
        "contains_personal_data": False,
        "pii_screening_status": "not_required_detail_page",
        "external_transfer_allowed": True,
        "local_processing_allowed": True,
        "requires_human_review": True,
        "is_clinical_recommendation": False,
        "clinical_recommendation_forbidden": True,
    }
    row.update(overrides)
    return row


def _decision_row(**overrides: object) -> dict[str, object]:
    """Return a valid approved decision row."""
    row: dict[str, object] = {
        "review_task_id": "d" * 64,
        "fixture_id": "naver-tm-detail-000001",
        "review_decision": {
            "status": "approved",
            "reviewer_id": "operator_1",
            "reviewed_at": "2026-05-24T14:30:00+09:00",
            "display_name": "Omega-3 1000",
            "manufacturer": "Reviewed Nutrition",
            "category_key": "omega_3",
            "attest_pii_screening_completed": True,
            "attest_no_raw_ocr_text": True,
            "attest_not_clinical_recommendation": True,
            "ingredients": [
                {
                    "display_name": "Omega-3",
                    "nutrient_code": "omega_3",
                    "amount": 1000,
                    "unit": "mg",
                    "source": "human_reviewed",
                }
            ],
        },
    }
    row.update(overrides)
    return row


def test_review_import_gate_allows_empty_decision_batch(tmp_path: Path) -> None:
    """Verify the gate keeps pending review rows out of DB import plans."""
    review_path = tmp_path / "review.jsonl"
    decisions_path = tmp_path / "decisions.jsonl"
    output_dir = tmp_path / "gate"
    _write_jsonl(review_path, [_review_row()])
    _write_jsonl(decisions_path, [])

    summary = gate_runner.run_review_import_gate(
        review_ingest_path=review_path,
        decisions_path=decisions_path,
        output_dir=output_dir,
        artifact_prefix="empty",
    )

    assert summary["review_row_count"] == 1
    assert summary["matched_decision_count"] == 0
    assert summary["pending_count"] == 1
    assert summary["approved_row_count"] == 0
    assert summary["planned_product_upsert_count"] == 0
    assert summary["planned_ingredient_row_count"] == 0
    assert summary["dry_run_only"] is True
    assert summary["db_write_performed"] is False
    assert (output_dir / "empty-review-ingest-with-decisions.jsonl").exists()
    assert (output_dir / "empty-approved-db-import.jsonl").read_text(encoding="utf-8") == ""
    serialized = json.dumps(summary, ensure_ascii=False).lower()
    assert '"raw_ocr_text"' not in serialized
    assert "/volumes/" not in serialized


def test_review_import_gate_exports_approved_rows_to_dry_run_plan(tmp_path: Path) -> None:
    """Verify an approved human decision reaches the ORM dry-run plan only."""
    review_path = tmp_path / "review.jsonl"
    decisions_path = tmp_path / "decisions.jsonl"
    output_dir = tmp_path / "gate"
    _write_jsonl(review_path, [_review_row()])
    _write_jsonl(decisions_path, [_decision_row()])

    summary = gate_runner.run_review_import_gate(
        review_ingest_path=review_path,
        decisions_path=decisions_path,
        output_dir=output_dir,
        artifact_prefix="approved",
        require_reviewed=True,
        require_all_approved=True,
    )

    assert summary["matched_decision_count"] == 1
    assert summary["pending_count"] == 0
    assert summary["approved_row_count"] == 1
    assert summary["planned_product_upsert_count"] == 1
    assert summary["planned_ingredient_row_count"] == 1
    plan_rows = [
        json.loads(line)
        for line in (output_dir / "approved-approved-db-import-dry-run.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert plan_rows[0]["product"]["table"] == "supplement_products"
    assert plan_rows[0]["ingredient_replace_plan"]["ingredient_count"] == 1
    assert plan_rows[0]["db_write_performed"] is False


def test_review_import_gate_can_require_all_rows_reviewed(tmp_path: Path) -> None:
    """Verify strict review mode fails when rows remain pending."""
    review_path = tmp_path / "review.jsonl"
    decisions_path = tmp_path / "decisions.jsonl"
    _write_jsonl(review_path, [_review_row()])
    _write_jsonl(decisions_path, [])

    with pytest.raises(ValueError, match="requires every row"):
        gate_runner.run_review_import_gate(
            review_ingest_path=review_path,
            decisions_path=decisions_path,
            output_dir=tmp_path / "gate",
            require_reviewed=True,
        )


def test_review_import_gate_rejects_unmatched_decisions_by_default(tmp_path: Path) -> None:
    """Verify decisions absent from the review queue fail closed by default."""
    review_path = tmp_path / "review.jsonl"
    decisions_path = tmp_path / "decisions.jsonl"
    _write_jsonl(review_path, [_review_row()])
    _write_jsonl(decisions_path, [_decision_row(review_task_id="e" * 64)])

    with pytest.raises(ValueError, match="not in review ingest"):
        gate_runner.run_review_import_gate(
            review_ingest_path=review_path,
            decisions_path=decisions_path,
            output_dir=tmp_path / "gate",
        )


def test_review_import_gate_rejects_unsafe_decision_payloads(tmp_path: Path) -> None:
    """Verify raw fields, local paths, and free-text decisions are rejected."""
    review_path = tmp_path / "review.jsonl"
    decisions_path = tmp_path / "decisions.jsonl"
    output_dir = tmp_path / "gate"
    _write_jsonl(review_path, [_review_row()])
    unsafe_decision = _decision_row()
    review_decision = dict(unsafe_decision["review_decision"])  # type: ignore[arg-type]
    review_decision["display_name"] = "/Volumes/Corsair EX400U Media/a.jpg"
    unsafe_decision["review_decision"] = review_decision
    _write_jsonl(decisions_path, [unsafe_decision])

    with pytest.raises(ValueError, match="local path literal"):
        gate_runner.run_review_import_gate(
            review_ingest_path=review_path,
            decisions_path=decisions_path,
            output_dir=output_dir,
        )

    assert not list(output_dir.glob("*.jsonl"))


def test_review_import_gate_main_error_is_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify CLI failures print a redacted JSON summary instead of traceback paths."""
    missing_review = tmp_path / "missing-review.jsonl"
    missing_decisions = tmp_path / "missing-decisions.jsonl"
    output_dir = tmp_path / "gate"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_naver_tampermonkey_review_import_gate.py",
            "--review-ingest",
            str(missing_review),
            "--decisions",
            str(missing_decisions),
            "--output-dir",
            str(output_dir),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        gate_runner.main()

    assert exc_info.value.code == 1
    stdout = capsys.readouterr().out
    summary = json.loads(stdout)
    assert summary["status"] == "error"
    assert summary["error_message"] == "Local file operation failed."
    assert str(tmp_path) not in stdout
    assert "/private/" not in stdout
