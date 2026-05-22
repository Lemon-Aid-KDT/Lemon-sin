"""Tests for the protected branch pre-push guard."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def test_guard_accepts_feature_branch_push() -> None:
    """Verify normal feature branch pushes are allowed."""
    guard = _load_guard()
    stdin_text = (
        "refs/heads/feat/ocr-quality-gates "
        + "1" * 40
        + " refs/heads/feat/ocr-quality-gates "
        + "2" * 40
        + "\n"
    )

    assert guard.validate_push(guard.parse_pre_push_stdin(stdin_text)) == []


def test_guard_rejects_direct_push_to_develop() -> None:
    """Verify direct protected-branch updates are blocked."""
    guard = _load_guard()
    stdin_text = "refs/heads/develop " + "1" * 40 + " refs/heads/develop " + "2" * 40 + "\n"

    errors = guard.validate_push(guard.parse_pre_push_stdin(stdin_text))

    assert errors == ["Direct update to protected branch is not allowed: develop"]


def test_guard_rejects_protected_branch_deletion() -> None:
    """Verify protected branch deletion is blocked."""
    guard = _load_guard()
    stdin_text = "delete " + "0" * 40 + " refs/heads/main " + "2" * 40 + "\n"

    errors = guard.validate_push(guard.parse_pre_push_stdin(stdin_text))

    assert errors == ["Direct delete to protected branch is not allowed: main"]


def test_guard_rejects_fallback_current_protected_branch() -> None:
    """Verify manual execution still catches protected current branches."""
    guard = _load_guard()

    errors = guard.validate_push([], fallback_branch="develop")

    assert errors == ["Direct push from protected branch is not allowed: develop"]


def test_main_reports_bounded_error(capsys) -> None:
    """Verify CLI errors do not print remote URLs or local paths."""
    guard = _load_guard()
    stdin_text = "refs/heads/main " + "1" * 40 + " refs/heads/main " + "2" * 40 + "\n"

    exit_code = guard.main(["origin", "https://example.invalid/repo.git"], stdin_text=stdin_text)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Protected branch push policy failed:" in captured.err
    assert "main" in captured.err
    assert "example.invalid" not in captured.err
    assert "/" + "Users/" not in captured.err


def _load_guard() -> ModuleType:
    """Load the guard script without relying on PYTHONPATH layout."""
    module_path = (
        Path(__file__).resolve().parents[5] / "scripts/git-hooks/guard_protected_branch.py"
    )
    spec = importlib.util.spec_from_file_location("guard_protected_branch", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"missing module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["guard_protected_branch"] = module
    spec.loader.exec_module(module)
    return module
