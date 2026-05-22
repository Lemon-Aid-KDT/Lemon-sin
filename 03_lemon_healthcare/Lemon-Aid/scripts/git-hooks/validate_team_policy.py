"""Validate Lemon Aid branch and PR policy for GitHub Actions."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

from validate_commit_msg import ALLOWED_SCOPES, ALLOWED_TYPES, validate_title

PROTECTED_BRANCHES = {"main", "develop"}
BRANCH_TYPES = (*ALLOWED_TYPES, "hotfix")
WORK_BRANCH_PATTERN = re.compile(
    r"^(?P<type>"
    + "|".join(BRANCH_TYPES)
    + r")/(?P<scope>"
    + "|".join(ALLOWED_SCOPES)
    + r")-[a-z0-9][a-z0-9-]*$"
)


def current_branch() -> str:
    """Return the current Git branch name, or an empty string.

    Returns:
        Current branch name when Git is available.
    """
    result = subprocess.run(
        ("git", "rev-parse", "--abbrev-ref", "HEAD"),
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def validate_branch(*, base: str, branch: str, event_name: str) -> list[str]:
    """Validate branch policy for PR and protected-branch push events.

    Args:
        base: PR base branch or push ref branch.
        branch: PR head branch or push ref branch.
        event_name: GitHub event name.

    Returns:
        Bounded policy errors.
    """
    errors: list[str] = []
    if event_name == "push" and branch in PROTECTED_BRANCHES:
        errors.append(f"Direct push to {branch} is not allowed. Use a PR.")
        return errors

    if base == "main" and branch == "develop":
        return errors
    if branch in PROTECTED_BRANCHES:
        errors.append(f"PR head branch must not be protected: {branch}")
    if base == "develop" and not WORK_BRANCH_PATTERN.match(branch):
        errors.append(
            "PR branch must look like <type>/<scope>-<kebab-subject>, "
            "for example feat/ocr-quality-gates."
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    """Run the team policy validator.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code. Zero means valid.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-name", default="")
    parser.add_argument("--base", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--title", default="")
    args = parser.parse_args(argv)

    branch = args.branch or current_branch()
    errors = validate_branch(base=args.base, branch=branch, event_name=args.event_name)
    if args.title:
        errors.extend(validate_title(args.title))

    if errors:
        print("Team collaboration policy failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
