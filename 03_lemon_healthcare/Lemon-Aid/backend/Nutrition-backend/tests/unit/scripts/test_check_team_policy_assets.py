"""Tests for team-policy asset checks."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def test_check_assets_accepts_complete_policy_files(tmp_path: Path) -> None:
    """Verify required team-policy assets pass with expected markers."""
    _write_policy_files(tmp_path)

    assert assets.check_assets(tmp_path) == []


def test_check_assets_rejects_missing_template(tmp_path: Path) -> None:
    """Verify missing PR template is reported with bounded output."""
    _write_policy_files(tmp_path)
    (tmp_path / ".github/PULL_REQUEST_TEMPLATE.md").unlink()

    findings = assets.check_assets(tmp_path)

    assert [(finding.path, finding.code, finding.detail) for finding in findings] == [
        (".github/PULL_REQUEST_TEMPLATE.md", "missing_required_file", "file_absent")
    ]


def test_check_assets_rejects_stale_workflow_path(tmp_path: Path) -> None:
    """Verify stale local workflow paths are blocked."""
    _write_policy_files(tmp_path)
    workflow = tmp_path / ".github/workflows/team-policy.yml"
    workflow.write_text(workflow.read_text(encoding="utf-8") + "\nyeong-Lemon-Aid\n")

    findings = assets.check_assets(tmp_path)

    assert [(finding.path, finding.code, finding.detail) for finding in findings] == [
        (".github/workflows/team-policy.yml", "forbidden_snippet", "marker=1")
    ]


def _write_policy_files(repo_root: Path) -> None:
    """Write minimal valid policy assets.

    Args:
        repo_root: Fixture repo root.
    """
    _write(
        repo_root / ".github/PULL_REQUEST_TEMPLATE.md",
        "\n".join(
            [
                "develop",
                "<type>/<scope>-<kebab-subject>",
                "<type>(<scope>): <subject>",
                "pre-commit run --all-files",
                "raw OCR text",
                "provider payload",
            ]
        ),
    )
    _write(
        repo_root / ".github/workflows/team-policy.yml",
        "\n".join(
            [
                "pull_request:",
                "push:",
                "contents: read",
                "backend/scripts/check_team_policy_assets.py",
                "scripts/git-hooks/validate_team_policy.py",
                "github.head_ref",
                "github.base_ref",
            ]
        ),
    )
    _write(repo_root / "scripts/git-hooks/validate_commit_msg.py", "print('ok')\n")
    _write(repo_root / "scripts/git-hooks/validate_team_policy.py", "print('ok')\n")


def _write(path: Path, text: str) -> None:
    """Write fixture text.

    Args:
        path: Fixture path.
        text: File content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_assets_module() -> ModuleType:
    """Load the backend script without relying on PYTHONPATH layout.

    Returns:
        Loaded ``check_team_policy_assets`` module.
    """
    module_path = Path(__file__).resolve().parents[4] / "scripts" / "check_team_policy_assets.py"
    spec = importlib.util.spec_from_file_location("check_team_policy_assets", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"missing module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_team_policy_assets"] = module
    spec.loader.exec_module(module)
    return module


assets = _load_assets_module()
