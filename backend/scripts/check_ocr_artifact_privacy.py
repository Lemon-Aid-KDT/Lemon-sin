"""Check OCR evaluation artifacts for raw text, secrets, and local paths.

This script is a local/CI gate for generated OCR artifacts. It parses JSON and
JSONL files structurally, rejects forbidden raw payload keys, and scans bounded
string values for local filesystem literals. It does not upload files, open a
database connection, call OCR providers, or call LLM services.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "ocr-artifact-privacy-check-v1"
DEFAULT_EXTENSIONS = (".json", ".jsonl")
RAW_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "image_bytes",
        "ocr_text",
        "provider_payload",
        "raw_image",
        "raw_model_response",
        "raw_ocr_text",
        "raw_provider_payload",
        "request_headers",
        "secret",
        "service_key",
    }
)
LITERAL_FORBIDDEN_KEYS = frozenset(
    {
        "absolute_path",
        "image_path",
        "local_path",
        "product_dir",
    }
)
LOCAL_PATH_MARKERS = ("/Users/", "/Volumes/", "file://", "\\Users\\", "\\Volumes\\")


@dataclass(frozen=True)
class PrivacyFinding:
    """One privacy finding in an artifact."""

    path: str
    location: str
    reason: str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for artifact privacy checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        action="append",
        required=True,
        help="Artifact file or directory to scan. May be repeated.",
    )
    parser.add_argument(
        "--extension",
        action="append",
        choices=DEFAULT_EXTENSIONS,
        help="File extension to scan. Defaults to JSON and JSONL.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Skip missing paths instead of failing.",
    )
    parser.add_argument(
        "--strict-literal-keys",
        action="store_true",
        help="Also reject image_path/product_dir-style keys used only by source manifests.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the privacy check and print a JSON summary."""
    args = parse_args()
    summary = check_artifact_privacy(
        paths=[path.expanduser().resolve() for path in args.path],
        extensions=tuple(args.extension or DEFAULT_EXTENSIONS),
        allow_missing=args.allow_missing,
        strict_literal_keys=args.strict_literal_keys,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if summary["finding_count"]:
        raise SystemExit(1)


def check_artifact_privacy(
    *,
    paths: list[Path],
    extensions: tuple[str, ...] = DEFAULT_EXTENSIONS,
    allow_missing: bool = False,
    strict_literal_keys: bool = False,
) -> dict[str, object]:
    """Return a privacy-check summary for OCR artifacts.

    Args:
        paths: Files or directories to scan.
        extensions: File extensions to include.
        allow_missing: Whether missing paths are skipped.
        strict_literal_keys: Whether source-manifest path keys are rejected even
            when their values are tokenized.

    Returns:
        JSON-serializable summary with finding counts and finding details.

    Raises:
        FileNotFoundError: If a requested path is missing and ``allow_missing``
            is false.
        ValueError: If unsupported file extensions are requested.
    """
    normalized_extensions = _normalize_extensions(extensions)
    files = _collect_files(
        paths=paths,
        extensions=normalized_extensions,
        allow_missing=allow_missing,
    )
    findings: list[PrivacyFinding] = []
    json_value_count = 0
    for path in files:
        file_findings, values_seen = _scan_file(
            path,
            strict_literal_keys=strict_literal_keys,
        )
        findings.extend(file_findings)
        json_value_count += values_seen

    return {
        "schema_version": SCHEMA_VERSION,
        "paths_checked": [str(path) for path in paths],
        "extensions": list(normalized_extensions),
        "strict_literal_keys": strict_literal_keys,
        "file_count": len(files),
        "json_value_count": json_value_count,
        "finding_count": len(findings),
        "passed": not findings,
        "findings": [
            {"path": item.path, "location": item.location, "reason": item.reason}
            for item in findings
        ],
        "db_write_performed": False,
        "external_transfer_performed": False,
    }


def _collect_files(
    *,
    paths: list[Path],
    extensions: tuple[str, ...],
    allow_missing: bool,
) -> list[Path]:
    """Return files matching the configured extensions."""
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            if allow_missing:
                continue
            raise FileNotFoundError(path)
        if path.is_file():
            if path.suffix in extensions:
                files.append(path)
            continue
        files.extend(
            file for file in sorted(path.rglob("*")) if file.is_file() and file.suffix in extensions
        )
    return sorted(set(files))


def _scan_file(path: Path, *, strict_literal_keys: bool) -> tuple[list[PrivacyFinding], int]:
    """Scan one JSON or JSONL artifact."""
    findings: list[PrivacyFinding] = []
    values_seen = 0
    if path.suffix == ".jsonl":
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                findings.append(
                    PrivacyFinding(
                        path=str(path),
                        location=f"line:{line_number}",
                        reason=f"invalid_jsonl:{exc.msg}",
                    )
                )
                continue
            values_seen += _scan_value(
                value,
                findings=findings,
                path=path,
                location=f"line:{line_number}",
                strict_literal_keys=strict_literal_keys,
            )
        return findings, values_seen

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [PrivacyFinding(path=str(path), location="$", reason=f"invalid_json:{exc.msg}")], 0
    values_seen += _scan_value(
        value,
        findings=findings,
        path=path,
        location="$",
        strict_literal_keys=strict_literal_keys,
    )
    return findings, values_seen


def _scan_value(
    value: Any,
    *,
    findings: list[PrivacyFinding],
    path: Path,
    location: str,
    strict_literal_keys: bool,
) -> int:
    """Scan a decoded JSON value recursively and return visited value count."""
    count = 1
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key)
            key_lower = key_text.lower()
            nested_location = f"{location}.{key_text}"
            if key_lower in RAW_FORBIDDEN_KEYS:
                findings.append(
                    PrivacyFinding(
                        path=str(path),
                        location=nested_location,
                        reason=f"forbidden_raw_key:{key_text}",
                    )
                )
            if strict_literal_keys and key_lower in LITERAL_FORBIDDEN_KEYS:
                findings.append(
                    PrivacyFinding(
                        path=str(path),
                        location=nested_location,
                        reason=f"forbidden_literal_key:{key_text}",
                    )
                )
            count += _scan_value(
                nested,
                findings=findings,
                path=path,
                location=nested_location,
                strict_literal_keys=strict_literal_keys,
            )
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            count += _scan_value(
                nested,
                findings=findings,
                path=path,
                location=f"{location}[{index}]",
                strict_literal_keys=strict_literal_keys,
            )
    elif isinstance(value, str) and any(marker in value for marker in LOCAL_PATH_MARKERS):
        findings.append(
            PrivacyFinding(
                path=str(path),
                location=location,
                reason="local_path_literal",
            )
        )
    return count


def _normalize_extensions(values: tuple[str, ...]) -> tuple[str, ...]:
    """Return supported extensions with leading dots."""
    normalized = tuple(value if value.startswith(".") else f".{value}" for value in values)
    unsupported = sorted(set(normalized) - set(DEFAULT_EXTENSIONS))
    if unsupported:
        raise ValueError(f"Unsupported extension(s): {unsupported}")
    return normalized


if __name__ == "__main__":
    main()
