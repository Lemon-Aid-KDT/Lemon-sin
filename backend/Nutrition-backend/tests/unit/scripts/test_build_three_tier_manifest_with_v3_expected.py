"""Tests for V3 expected snapshot manifest projection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import build_three_tier_manifest_with_v3_expected as builder


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    """Write JSONL rows.

    Args:
        path: Destination path.
        rows: JSON-serializable rows.
    """
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_v3_snapshot(
    path: Path,
    *,
    fixture_id: str,
    ingredients: list[dict[str, object]],
    chronic_targets: list[str] | None = None,
) -> None:
    """Write a schema-valid V3 snapshot for tests.

    Args:
        path: Snapshot destination.
        fixture_id: Fixture id used to build deterministic skeleton metadata.
        ingredients: V3 ingredient candidates.
        chronic_targets: Chronic disease indication tokens.
    """
    payload = {
        "schema_version": "supplement-parsed-snapshot-v3",
        "source": {
            "raw_image_stored": False,
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "raw_model_response_stored": False,
        },
        "fixture_id": fixture_id,
        "ingredients": ingredients,
        "warnings": [
            "ground_truth_pending_human_review",
            "category:테스트",
            "labels:live_naver,detail_page",
        ],
        "chronic_disease_indications": chronic_targets or [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def test_build_manifest_maps_live_fixture_to_v3_snapshot(tmp_path: Path) -> None:
    """Verify naver-live rows receive naver-chronic V3 expected data."""
    manifest_path = tmp_path / "manifest.jsonl"
    expected_dir = tmp_path / "expected"
    output_path = tmp_path / "out.jsonl"
    _write_jsonl(
        manifest_path,
        [
            {
                "fixture_id": "naver-live-0001",
                "image_path": "images/one.png",
                "expected": {"ingredients": [{"name": "정x 3개입("}]},
                "observations": [{"provider": "paddleocr_local", "parsed_ingredients": []}],
            }
        ],
    )
    _write_v3_snapshot(
        expected_dir / "naver-chronic-0001.snapshot_v3.json",
        fixture_id="naver-chronic-0001",
        ingredients=[
            {
                "display_name": "비타민 D",
                "normalized_name": "비타민 d",
                "nutrient_code_candidates": [],
                "amount": 25,
                "unit": "mcg",
                "daily_amount": None,
                "confidence": 0.8,
                "source": "ocr_llm_preview",
                "evidence_refs": [],
            }
        ],
        chronic_targets=["osteoporosis"],
    )

    summary = builder.build_manifest_with_v3_expected(
        manifest_path=manifest_path,
        expected_dir=expected_dir,
        output_path=output_path,
    )

    row = json.loads(output_path.read_text(encoding="utf-8").strip())
    assert summary.rows == 1
    assert summary.v3_expected_attached == 1
    assert summary.ingredient_count == 1
    assert summary.provisional_expected == 1
    assert row["fixture_id"] == "naver-live-0001"
    assert row["observations"] == [{"provider": "paddleocr_local", "parsed_ingredients": []}]
    assert row["expected"] == {
        "expected_source": "v3_snapshot",
        "expected_snapshot_id": "naver-chronic-0001",
        "expected_snapshot_schema": "supplement-parsed-snapshot-v3",
        "verification_status": "provisional",
        "ingredients": [
            {
                "display_name": "비타민 D",
                "normalized_name": "비타민 d",
                "amount": 25.0,
                "unit": "mcg",
                "source": "ocr_llm_preview",
                "confidence": 0.8,
            }
        ],
        "chronic_disease_indications": ["osteoporosis"],
        "warnings": [
            "ground_truth_pending_human_review",
            "category:테스트",
            "labels:live_naver,detail_page",
        ],
    }
    serialized = json.dumps(row, ensure_ascii=False).lower()
    assert "raw_ocr_text" not in serialized
    assert "provider_payload" not in serialized
    assert str(expected_dir) not in serialized


def test_build_manifest_rejects_raw_input_fields(tmp_path: Path) -> None:
    """Verify raw OCR text cannot be copied through by mistake."""
    manifest_path = tmp_path / "manifest.jsonl"
    _write_jsonl(
        manifest_path,
        [{"fixture_id": "naver-live-0001", "observations": [{"raw_ocr_text": "secret"}]}],
    )

    with pytest.raises(ValueError, match="raw_ocr_text"):
        builder.build_manifest_with_v3_expected(
            manifest_path=manifest_path,
            expected_dir=tmp_path / "expected",
            output_path=tmp_path / "out.jsonl",
        )


def test_build_manifest_fails_closed_on_missing_v3_snapshot(tmp_path: Path) -> None:
    """Verify missing expected snapshots fail instead of preserving stale expected data."""
    manifest_path = tmp_path / "manifest.jsonl"
    _write_jsonl(manifest_path, [{"fixture_id": "naver-live-0099"}])

    with pytest.raises(ValueError, match="missing V3 expected snapshot"):
        builder.build_manifest_with_v3_expected(
            manifest_path=manifest_path,
            expected_dir=tmp_path / "expected",
            output_path=tmp_path / "out.jsonl",
        )
