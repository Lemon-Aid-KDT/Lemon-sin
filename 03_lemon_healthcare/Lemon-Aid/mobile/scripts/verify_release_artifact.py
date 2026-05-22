"""Verify mobile release artifacts do not carry unsafe endpoint secrets.

This checker intentionally works on the built artifact bytes instead of source
files so it can be used as a post-build gate for APK/AAB outputs.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

DEFAULT_FORBIDDEN_STRINGS = (
    "http://127.0.0.1",
    "http://10.0.2.2",
    "http://localhost",
    "ngrok",
)


def _iter_artifact_bytes(path: Path) -> list[tuple[str, bytes]]:
    """Return decompressed artifact entries for scanning.

    Args:
        path: APK, AAB, or a plain binary artifact path.

    Returns:
        Pairs of display name and byte content.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        zipfile.BadZipFile: If a ``.apk``/``.aab`` file is not a valid zip.
    """
    if path.suffix.lower() not in {".apk", ".aab"}:
        return [(path.name, path.read_bytes())]

    entries: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            entries.append((info.filename, archive.read(info)))
    return entries


def _contains(haystack: bytes, needle: str) -> bool:
    """Check a UTF-8 string against binary artifact content."""
    return needle.encode("utf-8") in haystack


def verify_artifact(
    artifact: Path,
    *,
    expected_strings: tuple[str, ...],
    forbidden_strings: tuple[str, ...],
) -> list[str]:
    """Verify expected release strings and forbidden development strings.

    Args:
        artifact: Built APK/AAB/binary artifact.
        expected_strings: Strings that must be present in the artifact.
        forbidden_strings: Strings that must be absent from the artifact.

    Returns:
        Human-readable violation messages. Empty means pass.
    """
    entries = _iter_artifact_bytes(artifact)
    violations: list[str] = []

    for expected in expected_strings:
        if not any(_contains(content, expected) for _, content in entries):
            violations.append(f"missing_expected_string={expected}")

    for forbidden in forbidden_strings:
        for name, content in entries:
            if _contains(content, forbidden):
                violations.append(f"forbidden_string={forbidden} entry={name}")
                break

    return violations


def main() -> int:
    """Run the artifact verifier CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument(
        "--expect",
        action="append",
        default=[],
        help="UTF-8 string that must be present; repeatable.",
    )
    parser.add_argument(
        "--forbid",
        action="append",
        default=[],
        help="Additional UTF-8 string that must be absent; repeatable.",
    )
    args = parser.parse_args()

    artifact = args.artifact.resolve()
    forbidden = tuple(dict.fromkeys((*DEFAULT_FORBIDDEN_STRINGS, *args.forbid)))
    violations = verify_artifact(
        artifact,
        expected_strings=tuple(args.expect),
        forbidden_strings=forbidden,
    )
    if violations:
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1

    print(f"release_artifact_ok={artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
