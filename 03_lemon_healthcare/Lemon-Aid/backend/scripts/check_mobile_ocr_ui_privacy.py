"""Check mobile runtime source for OCR privacy leakage markers.

This gate scans only ``mobile/lib/**/*.dart`` by default. It is intentionally
bounded to runtime UI/client code so tests and documentation can keep negative
assertions for raw OCR/provider payload markers without failing the product UI
privacy check.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MOBILE_RUNTIME_GLOB = "mobile/lib/**/*.dart"
ALLOWED_RUNTIME_SNIPPETS = (
    "raw_ocr_text_stored",
    "raw_provider_payload_stored",
    "rawOcrTextStored",
    "rawProviderPayloadStored",
)
FORBIDDEN_RUNTIME_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "parse_ocr_text_method",
        re.compile(r"\bparseOcrText\b"),
    ),
    (
        "ocr_text_parse_request",
        re.compile(r"\bSupplementOCRTextParseRequest\b"),
    ),
    (
        "ocr_text_endpoint",
        re.compile(r"/ocr-text\b", re.IGNORECASE),
    ),
    (
        "raw_ocr_text_key",
        re.compile(r"\braw_ocr_text\b", re.IGNORECASE),
    ),
    (
        "ocr_text_key",
        re.compile(r"(?<!raw_)\bocr_text\b", re.IGNORECASE),
    ),
    (
        "raw_provider_payload_key",
        re.compile(r"\braw_provider_payload\b", re.IGNORECASE),
    ),
    (
        "provider_payload_key",
        re.compile(r"(?<!raw_)\bprovider_payload\b", re.IGNORECASE),
    ),
    (
        "request_headers_key",
        re.compile(r"\brequest_headers\b", re.IGNORECASE),
    ),
    (
        "image_bytes_key",
        re.compile(r"\bimage_bytes\b", re.IGNORECASE),
    ),
    (
        "authorization_marker",
        re.compile(r"\b(?:authorization|bearer)\b", re.IGNORECASE),
    ),
    (
        "secret_marker",
        re.compile(
            r"\b(?:api[_-]?key|secret|service_key|x_ocr_secret|clova_ocr_secret)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "raw_ocr_ui_label",
        re.compile(
            r"(?:OCR text review|Parse OCR text|Paste or edit OCR text|raw OCR text)",
            re.IGNORECASE,
        ),
    ),
)


@dataclass(frozen=True)
class MobilePrivacyFinding:
    """One mobile OCR UI privacy finding.

    Attributes:
        path: Source file path containing the finding.
        line: One-based line number.
        code: Stable finding code.
        detail: Bounded finding detail that never echoes source text.
    """

    path: Path
    line: int
    code: str
    detail: str


def iter_mobile_runtime_files(project_root: Path) -> Iterator[Path]:
    """Yield mobile runtime Dart files.

    Args:
        project_root: Lemon-Aid project root.

    Yields:
        Dart files under ``mobile/lib``.
    """
    yield from sorted(project_root.glob(DEFAULT_MOBILE_RUNTIME_GLOB))


def scan_mobile_runtime_source(project_root: Path) -> list[MobilePrivacyFinding]:
    """Scan mobile runtime Dart files for privacy findings.

    Args:
        project_root: Lemon-Aid project root.

    Returns:
        Mobile privacy findings.
    """
    findings: list[MobilePrivacyFinding] = []
    for path in iter_mobile_runtime_files(project_root):
        findings.extend(scan_dart_file(path))
    return findings


def scan_dart_file(path: Path) -> list[MobilePrivacyFinding]:
    """Scan one Dart source file.

    Args:
        path: Dart file path.

    Returns:
        Findings for the file.
    """
    findings: list[MobilePrivacyFinding] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if _is_comment_only_line(line):
            continue
        if _is_allowed_runtime_line(path, line):
            continue
        scanned_line = _remove_allowed_snippets(line)
        for code, pattern in FORBIDDEN_RUNTIME_PATTERNS:
            if pattern.search(scanned_line):
                findings.append(
                    MobilePrivacyFinding(path, line_number, code, "runtime_source_marker")
                )
    return findings


def _is_allowed_runtime_line(path: Path, line: str) -> bool:
    """Return whether a sensitive marker is part of known safe plumbing.

    Args:
        path: Dart file path.
        line: Source line.

    Returns:
        True when the marker belongs to auth transport or error redaction code.
    """
    normalized_path = path.as_posix()
    stripped = line.strip()
    if normalized_path.endswith("mobile/lib/core/api/api_client.dart"):
        return stripped == "headers['Authorization'] = 'Bearer ${_bearerToken.trim()}';"
    if normalized_path.endswith("mobile/lib/core/api/api_error.dart"):
        return stripped in {
            "<String>['raw', 'ocr', 'text'].join('_'),",
            "<String>['ocr', 'text'].join('_'),",
            "<String>['provider', 'payload'].join('_'),",
            "<String>['request', 'headers'].join('_'),",
            "<String>['image', 'bytes'].join('_'),",
            "<String>['authori', 'zation'].join(),",
            "'bearer ',",
            "<String>['api', 'key'].join('_'),",
            "<String>['api', 'key'].join('-'),",
            "'secret',",
        }
    return False


def _remove_allowed_snippets(line: str) -> str:
    """Remove explicitly allowed bounded metadata names from a line.

    Args:
        line: Source line.

    Returns:
        Source line with allowlisted snippets removed.
    """
    sanitized = line
    for snippet in ALLOWED_RUNTIME_SNIPPETS:
        sanitized = sanitized.replace(snippet, "")
    return sanitized


def _is_comment_only_line(line: str) -> bool:
    """Return whether a line is a Dart comment-only line.

    Args:
        line: Source line.

    Returns:
        True when the line contains only a Dart comment.
    """
    stripped = line.strip()
    return stripped.startswith("//") or stripped.startswith("*")


def main(argv: list[str] | None = None) -> int:
    """Run the mobile OCR UI privacy scanner.

    Args:
        argv: Optional CLI argument list.

    Returns:
        Process exit code. Zero means no findings.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Lemon-Aid project root. Defaults to the current directory.",
    )
    args = parser.parse_args(argv)

    project_root = args.project_root.resolve()
    files = list(iter_mobile_runtime_files(project_root))
    findings = scan_mobile_runtime_source(project_root)
    if findings:
        for finding in findings:
            print(
                f"{finding.path}:{finding.line}: {finding.code} {finding.detail}",
                file=sys.stderr,
            )
        return 1
    print(f"mobile_ocr_ui_privacy_ok files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
