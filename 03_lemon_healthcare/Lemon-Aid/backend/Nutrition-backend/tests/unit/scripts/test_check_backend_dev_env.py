"""Tests for the backend development environment doctor."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts import check_backend_dev_env as doctor


def test_run_checks_accepts_minimal_valid_project(tmp_path: Path) -> None:
    """Verify a project with required files and declared dev tools passes."""
    repo_root = _init_project(tmp_path)

    checks = doctor.run_checks(
        repo_root=repo_root,
        tool_modules={},
        python_version=(3, 13, 7),
    )

    assert all(check.ok for check in checks)


def test_run_checks_rejects_missing_dev_tool_declarations(tmp_path: Path) -> None:
    """Verify requirements-dev.txt must declare backend validation tools."""
    repo_root = _init_project(tmp_path)
    _write(repo_root / "backend/requirements-dev.txt", "-r requirements.txt\npytest>=8.0\n")

    checks = doctor.run_checks(
        repo_root=repo_root,
        tool_modules={},
        python_version=(3, 13, 7),
    )

    requirements_check = _find_check(checks, "requirements_dev")
    assert requirements_check.ok is False
    assert "missing_packages=black,ruff,mypy,pip-audit" in requirements_check.detail


def test_run_checks_rejects_tracked_local_artifacts(tmp_path: Path) -> None:
    """Verify tracked local-only files make the dev environment unsafe."""
    repo_root = _init_project(tmp_path)
    _write(repo_root / "backend/.env", "LOCAL_ONLY=true\n")
    _git(repo_root, "add", "-f", "backend/.env")
    _git(repo_root, "commit", "-m", "track env")

    checks = doctor.run_checks(
        repo_root=repo_root,
        tool_modules={},
        python_version=(3, 13, 7),
    )

    artifact_check = _find_check(checks, "tracked_local_artifacts")
    assert artifact_check.ok is False
    assert artifact_check.detail == "tracked=backend/.env"


def test_main_reports_bounded_failure(tmp_path: Path, capsys) -> None:
    """Verify CLI failures do not print local absolute paths."""
    repo_root = tmp_path / "project"
    repo_root.mkdir()

    exit_code = doctor.main(["--repo-root", str(repo_root)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "fail required_paths" in captured.err
    assert str(tmp_path) not in captured.err


def _find_check(checks: tuple[doctor.DevEnvCheck, ...], name: str) -> doctor.DevEnvCheck:
    """Return one named check.

    Args:
        checks: Check results.
        name: Check name.

    Returns:
        Matching check result.

    Raises:
        AssertionError: If the check is absent.
    """
    for check in checks:
        if check.name == name:
            return check
    raise AssertionError(f"missing check {name}")


def _init_project(tmp_path: Path) -> Path:
    """Create a minimal Lemon Aid-like project in a Git repo.

    Args:
        tmp_path: Pytest temporary directory.

    Returns:
        Project root.
    """
    repo_root = tmp_path / "project"
    repo_root.mkdir()
    _git(repo_root, "init")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test User")
    _write(
        repo_root / "backend/pyproject.toml",
        "\n".join(
            [
                "[project]",
                'requires-python = ">=3.13"',
                "",
            ]
        ),
    )
    _write(repo_root / "backend/requirements.txt", "fastapi>=0.110\n")
    _write(
        repo_root / "backend/requirements-dev.txt",
        "\n".join(
            [
                "-r requirements.txt",
                "black>=24.4",
                "ruff>=0.4",
                "mypy>=1.10",
                "pytest>=8.0",
                "pip-audit>=2.10,<3.0",
                "",
            ]
        ),
    )
    _write(repo_root / "backend/Nutrition-backend/src/__init__.py", "")
    _write(repo_root / "backend/Nutrition-backend/tests/__init__.py", "")
    _write(repo_root / "docs/team-collaboration/LOCAL_SETUP.md", "# setup\n")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "seed")
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
