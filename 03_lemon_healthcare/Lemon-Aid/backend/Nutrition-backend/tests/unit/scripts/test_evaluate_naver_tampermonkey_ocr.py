"""Tests for Naver Tampermonkey OCR/Ollama coverage evaluation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import evaluate_naver_tampermonkey_ocr as evaluate


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    """Write JSONL rows for tests.

    Args:
        path: Destination path.
        rows: JSON-serializable rows.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_evaluate_manifest_aggregates_provider_section_and_category(
    tmp_path: Path,
) -> None:
    """Verify provider metrics are grouped without ground-truth accuracy claims."""
    manifest_path = tmp_path / "manifest.jsonl"
    obs_path = tmp_path / "paddle" / "supplement-ocr-observations.jsonl"
    _write_jsonl(
        manifest_path,
        [
            {
                "fixture_id": "detail-1",
                "section": "detail",
                "category": "[오메가3]",
                "product_id": "111",
                "mime_type": "image/jpeg",
                "size_bucket": "small",
            },
            {
                "fixture_id": "review-1",
                "section": "review",
                "category": "[비타민C]",
                "product_id": "222",
                "mime_type": "image/jpeg",
                "size_bucket": "small",
            },
        ],
    )
    _write_jsonl(
        obs_path,
        [
            {
                "fixture_id": "detail-1",
                "provider": "paddleocr_local",
                "status": "completed",
                "latency_ms": 100,
                "text_non_empty": True,
                "char_count": 120,
                "parser_success": True,
                "llm_parse_status": "completed",
                "llm_parsed_ingredient_count": 2,
            },
            {
                "fixture_id": "review-1",
                "provider": "paddleocr_local",
                "status": "completed",
                "latency_ms": 200,
                "text_non_empty": False,
                "char_count": 0,
                "parser_success": False,
                "llm_parse_status": "skipped_pii_screening_required",
                "pii_candidate_flags": ["phone_candidate", "order_number_candidate"],
            },
        ],
    )

    summary = evaluate.evaluate_manifest(
        manifest_path=manifest_path,
        observation_paths=(obs_path,),
    )

    assert summary["fixture_count"] == 2
    assert summary["observation_count"] == 2
    assert summary["raw_ocr_text_stored"] is False
    providers = summary["providers"]
    assert isinstance(providers, dict)
    paddle = providers["paddleocr_local"]
    assert paddle["call_count"] == 2
    assert paddle["completed_rate"] == 1.0
    assert paddle["text_non_empty_rate"] == 0.5
    assert paddle["llm_parse_attempt_count"] == 1
    assert paddle["llm_parse_success_rate"] == 1.0
    assert paddle["ingredient_count_avg"] == 2.0
    assert paddle["latency_ms_p50"] == pytest.approx(150.0)
    assert paddle["pii_candidate_flag_counts"] == {
        "order_number_candidate": 1,
        "phone_candidate": 1,
    }

    by_section = summary["by_section"]
    assert isinstance(by_section, dict)
    assert by_section["detail"]["paddleocr_local"]["text_non_empty_rate"] == 1.0
    assert by_section["review"]["paddleocr_local"]["text_non_empty_rate"] == 0.0
    assert summary["by_product"]["111"]["paddleocr_local"]["call_count"] == 1
    assert summary["by_mime_type"]["image/jpeg"]["paddleocr_local"]["call_count"] == 2
    assert summary["by_size_bucket"]["small"]["paddleocr_local"]["call_count"] == 2


def test_evaluate_rejects_raw_ocr_text(tmp_path: Path) -> None:
    """Verify raw OCR text cannot enter evaluation inputs."""
    manifest_path = tmp_path / "manifest.jsonl"
    obs_path = tmp_path / "obs.jsonl"
    _write_jsonl(manifest_path, [{"fixture_id": "detail-1", "section": "detail"}])
    _write_jsonl(
        obs_path,
        [{"fixture_id": "detail-1", "provider": "paddleocr_local", "raw_ocr_text": "secret"}],
    )

    with pytest.raises(ValueError, match="raw_ocr_text"):
        evaluate.evaluate_manifest(
            manifest_path=manifest_path,
            observation_paths=(obs_path,),
        )


def test_render_markdown_omits_raw_content() -> None:
    """Verify Markdown renderer reports only aggregate metrics."""
    markdown = evaluate.render_markdown(
        {
            "generated_at": "2026-05-22T00:00:00+00:00",
            "manifest": "manifest.jsonl",
            "fixture_count": 1,
            "observation_count": 1,
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "raw_model_response_stored": False,
            "providers": {
                "paddleocr_local": {
                    "call_count": 1,
                    "completed_rate": 1.0,
                    "text_non_empty_rate": 1.0,
                    "llm_parse_success_rate": 1.0,
                    "latency_ms_p50": 100,
                    "latency_ms_p95": 100,
                }
            },
            "by_section": {},
            "by_category": {},
            "by_product": {},
            "by_mime_type": {},
            "by_size_bucket": {},
        }
    )

    assert "paddleocr_local" in markdown
    assert "## Product Metrics" in markdown
    assert "## MIME Type Metrics" in markdown
    assert "## Size Bucket Metrics" in markdown
    assert "raw_ocr_text" not in markdown
    assert "secret" not in markdown
