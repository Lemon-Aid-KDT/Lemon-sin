"""Tests for generated OCR artifact privacy checks."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import check_ocr_artifact_privacy as privacy


def test_scan_accepts_redacted_observation_jsonl(tmp_path: Path) -> None:
    """Verify redacted OCR observations pass the privacy gate."""
    path = tmp_path / "supplement-ocr-observations.jsonl"
    path.write_text(
        json.dumps(
            {
                "fixture_id": "fixture-1",
                "provider": "clova_ocr",
                "status": "completed",
                "text_hash": "0" * 64,
                "char_count": 120,
                "raw_ocr_text_stored": False,
                "raw_provider_payload_stored": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert privacy.scan_paths([path]) == []


def test_scan_rejects_forbidden_json_key(tmp_path: Path) -> None:
    """Verify raw OCR text keys are blocked even when nested."""
    path = tmp_path / "artifact.json"
    path.write_text(
        json.dumps({"fixture_id": "fixture-1", "nested": {"raw_ocr_text": "redacted"}}),
        encoding="utf-8",
    )

    findings = privacy.scan_paths([path])

    assert [(finding.code, finding.detail) for finding in findings] == [
        ("forbidden_json_key", "key=raw_ocr_text")
    ]


def test_scan_rejects_local_path_and_secret_assignment(tmp_path: Path) -> None:
    """Verify local absolute paths and populated secret assignments are blocked."""
    path = tmp_path / "report.md"
    path.write_text(
        "\n".join(
            [
                "root=/Users/example/project",
                "CLOVA_OCR_SECRET=real-secret-value",
            ]
        ),
        encoding="utf-8",
    )

    findings = privacy.scan_paths([path])

    assert [finding.code for finding in findings] == [
        "developer_home_path",
        "clova_secret_assignment",
    ]


def test_main_reports_success_for_empty_directory(tmp_path: Path, capsys) -> None:
    """Verify the CLI returns success for a directory with no findings."""
    path = tmp_path / "summary.md"
    path.write_text("raw_ocr_text_stored=false\n", encoding="utf-8")

    exit_code = privacy.main([str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "ocr_artifact_privacy_ok files=1" in captured.out
