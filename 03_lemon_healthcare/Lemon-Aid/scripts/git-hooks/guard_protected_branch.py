"""Reject local pushes to protected Lemon Aid branches.

This script is intended for a local ``pre-push`` hook. It is deliberately small:
GitHub branch protection is still the authoritative non-bypassable control, but
this hook catches accidental direct pushes before they leave a developer machine.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass

PROTECTED_BRANCHES = frozenset({"develop", "main"})
ZERO_SHA = "0" * 40


@dataclass(frozen=True)
class PushUpdate:
    """One pre-push update line.

    Attributes:
        local_ref: Local Git ref being pushed.
        local_sha: Local object SHA, or zeros for delete.
        remote_ref: Remote Git ref being updated.
        remote_sha: Remote object SHA, or zeros for new branch.
    """

    local_ref: str
    local_sha: str
    remote_ref: str
    remote_sha: str

    @property
    def remote_branch(self) -> str:
        """Return the remote branch name for ``refs/heads`` updates."""
        prefix = "refs/heads/"
        if self.remote_ref.startswith(prefix):
            return self.remote_ref.removeprefix(prefix)
        return ""


def parse_pre_push_stdin(text: str) -> list[PushUpdate]:
    """Parse Git pre-push stdin into bounded update records.

    Args:
        text: Raw pre-push stdin text.

    Returns:
        Parsed push updates. Malformed blank lines are ignored.
    """
    updates: list[PushUpdate] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        updates.append(
            PushUpdate(
                local_ref=parts[0],
                local_sha=parts[1],
                remote_ref=parts[2],
                remote_sha=parts[3],
            )
        )
    return updates


def current_branch() -> str:
    """Return the current Git branch name, or an empty string."""
    result = subprocess.run(
        ("git", "rev-parse", "--abbrev-ref", "HEAD"),
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def validate_push(updates: list[PushUpdate], *, fallback_branch: str = "") -> list[str]:
    """Validate that a push does not target protected branches.

    Args:
        updates: Parsed pre-push updates.
        fallback_branch: Current branch name used when no pre-push stdin exists.

    Returns:
        Bounded validation errors. Empty means valid.
    """
    errors: list[str] = []
    if not updates and fallback_branch in PROTECTED_BRANCHES:
        errors.append(f"Direct push from protected branch is not allowed: {fallback_branch}")
        return errors

    for update in updates:
        remote_branch = update.remote_branch
        if remote_branch not in PROTECTED_BRANCHES:
            continue
        action = "delete" if update.local_sha == ZERO_SHA else "update"
        errors.append(f"Direct {action} to protected branch is not allowed: {remote_branch}")
    return errors


def main(argv: list[str] | None = None, *, stdin_text: str | None = None) -> int:
    """Run the protected branch pre-push guard.

    Args:
        argv: Optional command-line arguments.
        stdin_text: Optional stdin override for tests.

    Returns:
        Process exit code. Zero means valid.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("remote_name", nargs="?")
    parser.add_argument("remote_url", nargs="?")
    args = parser.parse_args(argv)
    _ = (args.remote_name, args.remote_url)

    text = sys.stdin.read() if stdin_text is None else stdin_text
    errors = validate_push(parse_pre_push_stdin(text), fallback_branch=current_branch())
    if errors:
        print("Protected branch push policy failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
