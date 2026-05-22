"""Tests for Naver Tampermonkey OCR runner guardrails."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import run_naver_tampermonkey_ocr_eval as runner


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    """Write JSONL rows for tests."""
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_build_provider_runs_allows_local_paddle_with_llm_parse(tmp_path: Path) -> None:
    """Verify local PaddleOCR run plans are built without external opt-in."""
    manifest_path = tmp_path / "manifest.jsonl"
    _write_jsonl(
        manifest_path,
        [
            {
                "fixture_id": "detail-1",
                "section": "detail",
                "contains_personal_data": False,
                "external_transfer_allowed": True,
            }
        ],
    )

    runs = runner.build_provider_runs(
        manifest_path=manifest_path,
        output_root=tmp_path / "out",
        providers=("paddleocr",),
        env_file=tmp_path / ".env",
        python_executable=Path("/tmp/ocr-python"),
        llm_parse=True,
        allow_external_providers=False,
        allow_review_external=False,
    )

    assert len(runs) == 1
    run = runs[0]
    assert run.provider_id == "paddleocr_local"
    assert run.command[0] == "/tmp/ocr-python"
    assert run.python_executable == Path("/tmp/ocr-python")
    assert run.env_overrides["RUN_PADDLEOCR_PROBE"] == "1"
    assert "--llm-parse" in run.command
    redacted = json.dumps(run.redacted(), ensure_ascii=False)
    assert "api_key" not in redacted.lower()
    assert "secret" not in redacted.lower()


def test_external_provider_requires_explicit_allow_flag(tmp_path: Path) -> None:
    """Verify CLOVA/Google Vision cannot run without explicit external opt-in."""
    manifest_path = tmp_path / "manifest.jsonl"
    _write_jsonl(
        manifest_path,
        [
            {
                "fixture_id": "detail-1",
                "section": "detail",
                "contains_personal_data": False,
                "external_transfer_allowed": True,
            }
        ],
    )

    with pytest.raises(ValueError, match="External providers require"):
        runner.build_provider_runs(
            manifest_path=manifest_path,
            output_root=tmp_path / "out",
            providers=("clova",),
            env_file=None,
            python_executable=Path("/tmp/ocr-python"),
            llm_parse=False,
            allow_external_providers=False,
            allow_review_external=False,
        )


def test_review_rows_block_external_transfer_by_default(tmp_path: Path) -> None:
    """Verify review images are not externally transferred by default."""
    manifest_path = tmp_path / "manifest.jsonl"
    _write_jsonl(
        manifest_path,
        [
            {
                "fixture_id": "review-1",
                "section": "review",
                "contains_personal_data": False,
                "external_transfer_allowed": False,
            }
        ],
    )

    with pytest.raises(ValueError, match="Review image external transfer"):
        runner.build_provider_runs(
            manifest_path=manifest_path,
            output_root=tmp_path / "out",
            providers=("google_vision",),
            env_file=None,
            python_executable=Path("/tmp/ocr-python"),
            llm_parse=False,
            allow_external_providers=True,
            allow_review_external=False,
        )


def test_parse_provider_aliases_rejects_unknown_alias() -> None:
    """Verify unsupported provider aliases fail closed."""
    with pytest.raises(ValueError, match="Unsupported provider alias"):
        runner.parse_provider_aliases("paddleocr,unknown")


def test_run_provider_evaluations_resumes_complete_output(tmp_path: Path) -> None:
    """Verify resume skips a complete provider output without rerunning."""
    output_dir = tmp_path / "paddleocr-observations"
    output_dir.mkdir()
    _write_jsonl(
        output_dir / "supplement-ocr-observations.jsonl",
        [
            {
                "fixture_id": "detail-1",
                "provider": "paddleocr_local",
                "status": "completed",
                "text_non_empty": True,
            },
            {
                "fixture_id": "detail-2",
                "provider": "paddleocr_local",
                "status": "error",
                "error_code": "ocrerror",
            },
        ],
    )
    run = runner.ProviderRun(
        alias="paddleocr",
        provider_id="paddleocr_local",
        output_dir=output_dir,
        python_executable=Path("/tmp/ocr-python"),
        command=("/tmp/ocr-python", "collector.py"),
        env_overrides={},
    )
    calls: list[list[str]] = []

    def fake_runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    result = runner.run_provider_evaluations(
        [run],
        resume=True,
        manifest_rows=[{"fixture_id": "detail-1"}, {"fixture_id": "detail-2"}],
        runner=fake_runner,
    )

    assert calls == []
    assert result.completed_runs == [run]
    assert result.executed_runs == []
    assert result.resumed_runs == [run]


def test_run_provider_evaluations_reruns_not_run_output(tmp_path: Path) -> None:
    """Verify resume does not treat guard-skipped outputs as complete."""
    output_dir = tmp_path / "google_vision-observations"
    output_dir.mkdir()
    _write_jsonl(
        output_dir / "supplement-ocr-observations.jsonl",
        [
            {
                "fixture_id": "detail-1",
                "provider": "google_vision_document",
                "status": "not_run",
            }
        ],
    )
    run = runner.ProviderRun(
        alias="google_vision",
        provider_id="google_vision_document",
        output_dir=output_dir,
        python_executable=Path("/tmp/ocr-python"),
        command=("/tmp/ocr-python", "collector.py"),
        env_overrides={},
    )
    calls: list[list[str]] = []

    def fake_runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    result = runner.run_provider_evaluations(
        [run],
        resume=True,
        manifest_rows=[{"fixture_id": "detail-1"}],
        runner=fake_runner,
    )

    assert calls == [["/tmp/ocr-python", "collector.py"]]
    assert result.completed_runs == [run]
    assert result.executed_runs == [run]
    assert result.resumed_runs == []
