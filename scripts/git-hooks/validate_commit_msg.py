"""Validate Conventional Commits messages for Lemon Aid."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ALLOWED_TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "chore",
    "ci",
    "build",
    "revert",
    "data",
    "ops",
)
ALLOWED_SCOPES = (
    "mobile",
    "backend",
    "ai",
    "ocr",
    "db",
    "auth",
    "ux",
    "infra",
    "docs",
    "team",
    "test",
    "data",
)
TITLE_PATTERN = re.compile(
    r"^(?P<type>"
    + "|".join(ALLOWED_TYPES)
    + r")(\((?P<scope>[a-z0-9-]+)\))?(?P<breaking>!)?: (?P<subject>.+)$"
)
RELEASE_PATTERN = re.compile(r"^release: v\d+\.\d+\.\d+")


def _first_non_comment_line(message: str) -> str:
    for line in message.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def validate_title(title: str) -> list[str]:
    errors: list[str] = []
    if RELEASE_PATTERN.match(title):
        return errors

    match = TITLE_PATTERN.match(title)
    if match is None:
        return [
            "Use Conventional Commits: <type>(<scope>): <subject>",
            "Example: docs(team): 협업 규칙 문서 추가",
        ]

    scope = match.group("scope")
    subject = match.group("subject").strip()
    if scope is not None and scope not in ALLOWED_SCOPES:
        errors.append(
            "Scope must be one of: " + ", ".join(ALLOWED_SCOPES)
        )
    if not subject:
        errors.append("Subject is required.")
    if len(title) > 100:
        errors.append("Title should be 100 characters or less.")
    if subject.endswith("."):
        errors.append("Subject should not end with a period.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("message_file", nargs="?")
    parser.add_argument("--title")
    args = parser.parse_args()

    if args.title is not None:
        title = args.title.strip()
    elif args.message_file:
        title = _first_non_comment_line(Path(args.message_file).read_text(encoding="utf-8"))
    else:
        title = _first_non_comment_line(sys.stdin.read())

    errors = validate_title(title)
    if errors:
        print("Commit/PR title policy failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
