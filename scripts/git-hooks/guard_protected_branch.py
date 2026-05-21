"""Guard Lemon Aid protected branches in local git hooks."""

from __future__ import annotations

import argparse
import subprocess
import sys

PROTECTED_BRANCHES = {"main", "develop"}


def _current_branch() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _print_branch_guidance(branch: str) -> None:
    print(
        f"Direct work on protected branch '{branch}' is blocked.\n"
        "Create a short-lived branch from origin/develop, for example:\n"
        "  git fetch origin\n"
        "  git switch -c docs/team-collaboration-rules origin/develop\n"
        "Then open a PR to develop after tests pass.",
        file=sys.stderr,
    )


def _guard_current_branch() -> int:
    branch = _current_branch()
    if branch in PROTECTED_BRANCHES:
        _print_branch_guidance(branch)
        return 1
    return 0


def _guard_pre_push() -> int:
    blocked_refs: list[str] = []
    for raw_line in sys.stdin:
        parts = raw_line.strip().split()
        if len(parts) < 4:
            continue
        _local_ref, _local_sha, remote_ref, _remote_sha = parts[:4]
        if remote_ref in {"refs/heads/main", "refs/heads/develop"}:
            blocked_refs.append(remote_ref.removeprefix("refs/heads/"))

    if blocked_refs:
        print(
            "Direct push to protected branch is blocked: "
            + ", ".join(sorted(set(blocked_refs)))
            + "\nPush your feature branch and open a PR instead.",
            file=sys.stderr,
        )
        return 1

    return _guard_current_branch()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("commit", "pre-push"), default="commit")
    args = parser.parse_args()
    if args.mode == "pre-push":
        return _guard_pre_push()
    return _guard_current_branch()


if __name__ == "__main__":
    raise SystemExit(main())
