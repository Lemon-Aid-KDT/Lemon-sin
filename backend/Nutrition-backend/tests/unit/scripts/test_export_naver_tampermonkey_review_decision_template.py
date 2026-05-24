"""Tests for exporting Naver Tampermonkey review decision templates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import export_naver_tampermonkey_review_decision_template as exporter


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
        "category_key": "omega_3",
        "category_display": {"ko": "오메가3", "en": "Omega-3"},
        "image": {"image_ref_hash": "b" * 64, "image_sha256": "a" * 64},
        "requires_human_review": True,
        "is_clinical_recommendation": False,
        "clinical_recommendation_forbidden": True,
        "ocr_observation_count": 1,
        "ingredient_candidate_count": 2,
        "ingredient_candidates": [
            {
                "display_name": "Omega-3",
                "nutrient_code": "omega_3",
                "amount": 1000.0,
                "unit": "mg",
                "confidence": 0.92,
                "source": "ollama_structured",
                "provider": "paddleocr_local",
            },
        ],
    }
    row.update(overrides)
    return row


def test_export_review_decision_templates_with_safe_contract(
    tmp_path: Path,
) -> None:
    """Verify review templates expose required decision contract fields."""
    input_path = tmp_path / "review.jsonl"
    _write_jsonl(input_path, [_review_row()])

    rows, summary = exporter.export_review_decision_template_rows(input_path=input_path)

    assert summary["row_count"] == 1
    assert summary["rows_with_candidate_hints"] == 1
    assert summary["total_candidate_hints"] == 1
    assert summary["decision_batch_importable"] is False
    row = rows[0]
    assert row["schema_version"] == exporter.SCHEMA_VERSION
    assert "review_decision" not in row
    assert row["review_task_id"] == "d" * 64
    contract = row["review_decision_contract"]
    assert isinstance(contract, dict)
    assert contract["approved_attestations_required"] == [
        "attest_pii_screening_completed",
        "attest_no_raw_ocr_text",
        "attest_not_clinical_recommendation",
    ]
    assert contract["free_text_notes_allowed"] is False
    assert contract["local_path_literals_allowed"] is False
    candidates = row["candidate_context"]["ingredient_candidates"]  # type: ignore[index]
    assert candidates[0]["display_name"] == "Omega-3"
    assert candidates[0]["amount"] == 1000.0
    serialized = json.dumps(rows, ensure_ascii=False).lower()
    assert '"raw_ocr_text"' not in serialized
    assert '"provider_payload"' not in serialized
    assert "/volumes/" not in serialized


def test_export_review_decision_templates_caps_candidate_hints(
    tmp_path: Path,
) -> None:
    """Verify candidate hints are bounded and remain hints only."""
    input_path = tmp_path / "review.jsonl"
    row = _review_row(
        ingredient_candidates=[
            {"display_name": "Omega-3"},
            {"display_name": "Vitamin D"},
        ]
    )
    _write_jsonl(input_path, [row])

    rows, summary = exporter.export_review_decision_template_rows(
        input_path=input_path,
        max_candidates=1,
    )

    candidates = rows[0]["candidate_context"]["ingredient_candidates"]  # type: ignore[index]
    assert len(candidates) == 1
    assert summary["max_candidates_per_row"] == 1


def test_export_review_decision_templates_rejects_unsafe_input(
    tmp_path: Path,
) -> None:
    """Verify raw fields and local path literals cannot enter templates."""
    input_path = tmp_path / "raw.jsonl"
    _write_jsonl(input_path, [_review_row(raw_ocr_text="do not persist")])

    with pytest.raises(ValueError, match="raw_ocr_text"):
        exporter.export_review_decision_template_rows(input_path=input_path)

    local_path = tmp_path / "local.jsonl"
    _write_jsonl(
        local_path,
        [_review_row(ingredient_candidates=[{"display_name": "/Volumes/Corsair/a.jpg"}])],
    )

    with pytest.raises(ValueError, match="local path literal"):
        exporter.export_review_decision_template_rows(input_path=local_path)


def test_export_review_decision_templates_requires_human_review_rows(
    tmp_path: Path,
) -> None:
    """Verify non-reviewable or clinical rows fail closed."""
    input_path = tmp_path / "not-reviewable.jsonl"
    _write_jsonl(input_path, [_review_row(requires_human_review=False)])

    with pytest.raises(ValueError, match="require human review"):
        exporter.export_review_decision_template_rows(input_path=input_path)

    clinical_path = tmp_path / "clinical.jsonl"
    _write_jsonl(clinical_path, [_review_row(is_clinical_recommendation=True)])

    with pytest.raises(ValueError, match="clinical recommendations"):
        exporter.export_review_decision_template_rows(input_path=clinical_path)


def test_export_review_decision_templates_rejects_duplicate_review_ids(
    tmp_path: Path,
) -> None:
    """Verify duplicate review task ids fail before template export."""
    input_path = tmp_path / "review.jsonl"
    _write_jsonl(input_path, [_review_row(), _review_row()])

    with pytest.raises(ValueError, match="Duplicate review_task_id"):
        exporter.export_review_decision_template_rows(input_path=input_path)
