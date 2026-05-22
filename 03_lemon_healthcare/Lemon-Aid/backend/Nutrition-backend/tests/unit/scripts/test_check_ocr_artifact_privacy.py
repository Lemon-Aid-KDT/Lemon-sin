"""Tests for generated OCR artifact privacy checks."""

from __future__ import annotations

import json
import subprocess
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


def test_scan_rejects_real_manifest_private_source_and_text(tmp_path: Path) -> None:
    """Verify committed real OCR manifests cannot keep raw text or source paths."""
    path = tmp_path / "real_manifest.json"
    path.write_text(
        json.dumps(
            {
                "kind": "real",
                "source_root": "$PRIVATE_SOURCE_ROOT",
                "items": [
                    {
                        "id": "real-1",
                        "image_path": "real_samples/real-1.jpg",
                        "source_path": "$PRIVATE_SOURCE_ROOT/raw.jpg",
                        "gt_text": "full label text",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    findings = privacy.scan_paths([path])

    assert [(finding.code, finding.detail) for finding in findings] == [
        ("forbidden_json_key", "key=source_root"),
        ("forbidden_json_key", "key=source_path"),
        ("forbidden_json_key", "key=gt_text"),
    ]


def test_scan_allows_synthetic_manifest_text(tmp_path: Path) -> None:
    """Verify synthetic fixtures may keep generated text for deterministic tests."""
    path = tmp_path / "synthetic_manifest.json"
    path.write_text(
        json.dumps(
            {
                "kind": "synthetic",
                "items": [
                    {
                        "id": "synthetic-1",
                        "gt_text": "generated non-sensitive fixture text",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert privacy.scan_paths([path]) == []


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


def test_scan_tracked_generated_artifacts_rejects_git_tracked_report(
    tmp_path: Path,
) -> None:
    """Verify generated OCR eval artifacts cannot remain tracked."""
    repo_root = _init_git_repo(tmp_path)
    artifact = repo_root / "outputs/generated/ocr-eval/report.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n", encoding="utf-8")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "seed")

    findings = privacy.scan_tracked_generated_artifacts(project_root=repo_root)

    assert [(finding.path.as_posix(), finding.code, finding.detail) for finding in findings] == [
        ("outputs/generated/ocr-eval/report.json", "tracked_generated_artifact", "git_tracked")
    ]


def test_scan_tracked_generated_artifacts_allows_ignored_untracked_report(
    tmp_path: Path,
) -> None:
    """Verify ignored generated artifacts may exist locally without being tracked."""
    repo_root = _init_git_repo(tmp_path)
    (repo_root / ".gitignore").write_text("outputs/generated/ocr-eval/\n", encoding="utf-8")
    artifact = repo_root / "outputs/generated/ocr-eval/report.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n", encoding="utf-8")
    _git(repo_root, "add", ".gitignore")
    _git(repo_root, "commit", "-m", "seed")

    assert privacy.scan_tracked_generated_artifacts(project_root=repo_root) == []


def test_main_reports_tracked_generated_artifact(tmp_path: Path, capsys) -> None:
    """Verify the CLI reports tracked generated artifacts with bounded details."""
    repo_root = _init_git_repo(tmp_path)
    artifact = repo_root / "outputs/generated/ocr-eval/report.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n", encoding="utf-8")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "seed")

    exit_code = privacy.main(
        [
            "--project-root",
            str(repo_root),
            "--check-tracked-generated",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "tracked_generated_artifact git_tracked" in captured.err


def _init_git_repo(tmp_path: Path) -> Path:
    """Create a minimal Git repo for tracked artifact tests."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _git(repo_root, "init")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test User")
    return repo_root


def _git(repo_root: Path, *args: str) -> None:
    """Run Git in a temporary test repo."""
    subprocess.run(("git", "-C", str(repo_root), *args), check=True, capture_output=True)
