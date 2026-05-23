"""Tests for redacted OCR ground-truth review queue generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import build_ocr_ground_truth_review_queue as queue_builder


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    """Write JSONL rows.

    Args:
        path: Destination path.
        rows: Rows to serialize.
    """
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON object.

    Args:
        path: Destination path.
        payload: Object to serialize.
    """
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def test_build_review_queue_emits_bounded_human_actions(tmp_path: Path) -> None:
    """Verify queue rows include review actions without raw OCR/provider data."""
    manifest = tmp_path / "manifest.jsonl"
    evaluation = tmp_path / "evaluation.json"
    output_dir = tmp_path / "queue"
    _write_jsonl(
        manifest,
        [
            {
                "fixture_id": "fixture-empty",
                "image_path": "images/fixture-empty.jpg",
                "image_sha256": "a" * 64,
                "expected": {"ingredients": []},
                "observations": [
                    {
                        "provider": "paddleocr_local",
                        "status": "error",
                        "error_code": "ocr_empty_text",
                        "text_non_empty": False,
                        "layout_available": False,
                        "parsed_ingredients": [],
                    }
                ],
            },
            {
                "fixture_id": "fixture-ok",
                "image_path": "images/fixture-ok.jpg",
                "expected": {"ingredients": [{"display_name": "비타민 D"}]},
                "observations": [
                    {
                        "provider": "paddleocr_local",
                        "status": "completed",
                        "text_non_empty": True,
                        "layout_available": True,
                        "parsed_ingredients": [{"name": "비타민 D"}],
                    }
                ],
            },
        ],
    )
    _write_json(
        evaluation,
        {
            "expected_quality_warnings": [
                {
                    "fixture_id": "fixture-empty",
                    "code": "expected_ingredients_missing",
                },
                {
                    "fixture_id": "fixture-empty",
                    "code": "provisional_expected_fixture",
                },
            ],
            "unscoreable_fixture_ids": ["fixture-empty"],
        },
    )

    jsonl_path, markdown_path, queue = queue_builder.write_review_queue(
        manifest_path=manifest,
        evaluation_path=evaluation,
        output_dir=output_dir,
    )

    assert [item.fixture_id for item in queue] == ["fixture-empty"]
    row = json.loads(jsonl_path.read_text(encoding="utf-8").strip())
    assert row["review_reasons"] == [
        "expected_ingredients_missing",
        "provider_error:ocr_empty_text",
        "provisional_expected_fixture",
        "unscoreable_fixture",
    ]
    assert row["recommended_actions"] == [
        "add_human_reviewed_expected_ingredients",
        "clear_pending_review_after_manual_validation",
        "replace_non_label_or_empty_ocr_fixture",
    ]
    assert row["image_sha256_prefix"] == "a" * 12
    markdown = markdown_path.read_text(encoding="utf-8")
    serialized = json.dumps(row, ensure_ascii=False).lower() + markdown.lower()
    assert "raw_ocr_text" not in serialized
    assert "provider_payload" not in serialized
    assert "image_bytes" not in serialized


def test_build_review_queue_rejects_raw_manifest_fields(tmp_path: Path) -> None:
    """Verify raw OCR text cannot enter review queue inputs."""
    manifest = tmp_path / "manifest.jsonl"
    evaluation = tmp_path / "evaluation.json"
    _write_jsonl(
        manifest,
        [
            {
                "fixture_id": "fixture-raw",
                "expected": {},
                "observations": [
                    {
                        "provider": "paddleocr_local",
                        "raw_ocr_text": "secret",
                    }
                ],
            }
        ],
    )
    _write_json(evaluation, {"expected_quality_warnings": []})

    with pytest.raises(ValueError, match="raw_ocr_text"):
        queue_builder.build_review_queue(
            manifest_path=manifest,
            evaluation_path=evaluation,
        )
