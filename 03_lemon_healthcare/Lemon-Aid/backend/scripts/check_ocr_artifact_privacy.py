"""Check generated OCR artifacts for privacy-sensitive leakage.

This operator gate is intentionally conservative. It is meant for generated
OCR evaluation directories before a PR or artifact handoff, and rejects raw OCR
keys, provider payload keys, common secret assignments, and developer-local
filesystem paths.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FORBIDDEN_JSON_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "clova_ocr_secret",
        "image_bytes",
        "ocr_text",
        "provider_payload",
        "raw_image",
        "raw_ocr_text",
        "raw_provider_payload",
        "request_headers",
        "secret",
        "service_key",
        "x_ocr_secret",
    }
)
TEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("developer_home_path", re.compile(r"/Users/[A-Za-z0-9._-]+")),
    ("external_volume_path", re.compile(r"/Volumes/[^\s`]+")),
    (
        "clova_secret_assignment",
        re.compile(r"\bCLOVA_OCR_SECRET\s*[:=]\s*(?!$|<|\$|\.\.\.|placeholder|test|dummy)\S+"),
    ),
    (
        "google_api_key_assignment",
        re.compile(r"\bGOOGLE_CLOUD_API_KEY\s*[:=]\s*(?!$|<|\$|\.\.\.|placeholder|test|dummy)\S+"),
    ),
    (
        "lemon_api_token_assignment",
        re.compile(r"\bLEMON_API_TOKEN\s*[:=]\s*(?!$|<|\$|\.\.\.|placeholder|test|dummy)\S+"),
    ),
    (
        "authorization_bearer",
        re.compile(r"\bAuthorization\s*[:=]\s*Bearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    ),
)
SCAN_SUFFIXES = frozenset({".json", ".jsonl", ".md", ".txt", ".csv", ".tsv", ".log"})


@dataclass(frozen=True)
class PrivacyFinding:
    """One privacy finding in a generated OCR artifact.

    Attributes:
        path: File path where the finding was detected.
        line: One-based line number, or 1 for structured JSON documents.
        code: Stable finding code.
        detail: Bounded detail that never includes matched sensitive text.
    """

    path: Path
    line: int
    code: str
    detail: str


def iter_artifact_files(paths: list[Path]) -> Iterator[Path]:
    """Yield candidate artifact files below paths.

    Args:
        paths: Files or directories to scan.

    Yields:
        Existing files with a text artifact suffix.
    """
    for path in paths:
        if path.is_dir():
            for nested in sorted(path.rglob("*")):
                if nested.is_file() and nested.suffix.lower() in SCAN_SUFFIXES:
                    yield nested
        elif path.is_file() and path.suffix.lower() in SCAN_SUFFIXES:
            yield path


def scan_paths(paths: list[Path]) -> list[PrivacyFinding]:
    """Scan artifact paths for privacy findings.

    Args:
        paths: Files or directories to scan.

    Returns:
        Privacy findings sorted by file traversal order.
    """
    findings: list[PrivacyFinding] = []
    for path in iter_artifact_files(paths):
        findings.extend(scan_file(path))
    return findings


def scan_file(path: Path) -> list[PrivacyFinding]:
    """Scan one artifact file.

    Args:
        path: Artifact file path.

    Returns:
        Privacy findings for the file.
    """
    findings: list[PrivacyFinding] = []
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        findings.extend(_scan_json_document(path, text))
    elif suffix == ".jsonl":
        findings.extend(_scan_jsonl_document(path, text))
    findings.extend(_scan_text_patterns(path, text))
    return findings


def _scan_json_document(path: Path, text: str) -> list[PrivacyFinding]:
    """Scan a JSON document for forbidden keys.

    Args:
        path: JSON file path.
        text: JSON text.

    Returns:
        Privacy findings for forbidden keys or invalid JSON.
    """
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return [PrivacyFinding(path, 1, "invalid_json", "JSON artifact is not parseable")]
    return _scan_json_value(path, 1, payload)


def _scan_jsonl_document(path: Path, text: str) -> list[PrivacyFinding]:
    """Scan a JSONL document for forbidden keys.

    Args:
        path: JSONL file path.
        text: JSONL text.

    Returns:
        Privacy findings for forbidden keys or invalid JSONL lines.
    """
    findings: list[PrivacyFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            findings.append(
                PrivacyFinding(path, line_number, "invalid_jsonl", "JSONL line is not parseable")
            )
            continue
        findings.extend(_scan_json_value(path, line_number, payload))
    return findings


def _scan_json_value(path: Path, line: int, value: Any) -> list[PrivacyFinding]:
    """Recursively scan a parsed JSON value.

    Args:
        path: Artifact path.
        line: Source line number for this JSON value.
        value: Parsed JSON value.

    Returns:
        Privacy findings for forbidden keys.
    """
    findings: list[PrivacyFinding] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key)
            if key_text.lower() in FORBIDDEN_JSON_KEYS:
                findings.append(
                    PrivacyFinding(
                        path,
                        line,
                        "forbidden_json_key",
                        f"key={key_text}",
                    )
                )
            findings.extend(_scan_json_value(path, line, nested))
    elif isinstance(value, list):
        for item in value:
            findings.extend(_scan_json_value(path, line, item))
    return findings


def _scan_text_patterns(path: Path, text: str) -> list[PrivacyFinding]:
    """Scan text for local paths and secret assignments.

    Args:
        path: Artifact file path.
        text: Artifact text.

    Returns:
        Privacy findings with bounded details.
    """
    findings: list[PrivacyFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for code, pattern in TEXT_PATTERNS:
            if pattern.search(line):
                findings.append(PrivacyFinding(path, line_number, code, "pattern_match"))
    return findings


def main(argv: list[str] | None = None) -> int:
    """Run the artifact privacy scanner.

    Args:
        argv: Optional CLI argument list.

    Returns:
        Process exit code. Zero means no findings.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)

    files = list(iter_artifact_files(args.paths))
    findings = []
    for path in files:
        findings.extend(scan_file(path))
    if findings:
        for finding in findings:
            print(
                f"{finding.path}:{finding.line}: {finding.code} {finding.detail}",
                file=sys.stderr,
            )
        return 1
    print(f"ocr_artifact_privacy_ok files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
