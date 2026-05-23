"""Tests for redacted OCR error quality summaries."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from PIL import Image, ImageDraw


def _load_summary_module() -> ModuleType:
    """Load the repo-level OCR error summary script under test."""
    module_path = Path(__file__).resolve().parents[4] / "scripts/summarize_ocr_error_quality.py"
    spec = importlib.util.spec_from_file_location("summarize_ocr_error_quality", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"missing module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["summarize_ocr_error_quality"] = module
    spec.loader.exec_module(module)
    return module


summary_module = _load_summary_module()


def test_build_summary_reports_error_fixture_without_raw_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify OCR error quality reports omit raw paths and payload fields."""
    image_root = tmp_path / "images"
    image_root.mkdir()
    _write_label_like_image(image_root / "ok.png", size=(1000, 1000))
    _write_label_like_image(image_root / "error.png", size=(1000, 1000), low_contrast=True)
    monkeypatch.setenv("NAVER_TAMPERMONKEY_SOURCE_ROOT", str(image_root))
    manifest = tmp_path / "manifest.jsonl"
    observations = tmp_path / "observations.jsonl"
    _write_jsonl(
        manifest,
        [
            _manifest_row("fixture-ok", "$NAVER_TAMPERMONKEY_SOURCE_ROOT/ok.png"),
            _manifest_row("fixture-error", "$NAVER_TAMPERMONKEY_SOURCE_ROOT/error.png"),
        ],
    )
    _write_jsonl(
        observations,
        [
            {"fixture_id": "fixture-ok", "provider": "paddleocr_local", "status": "completed"},
            {
                "fixture_id": "fixture-error",
                "provider": "paddleocr_local",
                "status": "error",
                "error_code": "ocr_error",
            },
        ],
    )

    summary = summary_module.build_summary(
        manifest_path=manifest,
        observations_path=observations,
        provider="paddleocr_local",
    )

    assert summary["status_counts"] == {"completed": 1, "error": 1}
    assert summary["error_fixture_count"] == 1
    assert summary["error_fixtures"][0]["fixture_id"] == "fixture-error"
    serialized = json.dumps(summary, ensure_ascii=False)
    assert "image_path" not in serialized
    assert '"raw_ocr_text":' not in serialized
    assert str(image_root) not in serialized


def test_main_writes_json_and_markdown(tmp_path: Path, monkeypatch, capsys) -> None:
    """Verify CLI output is bounded and report files are created."""
    image_root = tmp_path / "images"
    image_root.mkdir()
    _write_label_like_image(image_root / "error.png", size=(1000, 1000), low_contrast=True)
    monkeypatch.setenv("NAVER_TAMPERMONKEY_SOURCE_ROOT", str(image_root))
    manifest = tmp_path / "manifest.jsonl"
    observations = tmp_path / "observations.jsonl"
    output_dir = tmp_path / "out"
    _write_jsonl(
        manifest,
        [_manifest_row("fixture-error", "$NAVER_TAMPERMONKEY_SOURCE_ROOT/error.png")],
    )
    _write_jsonl(
        observations,
        [
            {
                "fixture_id": "fixture-error",
                "provider": "paddleocr_local",
                "status": "error",
                "error_code": "ocr_error",
            }
        ],
    )

    exit_code = summary_module.main(
        [
            "--manifest",
            str(manifest),
            "--observations",
            str(observations),
            "--output-dir",
            str(output_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "error_fixture_count" in captured.out
    assert "NAVER_TAMPERMONKEY_SOURCE_ROOT" not in captured.out
    assert (output_dir / "ocr-error-quality-summary.json").exists()
    assert (output_dir / "ocr-error-quality-summary.md").exists()


def test_build_summary_rejects_unsafe_env_suffix(tmp_path: Path, monkeypatch) -> None:
    """Verify env-token image paths cannot traverse outside the image root."""
    monkeypatch.setenv("NAVER_TAMPERMONKEY_SOURCE_ROOT", str(tmp_path))
    manifest = tmp_path / "manifest.jsonl"
    observations = tmp_path / "observations.jsonl"
    row = _manifest_row("fixture-error", "$NAVER_TAMPERMONKEY_SOURCE_ROOT/../secret.png")
    _write_jsonl(manifest, [row])
    _write_jsonl(
        observations,
        [{"fixture_id": "fixture-error", "provider": "paddleocr_local", "status": "error"}],
    )

    try:
        summary_module.build_summary(
            manifest_path=manifest,
            observations_path=observations,
            provider="paddleocr_local",
        )
    except ValueError as exc:
        assert "suffix must stay under the image root" in str(exc)
    else:
        raise AssertionError("expected unsafe suffix rejection")


def _manifest_row(fixture_id: str, image_path: str) -> dict[str, object]:
    """Return a minimal redacted manifest row."""
    return {
        "fixture_id": fixture_id,
        "category": "[test]",
        "section": "detail",
        "image_path": image_path,
        "image_sha256": "0" * 64,
        "file_size_bytes": 100,
        "mime_type": "image/png",
        "width": 1000,
        "height": 1000,
        "size_bucket": "small",
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    """Write JSONL rows."""
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_label_like_image(
    path: Path,
    *,
    size: tuple[int, int],
    low_contrast: bool = False,
) -> None:
    """Create a synthetic image for quality-summary tests."""
    background = (235, 235, 235) if low_contrast else (255, 255, 255)
    foreground = (210, 210, 210) if low_contrast else (0, 0, 0)
    image = Image.new("RGB", size, background)
    draw = ImageDraw.Draw(image)
    for y in range(120, 820, 80):
        draw.rectangle((120, y, 880, y + 24), fill=foreground)
    image.save(path)
