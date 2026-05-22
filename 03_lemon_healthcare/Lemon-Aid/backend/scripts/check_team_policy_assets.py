"""Check Lemon Aid team-policy assets without reading secrets."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

REQUIRED_FILES = (
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/team-policy.yml",
    "scripts/git-hooks/validate_commit_msg.py",
    "scripts/git-hooks/validate_team_policy.py",
)
PR_TEMPLATE_REQUIRED_SNIPPETS = (
    "develop",
    "<type>/<scope>-<kebab-subject>",
    "<type>(<scope>): <subject>",
    "pre-commit run --all-files",
    "raw OCR text",
    "provider payload",
)
WORKFLOW_REQUIRED_SNIPPETS = (
    "pull_request:",
    "push:",
    "contents: read",
    "backend/scripts/check_team_policy_assets.py",
    "scripts/git-hooks/validate_team_policy.py",
    "github.head_ref",
    "github.base_ref",
)
FORBIDDEN_SNIPPETS = (
    "yeong-Lemon-Aid",
    "/" + "Users/",
    "/" + "Volumes/",
    "CLOVA" + "_OCR_SECRET=",
    "Authorization" + ": Bearer",
)


@dataclass(frozen=True)
class TeamPolicyAssetFinding:
    """One bounded team-policy asset finding.

    Attributes:
        path: Project-relative path.
        code: Stable finding code.
        detail: Short bounded detail without file content.
    """

    path: str
    code: str
    detail: str


def check_assets(repo_root: Path) -> list[TeamPolicyAssetFinding]:
    """Check team-policy files for export readiness.

    Args:
        repo_root: Lemon Aid project root.

    Returns:
        Bounded findings. Empty means pass.
    """
    findings: list[TeamPolicyAssetFinding] = []
    for relative_path in REQUIRED_FILES:
        if not (repo_root / relative_path).is_file():
            findings.append(
                TeamPolicyAssetFinding(relative_path, "missing_required_file", "file_absent")
            )
    if findings:
        return findings

    findings.extend(
        _check_required_snippets(
            repo_root=repo_root,
            relative_path=".github/PULL_REQUEST_TEMPLATE.md",
            snippets=PR_TEMPLATE_REQUIRED_SNIPPETS,
        )
    )
    findings.extend(
        _check_required_snippets(
            repo_root=repo_root,
            relative_path=".github/workflows/team-policy.yml",
            snippets=WORKFLOW_REQUIRED_SNIPPETS,
        )
    )
    for relative_path in REQUIRED_FILES:
        findings.extend(_check_forbidden_snippets(repo_root / relative_path, relative_path))
    return findings


def _check_required_snippets(
    *,
    repo_root: Path,
    relative_path: str,
    snippets: tuple[str, ...],
) -> list[TeamPolicyAssetFinding]:
    """Check that a policy asset contains required markers.

    Args:
        repo_root: Lemon Aid project root.
        relative_path: Project-relative file path.
        snippets: Required text markers.

    Returns:
        Bounded missing-snippet findings.
    """
    text = (repo_root / relative_path).read_text(encoding="utf-8")
    return [
        TeamPolicyAssetFinding(relative_path, "missing_required_snippet", f"marker={index}")
        for index, snippet in enumerate(snippets, start=1)
        if snippet not in text
    ]


def _check_forbidden_snippets(path: Path, relative_path: str) -> list[TeamPolicyAssetFinding]:
    """Check one policy asset for stale paths or obvious secret snippets.

    Args:
        path: File path.
        relative_path: Project-relative file path.

    Returns:
        Bounded forbidden-snippet findings.
    """
    text = path.read_text(encoding="utf-8")
    return [
        TeamPolicyAssetFinding(relative_path, "forbidden_snippet", f"marker={index}")
        for index, snippet in enumerate(FORBIDDEN_SNIPPETS, start=1)
        if snippet in text
    ]


def main(argv: list[str] | None = None) -> int:
    """Run the team-policy asset checker.

    Args:
        argv: Optional CLI argument list.

    Returns:
        Process exit code. Zero means all checks passed.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    findings = check_assets(args.repo_root)
    if findings:
        for finding in findings:
            print(
                f"{finding.path}: {finding.code} {finding.detail}",
                file=sys.stderr,
            )
        return 1
    print(f"team_policy_assets_ok files={len(REQUIRED_FILES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
