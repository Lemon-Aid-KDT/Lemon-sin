"""Tests for OCR artifact privacy checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import check_ocr_artifact_privacy as privacy


def _write_json(path: Path, value: object) -> None:
    """Write a JSON test artifact."""
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    """Write a JSONL test artifact."""
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_check_artifact_privacy_passes_redacted_json_and_jsonl(tmp_path: Path) -> None:
    """Verify redacted JSON/JSONL artifacts pass."""
    _write_json(
        tmp_path / "summary.json",
        {
            "image_path": "$NAVER_SOURCE_ROOT/detail.jpg",
            "raw_ocr_text_stored": False,
            "root_token": "$NAVER_SOURCE_ROOT",
        },
    )
    _write_jsonl(
        tmp_path / "rows.jsonl",
        [
            {
                "fixture_id": "naver-tm-detail-000001",
                "text_hash": "a" * 64,
                "candidate_context": {"ingredient_candidates": [{"display_name": "Omega-3"}]},
            }
        ],
    )

    summary = privacy.check_artifact_privacy(paths=[tmp_path])

    assert summary["file_count"] == 2
    assert summary["finding_count"] == 0
    assert summary["passed"] is True
    assert summary["db_write_performed"] is False
    assert summary["external_transfer_performed"] is False


def test_check_artifact_privacy_strict_mode_rejects_literal_keys(
    tmp_path: Path,
) -> None:
    """Verify strict mode can reject source-manifest path keys."""
    _write_json(tmp_path / "source-manifest.json", {"image_path": "$ROOT/detail.jpg"})

    summary = privacy.check_artifact_privacy(
        paths=[tmp_path],
        strict_literal_keys=True,
    )

    assert summary["passed"] is False
    assert summary["findings"][0]["reason"] == "forbidden_literal_key:image_path"


def test_check_artifact_privacy_rejects_forbidden_raw_keys(tmp_path: Path) -> None:
    """Verify raw OCR/provider payload keys fail."""
    _write_json(tmp_path / "bad.json", {"nested": {"raw_ocr_text": "secret"}})

    summary = privacy.check_artifact_privacy(paths=[tmp_path])

    assert summary["passed"] is False
    assert summary["finding_count"] == 1
    assert summary["findings"][0]["reason"] == "forbidden_raw_key:raw_ocr_text"


def test_check_artifact_privacy_rejects_local_path_literals(tmp_path: Path) -> None:
    """Verify generated artifacts cannot store local absolute paths."""
    _write_jsonl(
        tmp_path / "bad.jsonl",
        [{"image_ref": "/Volumes/Corsair EX400U Media/raw.jpg"}],
    )

    summary = privacy.check_artifact_privacy(paths=[tmp_path])

    assert summary["passed"] is False
    assert summary["findings"][0]["reason"] == "local_path_literal"


def test_check_artifact_privacy_reports_invalid_jsonl(tmp_path: Path) -> None:
    """Verify malformed JSONL is reported as a finding."""
    (tmp_path / "bad.jsonl").write_text('{"ok": true}\n{bad}\n', encoding="utf-8")

    summary = privacy.check_artifact_privacy(paths=[tmp_path])

    assert summary["passed"] is False
    assert summary["findings"][0]["reason"].startswith("invalid_jsonl:")


def test_check_artifact_privacy_handles_missing_paths(tmp_path: Path) -> None:
    """Verify missing paths can fail or be explicitly skipped."""
    missing = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        privacy.check_artifact_privacy(paths=[missing])

    summary = privacy.check_artifact_privacy(paths=[missing], allow_missing=True)
    assert summary["file_count"] == 0
    assert summary["passed"] is True
