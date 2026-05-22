"""Audit Lemon Aid GitHub CI assets for stale project paths."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

LEMON_WORKFLOW_GLOB = "17-lemon-*.y*ml"
OPTIONAL_POLICY_FILES = (
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
)
DEFAULT_STALE_PROJECT_PATHS = ("03_lemon_healthcare/yeong-Lemon-Aid",)
LOCAL_ABSOLUTE_PATH_MARKERS = (
    "/" + "Users/",
    "/" + "Volumes/",
)


@dataclass(frozen=True)
class CiPathFinding:
    """One bounded CI path finding.

    Attributes:
        path: Repository-relative file path or synthetic path marker.
        code: Stable finding code.
        detail: Short bounded detail without file content.
    """

    path: str
    code: str
    detail: str


def check_ci_paths(
    *,
    repo_root: Path,
    project_root: Path,
    github_root: Path | None = None,
    stale_project_paths: tuple[str, ...] = DEFAULT_STALE_PROJECT_PATHS,
) -> list[CiPathFinding]:
    """Check GitHub CI/policy files for stale Lemon Aid paths.

    Args:
        repo_root: Git repository root containing ``.github``.
        project_root: Current Lemon Aid project root.
        github_root: Optional explicit ``.github`` root.
        stale_project_paths: Project paths that must no longer appear.

    Returns:
        Bounded findings. Empty means pass.
    """
    repo_root = repo_root.resolve()
    project_root = project_root.resolve()
    github_root = (github_root or repo_root / ".github").resolve()
    project_path = _project_path_marker(repo_root=repo_root, project_root=project_root)

    findings: list[CiPathFinding] = []
    workflow_root = github_root / "workflows"
    lemon_workflows = sorted(workflow_root.glob(LEMON_WORKFLOW_GLOB))
    if not lemon_workflows:
        findings.append(
            CiPathFinding(
                _display_path(workflow_root / LEMON_WORKFLOW_GLOB, repo_root),
                "missing_lemon_workflow",
                "glob_empty",
            )
        )
    for path in lemon_workflows:
        findings.extend(
            _check_file(
                path=path,
                repo_root=repo_root,
                project_path=project_path,
                stale_project_paths=stale_project_paths,
                require_project_path=True,
            )
        )

    for relative_path in OPTIONAL_POLICY_FILES:
        path = github_root.parent / relative_path
        if path.is_file():
            findings.extend(
                _check_file(
                    path=path,
                    repo_root=repo_root,
                    project_path=project_path,
                    stale_project_paths=stale_project_paths,
                    require_project_path=False,
                )
            )
    return findings


def _check_file(
    *,
    path: Path,
    repo_root: Path,
    project_path: str,
    stale_project_paths: tuple[str, ...],
    require_project_path: bool,
) -> list[CiPathFinding]:
    """Check one GitHub policy file for stale or unsafe path markers.

    Args:
        path: File to inspect.
        repo_root: Git repository root.
        project_path: Expected current project path marker.
        stale_project_paths: Stale project path markers to reject.
        require_project_path: Whether the current project path must appear.

    Returns:
        Bounded findings for the file.
    """
    text = path.read_text(encoding="utf-8")
    display_path = _display_path(path, repo_root)
    findings: list[CiPathFinding] = []
    if require_project_path and project_path not in text:
        findings.append(
            CiPathFinding(
                display_path,
                "missing_current_project_path",
                "expected_project_path",
            )
        )
    for index, stale_path in enumerate(stale_project_paths, start=1):
        if stale_path != project_path and stale_path in text:
            findings.append(CiPathFinding(display_path, "stale_project_path", f"marker={index}"))
    for index, marker in enumerate(LOCAL_ABSOLUTE_PATH_MARKERS, start=1):
        if marker in text:
            findings.append(CiPathFinding(display_path, "local_absolute_path", f"marker={index}"))
    return findings


def _project_path_marker(*, repo_root: Path, project_root: Path) -> str:
    """Return the current project path marker expected in monorepo CI.

    Args:
        repo_root: Git repository root.
        project_root: Current Lemon Aid project root.

    Returns:
        POSIX-style repository-relative path, or ``"."`` for standalone roots.
    """
    try:
        relative_path = project_root.relative_to(repo_root)
    except ValueError:
        return project_root.name
    return relative_path.as_posix() or "."


def _display_path(path: Path, repo_root: Path) -> str:
    """Return a bounded display path without local absolute prefixes.

    Args:
        path: File path.
        repo_root: Git repository root.

    Returns:
        POSIX-style repository-relative path when possible.
    """
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.name


def _git_root_for_path(path: Path) -> Path:
    """Return the Git repository root for a path.

    Args:
        path: Directory inside a Git worktree.

    Returns:
        Absolute repository root path.

    Raises:
        RuntimeError: If the path is not inside a Git worktree.
    """
    result = subprocess.run(
        ("git", "-C", str(path), "rev-parse", "--show-toplevel"),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("not_inside_git_worktree")
    return Path(result.stdout.strip()).resolve()


def main(argv: list[str] | None = None) -> int:
    """Run the Lemon CI path audit.

    Args:
        argv: Optional CLI argument list.

    Returns:
        Process exit code. Zero means no stale CI path was found.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--github-root", type=Path)
    args = parser.parse_args(argv)

    project_root = args.project_root.resolve()
    repo_root = args.repo_root.resolve() if args.repo_root else _git_root_for_path(project_root)
    findings = check_ci_paths(
        repo_root=repo_root,
        project_root=project_root,
        github_root=args.github_root,
    )
    if findings:
        for finding in findings:
            print(
                f"{finding.path}: {finding.code} {finding.detail}",
                file=sys.stderr,
            )
        return 1
    print(
        "lemon_ci_paths_ok "
        f"project_path={_project_path_marker(repo_root=repo_root, project_root=project_root)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
