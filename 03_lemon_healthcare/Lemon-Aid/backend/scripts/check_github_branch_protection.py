"""Audit public GitHub branch protection metadata with bounded output.

This operator check uses GitHub's public branch metadata endpoint. It does not
require or read a token, and it intentionally prints only branch names, boolean
protection state, and aggregate ruleset counts. Admin-only details such as force
push bypass actors still require a valid repository-admin token or UI review.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_REPO = "Lemon-Aid-KDT/Lemon-sin"
DEFAULT_BRANCHES = ("develop", "main")
DEFAULT_API_BASE = "https://api.github.com"


@dataclass(frozen=True)
class BranchProtectionFinding:
    """One bounded branch protection finding.

    Attributes:
        target: Branch name or repository-level target.
        code: Stable finding code.
        detail: Bounded detail without raw API payload content.
    """

    target: str
    code: str
    detail: str


@dataclass(frozen=True)
class BranchProtectionState:
    """Public branch protection state for one branch.

    Attributes:
        branch: Branch name.
        protected: Public GitHub ``protected`` boolean.
        protection_enabled: Public nested protection enabled flag, if present.
        status_checks_enforcement: Public status-check enforcement level.
        status_check_count: Count of configured public status checks.
    """

    branch: str
    protected: bool
    protection_enabled: bool | None
    status_checks_enforcement: str | None
    status_check_count: int


@dataclass(frozen=True)
class RulesetSummary:
    """Bounded repository ruleset summary.

    Attributes:
        total_count: Count of returned repository rulesets.
        active_branch_count: Count of active rulesets targeting branches.
    """

    total_count: int
    active_branch_count: int


@dataclass(frozen=True)
class AuditResult:
    """Branch protection audit result.

    Attributes:
        states: Public branch states by branch.
        rulesets: Repository ruleset summary, or ``None`` if unavailable.
        findings: Bounded findings.
    """

    states: tuple[BranchProtectionState, ...]
    rulesets: RulesetSummary | None
    findings: tuple[BranchProtectionFinding, ...]

    @property
    def ok(self) -> bool:
        """Return whether the public metadata satisfies the expected policy."""
        return not self.findings


def audit_repository(
    *,
    repo: str,
    branches: tuple[str, ...],
    api_base: str = DEFAULT_API_BASE,
    timeout_seconds: float = 10.0,
    fetch_json: Callable[[str, float], Any] | None = None,
) -> AuditResult:
    """Audit public branch protection metadata for a GitHub repository.

    Args:
        repo: GitHub repository in ``owner/name`` form.
        branches: Branch names expected to be protected.
        api_base: GitHub API base URL.
        timeout_seconds: Network timeout for each request.
        fetch_json: Optional JSON fetcher used by tests.

    Returns:
        Structured audit result.
    """
    active_fetcher = fetch_json or _fetch_json
    normalized_repo = _normalize_repo(repo)
    findings: list[BranchProtectionFinding] = []
    states: list[BranchProtectionState] = []
    for branch in branches:
        try:
            payload = active_fetcher(
                _branch_url(api_base=api_base, repo=normalized_repo, branch=branch),
                timeout_seconds,
            )
        except RuntimeError as exc:
            findings.append(
                BranchProtectionFinding(branch, "branch_metadata_unavailable", str(exc))
            )
            continue
        state = _branch_state(branch=branch, payload=payload)
        states.append(state)
        findings.extend(_branch_findings(state))

    rulesets: RulesetSummary | None
    try:
        rulesets_payload = active_fetcher(
            _rulesets_url(api_base=api_base, repo=normalized_repo),
            timeout_seconds,
        )
        rulesets = _rulesets_summary(rulesets_payload)
    except RuntimeError as exc:
        rulesets = None
        findings.append(BranchProtectionFinding("repository", "rulesets_unavailable", str(exc)))

    return AuditResult(
        states=tuple(states),
        rulesets=rulesets,
        findings=tuple(findings),
    )


def _branch_state(*, branch: str, payload: Any) -> BranchProtectionState:
    """Parse public branch metadata.

    Args:
        branch: Branch name being parsed.
        payload: Parsed branch API response.

    Returns:
        Bounded branch protection state.
    """
    if not isinstance(payload, dict):
        raise RuntimeError("invalid_branch_payload")
    protection = payload.get("protection")
    if not isinstance(protection, dict):
        protection = {}
    status_checks = protection.get("required_status_checks")
    if not isinstance(status_checks, dict):
        status_checks = {}
    checks = status_checks.get("checks")
    contexts = status_checks.get("contexts")
    status_check_count = _count_items(checks) + _count_items(contexts)
    enabled = protection.get("enabled")
    return BranchProtectionState(
        branch=branch,
        protected=payload.get("protected") is True,
        protection_enabled=enabled if isinstance(enabled, bool) else None,
        status_checks_enforcement=_string_or_none(status_checks.get("enforcement_level")),
        status_check_count=status_check_count,
    )


def _branch_findings(state: BranchProtectionState) -> tuple[BranchProtectionFinding, ...]:
    """Return policy findings for one public branch state.

    Args:
        state: Public branch protection state.

    Returns:
        Bounded findings.
    """
    findings: list[BranchProtectionFinding] = []
    if not state.protected:
        findings.append(
            BranchProtectionFinding(state.branch, "branch_unprotected", "protected=false")
        )
    if state.protection_enabled is False:
        findings.append(
            BranchProtectionFinding(
                state.branch,
                "branch_protection_disabled",
                "protection.enabled=false",
            )
        )
    if state.status_checks_enforcement in {None, "off"}:
        findings.append(
            BranchProtectionFinding(
                state.branch,
                "required_status_checks_not_enforced",
                f"enforcement={state.status_checks_enforcement or 'missing'}",
            )
        )
    return tuple(findings)


def _rulesets_summary(payload: Any) -> RulesetSummary:
    """Summarize repository rulesets without printing ruleset content.

    Args:
        payload: Parsed rulesets API response.

    Returns:
        Bounded ruleset summary.
    """
    if not isinstance(payload, list):
        raise RuntimeError("invalid_rulesets_payload")
    active_branch_count = 0
    for item in payload:
        if not isinstance(item, dict):
            continue
        if item.get("target") == "branch" and item.get("enforcement") == "active":
            active_branch_count += 1
    return RulesetSummary(total_count=len(payload), active_branch_count=active_branch_count)


def _fetch_json(url: str, timeout_seconds: float) -> Any:
    """Fetch a JSON document from GitHub without credentials.

    Args:
        url: API URL.
        timeout_seconds: Request timeout.

    Returns:
        Parsed JSON payload.

    Raises:
        RuntimeError: If the request fails or JSON is invalid.
    """
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "lemon-aid-branch-protection-audit",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"http_status={exc.code}") from exc
    except URLError as exc:
        reason = exc.reason.__class__.__name__.casefold()
        raise RuntimeError(f"url_error={reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("invalid_json") from exc


def _branch_url(*, api_base: str, repo: str, branch: str) -> str:
    """Build the public branch metadata URL."""
    return f"{api_base.rstrip('/')}/repos/{quote(repo, safe='/')}/branches/{quote(branch, safe='')}"


def _rulesets_url(*, api_base: str, repo: str) -> str:
    """Build the public repository rulesets URL."""
    return f"{api_base.rstrip('/')}/repos/{quote(repo, safe='/')}/rulesets"


def _normalize_repo(repo: str) -> str:
    """Normalize an ``owner/name`` repository string.

    Args:
        repo: Input repository string.

    Returns:
        Normalized repository string.

    Raises:
        ValueError: If ``repo`` is not in ``owner/name`` form.
    """
    normalized = repo.strip().strip("/")
    if normalized.count("/") != 1 or any(not part for part in normalized.split("/")):
        raise ValueError("repo must be in owner/name form")
    return normalized


def _count_items(value: object) -> int:
    """Count list-like values without inspecting contents."""
    return len(value) if isinstance(value, list) else 0


def _string_or_none(value: object) -> str | None:
    """Return a string value or ``None``."""
    return value if isinstance(value, str) else None


def _parse_branches(values: Iterable[str]) -> tuple[str, ...]:
    """Parse CLI branch values.

    Args:
        values: Branch argument values.

    Returns:
        Unique non-empty branch names.
    """
    branches = tuple(dict.fromkeys(branch.strip() for branch in values if branch.strip()))
    if not branches:
        raise ValueError("at least one branch is required")
    return branches


def main(argv: list[str] | None = None) -> int:
    """Run the public branch protection audit.

    Args:
        argv: Optional CLI argument list.

    Returns:
        Process exit code. Zero means no public protection findings.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository owner/name.")
    parser.add_argument(
        "--branch",
        action="append",
        dest="branches",
        default=None,
        help="Branch expected to be protected. Repeat for multiple branches.",
    )
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)

    try:
        branches = _parse_branches(args.branches or DEFAULT_BRANCHES)
        result = audit_repository(
            repo=args.repo,
            branches=branches,
            api_base=args.api_base,
            timeout_seconds=args.timeout,
        )
    except ValueError as exc:
        print(f"branch_protection_audit_error {exc}", file=sys.stderr)
        return 2

    if result.findings:
        for finding in result.findings:
            print(f"{finding.target}: {finding.code} {finding.detail}", file=sys.stderr)
        rulesets = result.rulesets
        ruleset_text = (
            "unknown"
            if rulesets is None
            else f"total={rulesets.total_count} active_branch={rulesets.active_branch_count}"
        )
        print(
            "github_branch_protection_failed "
            f"repo={args.repo} branches={len(branches)} rulesets={ruleset_text}",
            file=sys.stderr,
        )
        return 1

    rulesets = result.rulesets
    ruleset_text = (
        "unknown"
        if rulesets is None
        else f"total={rulesets.total_count} active_branch={rulesets.active_branch_count}"
    )
    print(
        "github_branch_protection_ok "
        f"repo={args.repo} branches={len(branches)} rulesets={ruleset_text}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
