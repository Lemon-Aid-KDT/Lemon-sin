from __future__ import annotations

from pathlib import Path

import pytest

from scripts import export_medical_wiki_langsmith_eval as export_langsmith_eval

WORKSPACE_ROOT = Path(__file__).resolve().parents[6]
MEDICAL_WIKI_MANIFEST = WORKSPACE_ROOT / "MEDICAL-WIKI" / "manifest"
CHATBOT_EVAL_INPUTS = MEDICAL_WIKI_MANIFEST / "chatbot_answer_eval_inputs.jsonl"
EVIDENCE_BUNDLE_FIXTURES = MEDICAL_WIKI_MANIFEST / "evidence_bundle_adapter_fixtures.jsonl"

pytestmark = pytest.mark.skipif(
    not CHATBOT_EVAL_INPUTS.exists() or not EVIDENCE_BUNDLE_FIXTURES.exists(),
    reason="MEDICAL-WIKI manifest is managed outside this git worktree",
)


def test_claim_eval_export_keeps_row_count_and_excludes_raw_questions() -> None:
    rows = export_langsmith_eval.build_claim_eval_dataset(CHATBOT_EVAL_INPUTS)

    assert len(rows) == 84
    assert rows[0]["dataset"] == "medical_wiki_claim_boundary_eval"
    assert rows[0].keys() == {
        "dataset",
        "example_id",
        "inputs",
        "reference_outputs",
        "metadata",
    }
    assert rows[0]["inputs"].keys() == {"case_id", "expected_claim_id"}
    assert rows[0]["reference_outputs"]["claim_ids"]
    assert "query" not in rows[0]["inputs"]
    assert "raw_question" not in str(rows[0]).casefold()
    assert all(row["metadata"]["raw_fields_stored"] is False for row in rows)
    assert all(row["metadata"]["upload_allowed"] is False for row in rows)
    assert all(row["metadata"]["phi_free_review_required"] is True for row in rows)


def test_evidence_bundle_eval_export_keeps_row_count_and_source_ids_only() -> None:
    rows = export_langsmith_eval.build_evidence_bundle_dataset(EVIDENCE_BUNDLE_FIXTURES)

    assert len(rows) == 94
    assert rows[0]["dataset"] == "medical_wiki_evidence_bundle_eval"
    assert rows[0].keys() == {
        "dataset",
        "example_id",
        "inputs",
        "reference_outputs",
        "metadata",
    }
    assert rows[0]["inputs"].keys() == {"case_id", "expected_renderer_route"}
    assert "query" not in rows[0]["inputs"]
    assert rows[0]["reference_outputs"]["source_ids"]
    assert rows[0]["reference_outputs"]["claim_ids"]
    assert all(row["metadata"]["raw_fields_stored"] is False for row in rows)
    assert all(row["metadata"]["upload_allowed"] is False for row in rows)
    assert all(row["metadata"]["phi_free_review_required"] is True for row in rows)


def test_langsmith_eval_export_forbidden_marker_scan() -> None:
    rows = export_langsmith_eval.build_claim_eval_dataset(CHATBOT_EVAL_INPUTS)
    summary = export_langsmith_eval.evaluate_export_rows(rows)

    assert summary == {
        "status": "pass",
        "row_count": 84,
        "forbidden_marker_hits": 0,
        "raw_fields_stored": False,
        "upload_allowed_count": 0,
        "missing_required_ids": 0,
    }


def test_langsmith_eval_export_summary_fails_on_upload_or_missing_ids() -> None:
    rows = [
        {
            "dataset": "medical_wiki_claim_boundary_eval",
            "example_id": "case-1",
            "inputs": {"case_id": "case-1"},
            "reference_outputs": {"claim_ids": [], "source_ids": []},
            "metadata": {
                "upload_allowed": True,
                "raw_fields_stored": False,
                "phi_free_review_required": True,
                "cloud_or_self_hosted_gate_required": True,
            },
        }
    ]

    summary = export_langsmith_eval.evaluate_export_rows(rows)

    assert summary == {
        "status": "fail",
        "row_count": 1,
        "forbidden_marker_hits": 0,
        "raw_fields_stored": False,
        "upload_allowed_count": 1,
        "missing_required_ids": 1,
    }


def test_langsmith_eval_export_summary_fails_on_raw_markers() -> None:
    rows = [
        {
            "dataset": "medical_wiki_claim_boundary_eval",
            "example_id": "case-1",
            "inputs": {"case_id": "case-1"},
            "reference_outputs": {
                "claim_ids": ["claim-1"],
                "source_ids": ["source-1"],
                "note": "raw prompt",
            },
            "metadata": {
                "upload_allowed": False,
                "raw_fields_stored": True,
                "phi_free_review_required": True,
                "cloud_or_self_hosted_gate_required": True,
            },
        }
    ]

    summary = export_langsmith_eval.evaluate_export_rows(rows)

    assert summary == {
        "status": "fail",
        "row_count": 1,
        "forbidden_marker_hits": 1,
        "raw_fields_stored": True,
        "upload_allowed_count": 0,
        "missing_required_ids": 0,
    }
