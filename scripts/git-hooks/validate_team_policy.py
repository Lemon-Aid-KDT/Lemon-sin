"""Validate Lemon Aid branch and PR policy for GitHub Actions."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

from validate_commit_msg import validate_title

PROTECTED_BRANCHES = {"main", "develop"}
WORK_BRANCH_PATTERN = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert|data|ops|hotfix)/"
    r"(mobile|backend|ai|ocr|db|auth|ux|infra|docs|team|test|data)-[a-z0-9][a-z0-9-]*$"
)


def _current_branch() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _validate_branch(base: str, branch: str, event_name: str) -> list[str]:
    errors: list[str] = []
    if event_name == "push" and branch in PROTECTED_BRANCHES:
        errors.append(
            f"Direct push to {branch} is not allowed. Use a PR from a short-lived branch."
        )
        return errors

    if base == "main" and branch == "develop":
        return errors
    if base == "develop" and not WORK_BRANCH_PATTERN.match(branch):
        errors.append(
            "PR branch must look like <type>/<scope>-<subject>, "
            "for example docs/team-collaboration-rules."
        )
    if branch in PROTECTED_BRANCHES and not (base == "main" and branch == "develop"):
        errors.append(f"PR head branch must not be protected: {branch}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-name", default="")
    parser.add_argument("--base", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    branch = args.branch or _current_branch()
    errors = _validate_branch(args.base, branch, args.event_name)
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
