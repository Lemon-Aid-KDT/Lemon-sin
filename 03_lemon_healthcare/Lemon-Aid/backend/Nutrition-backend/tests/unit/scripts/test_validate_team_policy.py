"""Tests for standalone team-policy Git hook scripts."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def test_validate_commit_title_accepts_documented_shape() -> None:
    """Verify documented Conventional Commit titles are accepted."""
    commit = _load_module("validate_commit_msg")

    assert commit.validate_title("feat(ocr): 품질 게이트 추가") == []


def test_validate_commit_title_rejects_subject_period_and_scope() -> None:
    """Verify subject and scope rules are enforced."""
    commit = _load_module("validate_commit_msg")

    assert commit.validate_title("feat(bad): 품질 게이트 추가.") == [
        "Scope must be one of: mobile, backend, ai, ocr, db, auth, ux, infra, docs, team, test, data",
        "Subject must not end with a period.",
    ]


def test_validate_commit_title_rejects_missing_scope() -> None:
    """Verify scope is required by the team convention."""
    commit = _load_module("validate_commit_msg")

    assert commit.validate_title("feat: 품질 게이트 추가") == [
        "Use Conventional Commits: <type>(<scope>): <subject>",
        "Example: docs(team): 협업 규칙 문서 추가",
    ]


def test_validate_team_policy_accepts_feature_branch_to_develop() -> None:
    """Verify valid feature branch PRs to develop are accepted."""
    policy = _load_module("validate_team_policy")

    assert (
        policy.validate_branch(
            base="develop",
            branch="feat/ocr-quality-gates",
            event_name="pull_request",
        )
        == []
    )


def test_validate_team_policy_rejects_worker_name_branch() -> None:
    """Verify worker-name branches are rejected by shape."""
    policy = _load_module("validate_team_policy")

    assert policy.validate_branch(
        base="develop",
        branch="yeong-tech",
        event_name="pull_request",
    ) == [
        "PR branch must look like <type>/<scope>-<kebab-subject>, "
        "for example feat/ocr-quality-gates."
    ]


def test_validate_team_policy_rejects_direct_push_to_develop() -> None:
    """Verify direct pushes to protected branches fail."""
    policy = _load_module("validate_team_policy")

    assert policy.validate_branch(base="develop", branch="develop", event_name="push") == [
        "Direct push to develop is not allowed. Use a PR."
    ]


def _load_module(name: str) -> ModuleType:
    """Load one script from ``scripts/git-hooks``.

    Args:
        name: Module filename without ``.py``.

    Returns:
        Loaded module.
    """
    script_dir = Path(__file__).resolve().parents[5] / "scripts/git-hooks"
    module_path = script_dir / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"missing module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
