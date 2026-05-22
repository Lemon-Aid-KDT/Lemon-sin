"""Tests for Lemon CI path audit."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def test_check_ci_paths_accepts_current_project_markers(tmp_path: Path) -> None:
    """Verify monorepo CI assets pass when they point to the current project."""
    checker = _load_checker()
    repo_root = tmp_path / "repo"
    project_root = repo_root / "03_lemon_healthcare/Lemon-Aid"
    _write_lemon_workflows(repo_root, "03_lemon_healthcare/Lemon-Aid")
    _write(
        repo_root / ".github/dependabot.yml",
        "directory: /03_lemon_healthcare/Lemon-Aid/backend\n",
    )
    _write(
        repo_root / ".github/PULL_REQUEST_TEMPLATE.md",
        "Check affected areas under 03_lemon_healthcare/Lemon-Aid.\n",
    )

    assert checker.check_ci_paths(repo_root=repo_root, project_root=project_root) == []


def test_check_ci_paths_rejects_stale_workflow_path(tmp_path: Path) -> None:
    """Verify stale CI paths are reported without printing path content."""
    checker = _load_checker()
    repo_root = tmp_path / "repo"
    project_root = repo_root / "03_lemon_healthcare/Lemon-Aid"
    _write(
        repo_root / ".github/workflows/17-lemon-backend-ci.yml",
        "working-directory: 03_lemon_healthcare/yeong-Lemon-Aid/backend\n",
    )

    findings = checker.check_ci_paths(repo_root=repo_root, project_root=project_root)

    assert [(item.path, item.code, item.detail) for item in findings] == [
        (
            ".github/workflows/17-lemon-backend-ci.yml",
            "missing_current_project_path",
            "expected_project_path",
        ),
        (
            ".github/workflows/17-lemon-backend-ci.yml",
            "stale_project_path",
            "marker=1",
        ),
    ]


def test_check_ci_paths_rejects_stale_optional_policy_file(tmp_path: Path) -> None:
    """Verify optional policy files are scanned for stale paths."""
    checker = _load_checker()
    repo_root = tmp_path / "repo"
    project_root = repo_root / "03_lemon_healthcare/Lemon-Aid"
    _write_lemon_workflows(repo_root, "03_lemon_healthcare/Lemon-Aid")
    _write(
        repo_root / ".github/PULL_REQUEST_TEMPLATE.md",
        "Check affected areas under 03_lemon_healthcare/yeong-Lemon-Aid.\n",
    )

    findings = checker.check_ci_paths(repo_root=repo_root, project_root=project_root)

    assert [(item.path, item.code, item.detail) for item in findings] == [
        (".github/PULL_REQUEST_TEMPLATE.md", "stale_project_path", "marker=1")
    ]


def test_check_ci_paths_rejects_local_absolute_path(tmp_path: Path) -> None:
    """Verify local absolute paths are rejected from CI assets."""
    checker = _load_checker()
    repo_root = tmp_path / "repo"
    project_root = repo_root / "03_lemon_healthcare/Lemon-Aid"
    _write(
        repo_root / ".github/workflows/17-lemon-docs-ci.yml",
        "\n".join(
            [
                "working-directory: 03_lemon_healthcare/Lemon-Aid",
                "debug-path: " + "/" + "Users/example/project",
            ]
        ),
    )

    findings = checker.check_ci_paths(repo_root=repo_root, project_root=project_root)

    assert [(item.path, item.code, item.detail) for item in findings] == [
        (".github/workflows/17-lemon-docs-ci.yml", "local_absolute_path", "marker=1")
    ]


def test_main_reports_bounded_failure(tmp_path: Path, capsys) -> None:
    """Verify CLI failures print bounded diagnostics."""
    checker = _load_checker()
    repo_root = tmp_path / "repo"
    project_root = repo_root / "03_lemon_healthcare/Lemon-Aid"
    _write(
        repo_root / ".github/workflows/17-lemon-mobile-ci.yml",
        "working-directory: 03_lemon_healthcare/yeong-Lemon-Aid/mobile/flutter_app\n",
    )

    exit_code = checker.main(
        [
            "--repo-root",
            str(repo_root),
            "--project-root",
            str(project_root),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert ".github/workflows/17-lemon-mobile-ci.yml: stale_project_path" in captured.err
    assert "/" + "Users/" not in captured.err


def _write_lemon_workflows(repo_root: Path, project_path: str) -> None:
    """Write minimal Lemon workflow files.

    Args:
        repo_root: Test repository root.
        project_path: Expected Lemon Aid project path marker.
    """
    for name, suffix in (
        ("17-lemon-backend-ci.yml", "backend"),
        ("17-lemon-mobile-ci.yml", "mobile/flutter_app"),
        ("17-lemon-docs-ci.yml", "docs"),
    ):
        _write(
            repo_root / ".github/workflows" / name,
            f"working-directory: {project_path}/{suffix}\n",
        )


def _write(path: Path, text: str) -> None:
    """Write fixture text.

    Args:
        path: Fixture path.
        text: File content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_checker() -> ModuleType:
    """Load the backend script without relying on PYTHONPATH layout.

    Returns:
        Loaded ``check_lemon_ci_paths`` module.
    """
    module_path = Path(__file__).resolve().parents[4] / "scripts/check_lemon_ci_paths.py"
    spec = importlib.util.spec_from_file_location("check_lemon_ci_paths", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"missing module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_lemon_ci_paths"] = module
    spec.loader.exec_module(module)
    return module
