"""Tests for redacted OCR fixture input inspection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

from scripts import inspect_ocr_fixture_inputs as inspector


def _write_manifest_row(path: Path, row: dict[str, object]) -> None:
    """Write one JSONL manifest row.

    Args:
        path: Destination path.
        row: Manifest row.
    """
    path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")


def test_inspect_manifest_inputs_reports_bounded_image_metadata(tmp_path: Path) -> None:
    """Verify image inspection returns metadata without local paths or raw bytes."""
    image_path = tmp_path / "fixture.jpg"
    Image.new("RGB", (20, 10), color=(255, 255, 255)).save(image_path, format="JPEG")
    manifest_path = tmp_path / "manifest.jsonl"
    _write_manifest_row(
        manifest_path,
        {
            "fixture_id": "fixture-1",
            "image_path": str(image_path),
            "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
            "license_status": "team_approved",
            "consent_status": "team_approved",
            "contains_personal_data": False,
            "external_transfer_allowed": True,
            "local_processing_allowed": True,
            "expected": {},
        },
    )

    summary = inspector.inspect_manifest_inputs(
        manifest_path=manifest_path,
        fixture_ids={"fixture-1"},
    )

    assert summary["raw_artifacts_stored"] is False
    assert summary["raw_ocr_text_stored"] is False
    assert summary["inspected_fixture_count"] == 1
    fixture = summary["fixtures"][0]  # type: ignore[index]
    assert fixture == {
        "fixture_id": "fixture-1",
        "status": "ok",
        "file_size_bytes": image_path.stat().st_size,
        "format": "JPEG",
        "mime_type": "image/jpeg",
        "width": 20,
        "height": 10,
        "mode": "RGB",
        "megapixels": 0.0002,
        "sha256_verified": True,
    }
    serialized_summary = json.dumps(summary, ensure_ascii=False).lower()
    serialized_fixture = json.dumps(fixture, ensure_ascii=False).lower()
    assert str(tmp_path).lower() not in serialized_summary
    assert "image_bytes" not in serialized_summary
    assert "raw_ocr_text" not in serialized_fixture


def test_main_writes_redacted_output_file(tmp_path: Path) -> None:
    """Verify CLI output file contains only bounded metadata."""
    image_path = tmp_path / "fixture.png"
    Image.new("RGB", (8, 4), color=(255, 255, 255)).save(image_path, format="PNG")
    manifest_path = tmp_path / "manifest.jsonl"
    output_path = tmp_path / "inspection.json"
    _write_manifest_row(
        manifest_path,
        {
            "fixture_id": "fixture-1",
            "image_path": str(image_path),
            "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
            "license_status": "team_approved",
            "consent_status": "team_approved",
            "contains_personal_data": False,
            "external_transfer_allowed": True,
            "local_processing_allowed": True,
            "expected": {},
        },
    )

    exit_code = inspector.main(
        [
            "--manifest",
            str(manifest_path),
            "--fixture-id",
            "fixture-1",
            "--output",
            str(output_path),
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["fixtures"][0]["mime_type"] == "image/png"
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert str(tmp_path).lower() not in serialized
