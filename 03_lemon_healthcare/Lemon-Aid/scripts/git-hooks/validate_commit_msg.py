"""Validate Lemon Aid Conventional Commit and PR titles."""

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
MAX_SUBJECT_CHARS = 50
TITLE_PATTERN = re.compile(
    r"^(?P<type>"
    + "|".join(ALLOWED_TYPES)
    + r")\((?P<scope>[a-z0-9-]+)\): (?P<subject>.+)$"
)
RELEASE_PATTERN = re.compile(r"^release: v\d+\.\d+\.\d+$")


def first_non_comment_line(message: str) -> str:
    """Return the first non-comment line from a commit message.

    Args:
        message: Commit message text.

    Returns:
        First non-empty line that does not start with ``#``.
    """
    for line in message.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def validate_title(title: str) -> list[str]:
    """Validate one commit or PR title.

    Args:
        title: Commit or PR title.

    Returns:
        Bounded validation errors. Empty means valid.
    """
    errors: list[str] = []
    normalized = title.strip()
    if RELEASE_PATTERN.match(normalized):
        return errors

    match = TITLE_PATTERN.match(normalized)
    if match is None:
        return [
            "Use Conventional Commits: <type>(<scope>): <subject>",
            "Example: docs(team): 협업 규칙 문서 추가",
        ]

    commit_type = match.group("type")
    scope = match.group("scope")
    subject = match.group("subject").strip()
    if commit_type not in ALLOWED_TYPES:
        errors.append("Type must be one of: " + ", ".join(ALLOWED_TYPES))
    if scope not in ALLOWED_SCOPES:
        errors.append("Scope must be one of: " + ", ".join(ALLOWED_SCOPES))
    if not subject:
        errors.append("Subject is required.")
    if len(subject) > MAX_SUBJECT_CHARS:
        errors.append(f"Subject must be {MAX_SUBJECT_CHARS} characters or less.")
    if subject.endswith("."):
        errors.append("Subject must not end with a period.")
    return errors


def main(argv: list[str] | None = None) -> int:
    """Run the commit message validator.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code. Zero means valid.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message_file", nargs="?")
    parser.add_argument("--title")
    args = parser.parse_args(argv)

    if args.title is not None:
        title = args.title.strip()
    elif args.message_file:
        title = first_non_comment_line(
            Path(args.message_file).read_text(encoding="utf-8")
        )
    else:
        title = first_non_comment_line(sys.stdin.read())

    errors = validate_title(title)
    if errors:
        print("Commit/PR title policy failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
