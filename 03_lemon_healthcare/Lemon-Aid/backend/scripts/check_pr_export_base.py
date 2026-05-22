"""Validate that a Git base ref is safe for OCR PR export.

This check prevents two recurring PR-prep failures:

1. Exporting a small OCR patch onto a skeleton branch that does not contain the
   real Lemon Aid backend tree.
2. Basing a new PR on a branch that already tracks generated/private OCR
   evaluation artifacts.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REQUIRED_PATHS = (
    "backend/Nutrition-backend/src/ocr/field_extractor.py",
    "backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py",
)
DEFAULT_FORBIDDEN_PREFIXES = (
    ".env",
    "outputs/generated/ocr-eval/",
)


@dataclass(frozen=True)
class BaseCheckResult:
    """Result of checking one base ref.

    Attributes:
        base_ref: Git ref that was checked.
        missing_required_paths: Required paths absent from the ref.
        forbidden_paths: Forbidden files tracked in the ref.
    """

    base_ref: str
    missing_required_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Return whether the base ref passed all checks.

        Returns:
            True when no required path is missing and no forbidden path is tracked.
        """
        return not self.missing_required_paths and not self.forbidden_paths


def check_base_ref(
    *,
    repo_root: Path,
    base_ref: str,
    required_paths: tuple[str, ...],
    forbidden_prefixes: tuple[str, ...],
    project_root: Path | None = None,
) -> BaseCheckResult:
    """Check a base ref for required code paths and forbidden artifacts.

    Args:
        repo_root: Git repository root.
        base_ref: Git ref to inspect.
        required_paths: Root-relative paths that must exist in the base ref.
        forbidden_prefixes: Root-relative file or directory prefixes that must
            not be tracked in the base ref.
        project_root: Optional project directory under ``repo_root``. When
            supplied, each path is checked both as a standalone-repo path and as
            a monorepo-prefixed path.

    Returns:
        Structured check result.

    Raises:
        RuntimeError: If ``base_ref`` is not a valid tree.
    """
    _require_git_tree(repo_root=repo_root, base_ref=base_ref)
    project_root = project_root or repo_root
    missing_required_paths = tuple(
        path
        for path in required_paths
        if not any(
            _tree_path_exists(repo_root=repo_root, base_ref=base_ref, path=candidate_path)
            for candidate_path in _candidate_tree_paths(
                repo_root=repo_root,
                project_root=project_root,
                path=path,
            )
        )
    )
    forbidden_paths: list[str] = []
    for prefix in forbidden_prefixes:
        for candidate_prefix in _candidate_tree_paths(
            repo_root=repo_root,
            project_root=project_root,
            path=prefix,
        ):
            forbidden_paths.extend(
                _tracked_paths_under(
                    repo_root=repo_root,
                    base_ref=base_ref,
                    prefix=_normalize_forbidden_prefix(candidate_prefix),
                )
            )
    return BaseCheckResult(
        base_ref=base_ref,
        missing_required_paths=missing_required_paths,
        forbidden_paths=tuple(sorted(dict.fromkeys(forbidden_paths))),
    )


def _require_git_tree(*, repo_root: Path, base_ref: str) -> None:
    """Require a ref to resolve to a Git tree.

    Args:
        repo_root: Git repository root.
        base_ref: Git ref to inspect.

    Raises:
        RuntimeError: If the ref cannot be resolved as a tree.
    """
    result = _git(repo_root, "cat-file", "-e", f"{base_ref}^{{tree}}")
    if result.returncode != 0:
        raise RuntimeError(f"base_ref_not_found ref={base_ref}")


def _tree_path_exists(*, repo_root: Path, base_ref: str, path: str) -> bool:
    """Return whether a root-relative path exists in a ref.

    Args:
        repo_root: Git repository root.
        base_ref: Git ref to inspect.
        path: Root-relative file path.

    Returns:
        True if the path exists in ``base_ref``.
    """
    result = _git(repo_root, "cat-file", "-e", f"{base_ref}:{path}")
    return result.returncode == 0


def _tracked_paths_under(*, repo_root: Path, base_ref: str, prefix: str) -> tuple[str, ...]:
    """Return tracked files below a prefix in a ref.

    Args:
        repo_root: Git repository root.
        base_ref: Git ref to inspect.
        prefix: Root-relative file or directory prefix.

    Returns:
        Tracked paths under the prefix.
    """
    result = _git(repo_root, "ls-tree", "-r", "--name-only", base_ref, "--", prefix)
    if result.returncode != 0:
        return ()
    return tuple(line for line in result.stdout.splitlines() if line.strip())


def _normalize_forbidden_prefix(prefix: str) -> str:
    """Normalize a forbidden path prefix for Git pathspec checks.

    Args:
        prefix: Input prefix.

    Returns:
        Prefix without leading slashes.
    """
    return prefix.strip().lstrip("/")


def _candidate_tree_paths(*, repo_root: Path, project_root: Path, path: str) -> tuple[str, ...]:
    """Return standalone and monorepo-prefixed candidate tree paths.

    Args:
        repo_root: Git repository root.
        project_root: Project directory that may live below ``repo_root``.
        path: Project-relative or root-relative path.

    Returns:
        Unique candidate paths suitable for Git tree/pathspec checks.
    """
    normalized = _normalize_forbidden_prefix(path)
    candidates = [normalized]
    try:
        project_prefix = project_root.resolve().relative_to(repo_root.resolve())
    except ValueError:
        project_prefix = Path()
    if project_prefix.parts and not normalized.startswith(project_prefix.as_posix() + "/"):
        candidates.append((project_prefix / normalized).as_posix())
    return tuple(dict.fromkeys(candidates))


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a Git command in the repository root.

    Args:
        repo_root: Git repository root.
        *args: Git command arguments after ``git``.

    Returns:
        Completed process with captured text output.
    """
    return subprocess.run(
        ("git", "-C", str(repo_root), *args),
        check=False,
        capture_output=True,
        text=True,
    )


def _git_root_for_path(path: Path) -> Path:
    """Return the Git repository root for a path.

    Args:
        path: Directory inside a Git worktree.

    Returns:
        Absolute repository root path.

    Raises:
        RuntimeError: If the current directory is not inside a Git worktree.
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


def _print_result(result: BaseCheckResult) -> None:
    """Print a bounded human-readable check result.

    Args:
        result: Check result to print.
    """
    if result.ok:
        print(f"pr_export_base_ok ref={result.base_ref}")
        return
    for path in result.missing_required_paths:
        print(
            f"missing_required_path ref={result.base_ref} path={path}",
            file=sys.stderr,
        )
    for path in result.forbidden_paths:
        print(
            f"forbidden_base_path ref={result.base_ref} path={path}",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    """Run the PR export base check.

    Args:
        argv: Optional CLI argument list.

    Returns:
        Process exit code. Zero means the base ref is safe for export.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help=(
            "Project directory to use for monorepo-prefixed path checks. "
            "Defaults to the current directory when --repo-root is omitted."
        ),
    )
    parser.add_argument(
        "--required-path",
        action="append",
        dest="required_paths",
        default=None,
        help="Root-relative path that must exist in the base ref. Repeatable.",
    )
    parser.add_argument(
        "--forbid-prefix",
        action="append",
        dest="forbidden_prefixes",
        default=None,
        help="Root-relative file or directory prefix that must not be tracked. Repeatable.",
    )
    args = parser.parse_args(argv)

    input_root = args.repo_root.resolve() if args.repo_root else Path.cwd().resolve()
    repo_root = _git_root_for_path(input_root)
    if args.project_root is not None:
        project_root = args.project_root.resolve()
    elif args.repo_root is None:
        project_root = Path.cwd().resolve()
    else:
        project_root = input_root
    required_paths = tuple(args.required_paths or DEFAULT_REQUIRED_PATHS)
    forbidden_prefixes = tuple(args.forbidden_prefixes or DEFAULT_FORBIDDEN_PREFIXES)
    try:
        result = check_base_ref(
            repo_root=repo_root,
            project_root=project_root,
            base_ref=args.base_ref,
            required_paths=required_paths,
            forbidden_prefixes=forbidden_prefixes,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _print_result(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
