"""Tests for PR export base checks."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts import check_pr_export_base as checker


def test_check_base_ref_accepts_code_bearing_clean_ref(tmp_path: Path) -> None:
    """Verify a base ref with required files and no artifacts passes."""
    repo_root = _init_git_repo(tmp_path)
    _write(repo_root / "backend/Nutrition-backend/src/ocr/field_extractor.py", "# ok\n")
    _write(
        repo_root / "backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py",
        "# ok\n",
    )
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "seed")

    result = checker.check_base_ref(
        repo_root=repo_root,
        base_ref="HEAD",
        required_paths=checker.DEFAULT_REQUIRED_PATHS,
        forbidden_prefixes=checker.DEFAULT_FORBIDDEN_PREFIXES,
    )

    assert result.ok is True


def test_check_base_ref_rejects_skeleton_ref(tmp_path: Path) -> None:
    """Verify a skeleton branch without OCR code is rejected."""
    repo_root = _init_git_repo(tmp_path)
    _write(repo_root / "backend/src/README.md", "skeleton\n")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "seed")

    result = checker.check_base_ref(
        repo_root=repo_root,
        base_ref="HEAD",
        required_paths=checker.DEFAULT_REQUIRED_PATHS,
        forbidden_prefixes=checker.DEFAULT_FORBIDDEN_PREFIXES,
    )

    assert result.ok is False
    assert result.missing_required_paths == checker.DEFAULT_REQUIRED_PATHS


def test_check_base_ref_rejects_generated_ocr_artifacts(tmp_path: Path) -> None:
    """Verify existing generated OCR artifacts make the base unsafe."""
    repo_root = _init_git_repo(tmp_path)
    _write(repo_root / "backend/Nutrition-backend/src/ocr/field_extractor.py", "# ok\n")
    _write(
        repo_root / "backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py",
        "# ok\n",
    )
    _write(repo_root / "outputs/generated/ocr-eval/report.json", "{}\n")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "seed")

    result = checker.check_base_ref(
        repo_root=repo_root,
        base_ref="HEAD",
        required_paths=checker.DEFAULT_REQUIRED_PATHS,
        forbidden_prefixes=checker.DEFAULT_FORBIDDEN_PREFIXES,
    )

    assert result.ok is False
    assert result.missing_required_paths == ()
    assert result.forbidden_paths == ("outputs/generated/ocr-eval/report.json",)


def test_check_base_ref_accepts_monorepo_prefixed_project_tree(tmp_path: Path) -> None:
    """Verify project-relative paths work when the tree is nested in a monorepo."""
    repo_root = _init_git_repo(tmp_path)
    project_root = repo_root / "03_lemon_healthcare/Lemon-Aid"
    _write(project_root / "backend/Nutrition-backend/src/ocr/field_extractor.py", "# ok\n")
    _write(
        project_root / "backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py",
        "# ok\n",
    )
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "seed")

    result = checker.check_base_ref(
        repo_root=repo_root,
        project_root=project_root,
        base_ref="HEAD",
        required_paths=checker.DEFAULT_REQUIRED_PATHS,
        forbidden_prefixes=checker.DEFAULT_FORBIDDEN_PREFIXES,
    )

    assert result.ok is True


def test_check_base_ref_rejects_monorepo_prefixed_generated_artifacts(
    tmp_path: Path,
) -> None:
    """Verify generated OCR artifacts are blocked in nested project trees."""
    repo_root = _init_git_repo(tmp_path)
    project_root = repo_root / "03_lemon_healthcare/Lemon-Aid"
    _write(project_root / "backend/Nutrition-backend/src/ocr/field_extractor.py", "# ok\n")
    _write(
        project_root / "backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py",
        "# ok\n",
    )
    _write(project_root / "outputs/generated/ocr-eval/report.json", "{}\n")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "seed")

    result = checker.check_base_ref(
        repo_root=repo_root,
        project_root=project_root,
        base_ref="HEAD",
        required_paths=checker.DEFAULT_REQUIRED_PATHS,
        forbidden_prefixes=checker.DEFAULT_FORBIDDEN_PREFIXES,
    )

    assert result.ok is False
    assert result.missing_required_paths == ()
    assert result.forbidden_paths == (
        "03_lemon_healthcare/Lemon-Aid/outputs/generated/ocr-eval/report.json",
    )


def test_main_reports_missing_path(tmp_path: Path, capsys) -> None:
    """Verify the CLI returns nonzero with bounded diagnostics."""
    repo_root = _init_git_repo(tmp_path)
    _write(repo_root / "README.md", "skeleton\n")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "seed")

    exit_code = checker.main(["--repo-root", str(repo_root), "--base-ref", "HEAD"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing_required_path ref=HEAD" in captured.err


def _init_git_repo(tmp_path: Path) -> Path:
    """Create a minimal Git repo for tests.

    Args:
        tmp_path: Pytest temporary directory.

    Returns:
        Git repository root.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _git(repo_root, "init")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test User")
    return repo_root


def _write(path: Path, text: str) -> None:
    """Write text and create parent directories.

    Args:
        path: File path.
        text: Text to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(repo_root: Path, *args: str) -> None:
    """Run Git in a temporary test repo.

    Args:
        repo_root: Git repository root.
        *args: Git arguments after ``git``.
    """
    subprocess.run(("git", "-C", str(repo_root), *args), check=True, capture_output=True)
