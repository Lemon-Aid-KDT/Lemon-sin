"""Tests for bounded GitHub branch protection audit."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def test_audit_accepts_publicly_protected_branches() -> None:
    """Verify protected branches with enforced checks pass."""
    payloads = {
        "/branches/develop": _branch_payload(
            protected=True, enabled=True, enforcement="non_admins"
        ),
        "/branches/main": _branch_payload(protected=True, enabled=True, enforcement="everyone"),
        "/rulesets": [],
    }

    result = protection.audit_repository(
        repo="Lemon-Aid-KDT/Lemon-sin",
        branches=("develop", "main"),
        api_base="https://example.invalid",
        fetch_json=_fetcher(payloads),
    )

    assert result.ok
    assert [state.branch for state in result.states] == ["develop", "main"]
    assert result.rulesets is not None
    assert result.rulesets.total_count == 0


def test_audit_rejects_unprotected_branch_metadata() -> None:
    """Verify disabled branch protection is reported without raw API payloads."""
    payloads = {
        "/branches/develop": _branch_payload(protected=False, enabled=False, enforcement="off"),
        "/rulesets": [],
    }

    result = protection.audit_repository(
        repo="Lemon-Aid-KDT/Lemon-sin",
        branches=("develop",),
        api_base="https://example.invalid",
        fetch_json=_fetcher(payloads),
    )

    assert [(item.target, item.code, item.detail) for item in result.findings] == [
        ("develop", "branch_unprotected", "protected=false"),
        ("develop", "branch_protection_disabled", "protection.enabled=false"),
        ("develop", "required_status_checks_not_enforced", "enforcement=off"),
    ]


def test_ruleset_summary_counts_active_branch_rulesets_only() -> None:
    """Verify repository rulesets are summarized as counts only."""
    summary = protection._rulesets_summary(
        [
            {"target": "branch", "enforcement": "active", "name": "protected branches"},
            {"target": "branch", "enforcement": "evaluate", "name": "dry run"},
            {"target": "tag", "enforcement": "active", "name": "tags"},
        ]
    )

    assert summary.total_count == 3
    assert summary.active_branch_count == 1


def test_main_reports_bounded_failure(capsys) -> None:
    """Verify CLI output avoids raw JSON and account metadata."""
    original_fetch = protection._fetch_json
    protection._fetch_json = _fetcher(
        {
            "/branches/develop": _branch_payload(
                protected=False,
                enabled=False,
                enforcement="off",
                noisy_email="person@example.com",
            ),
            "/rulesets": [],
        }
    )
    try:
        exit_code = protection.main(
            [
                "--repo",
                "Lemon-Aid-KDT/Lemon-sin",
                "--branch",
                "develop",
                "--api-base",
                "https://example.invalid",
            ]
        )
    finally:
        protection._fetch_json = original_fetch

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "develop: branch_unprotected protected=false" in captured.err
    assert "github_branch_protection_failed" in captured.err
    assert "person@example.com" not in captured.err
    assert "commit" not in captured.err


def _branch_payload(
    *,
    protected: bool,
    enabled: bool,
    enforcement: str,
    noisy_email: str | None = None,
) -> dict[str, Any]:
    """Return a minimal branch API payload.

    Args:
        protected: Branch protected flag.
        enabled: Nested protection enabled flag.
        enforcement: Status-check enforcement level.
        noisy_email: Optional value that must not be printed.

    Returns:
        Branch payload fixture.
    """
    payload: dict[str, Any] = {
        "protected": protected,
        "protection": {
            "enabled": enabled,
            "required_status_checks": {
                "enforcement_level": enforcement,
                "contexts": ["backend-ci"],
                "checks": [],
            },
        },
    }
    if noisy_email is not None:
        payload["commit"] = {"commit": {"author": {"email": noisy_email}}}
    return payload


def _fetcher(payloads: dict[str, Any]):
    """Return a fake URL fetcher.

    Args:
        payloads: Mapping keyed by URL suffix.

    Returns:
        Fetcher callable.
    """

    def fetch(url: str, _timeout_seconds: float) -> Any:
        for suffix, payload in payloads.items():
            if url.endswith(suffix):
                return payload
        raise RuntimeError("not_found")

    return fetch


def _load_protection_module() -> ModuleType:
    """Load the backend script without relying on PYTHONPATH layout.

    Returns:
        Loaded ``check_github_branch_protection`` module.
    """
    module_path = Path(__file__).resolve().parents[4] / "scripts/check_github_branch_protection.py"
    spec = importlib.util.spec_from_file_location("check_github_branch_protection", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"missing module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_github_branch_protection"] = module
    spec.loader.exec_module(module)
    return module


protection = _load_protection_module()
