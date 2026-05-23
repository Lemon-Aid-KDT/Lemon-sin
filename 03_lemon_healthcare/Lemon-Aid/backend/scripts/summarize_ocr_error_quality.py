"""Summarize OCR error fixtures with redacted image-quality signals.

This operator tool joins a redacted OCR observation JSONL with its manifest and
recomputes deterministic image-quality metrics for each observed fixture. It is
intentionally bounded: reports include fixture ids, coarse manifest metadata,
OCR status/error code, quality reason codes, and numeric metrics only.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from src.services.supplement_image_quality import analyze_supplement_label_image_quality
from src.services.supplement_intake import ValidatedSupplementImage

SUMMARY_JSON = "ocr-error-quality-summary.json"
SUMMARY_MARKDOWN = "ocr-error-quality-summary.md"
ALLOWED_IMAGE_PATH_ENV_VARS = frozenset(
    {
        "LEMON_OCR_FIXTURE_ROOT",
        "NAVER_TAMPERMONKEY_SOURCE_ROOT",
        "SUPPLEMENT_OCR_FIXTURE_ROOT",
    }
)
RAW_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "clova_ocr_secret",
        "gt_text",
        "image_bytes",
        "image_path",
        "ocr_text",
        "product_dir",
        "provider_payload",
        "raw_image",
        "raw_model_response",
        "raw_ocr_text",
        "raw_provider_payload",
        "request_headers",
        "secret",
        "service_key",
        "source_path",
        "source_root",
        "x_ocr_secret",
    }
)
QUALITY_METRIC_KEYS = (
    "total_pixels",
    "short_edge_px",
    "edge_variance",
    "contrast_stddev",
    "bright_pixel_ratio",
    "border_ink_ratio",
    "aspect_ratio",
)


def build_summary(
    *,
    manifest_path: Path,
    observations_path: Path,
    provider: str,
) -> dict[str, Any]:
    """Build a redacted OCR error quality summary.

    Args:
        manifest_path: Redacted manifest JSONL used for the OCR run.
        observations_path: Redacted provider observation JSONL.
        provider: Provider id to summarize.

    Returns:
        JSON-serializable summary with bounded fields.

    Raises:
        ValueError: If a manifest row cannot be resolved safely.
    """
    manifest_rows = _read_jsonl(manifest_path)
    observation_rows = _read_jsonl(observations_path)
    observations = {
        str(row["fixture_id"]): row
        for row in observation_rows
        if row.get("provider") == provider and row.get("fixture_id")
    }

    error_fixtures: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    quality_status_counts: dict[str, Counter[str]] = defaultdict(Counter)
    issue_code_counts: dict[str, Counter[str]] = defaultdict(Counter)
    metric_values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    observed_count = 0
    for manifest_row in manifest_rows:
        fixture_id = str(manifest_row.get("fixture_id") or "")
        observation = observations.get(fixture_id)
        if observation is None:
            continue
        observed_count += 1
        ocr_status = str(observation.get("status") or "unknown")
        status_counts[ocr_status] += 1

        report = _analyze_manifest_image(manifest_path, manifest_row)
        issue_codes = [issue.reason_code for issue in report.issues]
        quality_status_counts[ocr_status][report.status] += 1
        issue_code_counts[ocr_status].update(issue_codes)
        for key in QUALITY_METRIC_KEYS:
            value = report.metrics.get(key)
            if isinstance(value, int | float):
                metric_values[ocr_status][key].append(float(value))

        if ocr_status == "error":
            error_fixtures.append(
                {
                    "fixture_id": fixture_id,
                    "category": _coerce_optional_str(manifest_row.get("category")),
                    "section": _coerce_optional_str(manifest_row.get("section")),
                    "mime_type": _coerce_optional_str(manifest_row.get("mime_type")),
                    "width": _coerce_optional_int(manifest_row.get("width")),
                    "height": _coerce_optional_int(manifest_row.get("height")),
                    "file_size_bytes": _coerce_optional_int(manifest_row.get("file_size_bytes")),
                    "size_bucket": _coerce_optional_str(manifest_row.get("size_bucket")),
                    "error_code": _coerce_optional_str(observation.get("error_code")),
                    "quality_status": report.status,
                    "issue_codes": issue_codes,
                    "retake_reasons": list(report.retake_reasons),
                    "metrics": {
                        key: report.metrics[key]
                        for key in QUALITY_METRIC_KEYS
                        if key in report.metrics
                    },
                }
            )

    summary: dict[str, Any] = {
        "schema_version": "ocr-error-quality-summary-v1",
        "provider": provider,
        "manifest_fixture_count": len(manifest_rows),
        "observation_count": observed_count,
        "status_counts": dict(sorted(status_counts.items())),
        "error_fixture_count": len(error_fixtures),
        "error_fixtures": error_fixtures,
        "quality_status_counts_by_ocr_status": _counter_map_to_dict(quality_status_counts),
        "issue_code_counts_by_ocr_status": _counter_map_to_dict(issue_code_counts),
        "metric_averages_by_ocr_status": _average_metric_values(metric_values),
        "privacy": {
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "raw_model_response_stored": False,
            "raw_image_bytes_stored": False,
            "source_paths_stored": False,
        },
    }
    _reject_forbidden_keys(summary)
    return summary


def write_summary(summary: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Write redacted JSON and Markdown summaries.

    Args:
        summary: Summary returned by :func:`build_summary`.
        output_dir: Directory where report files are written.

    Returns:
        JSON and Markdown output paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / SUMMARY_JSON
    markdown_path = output_dir / SUMMARY_MARKDOWN
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown(summary), encoding="utf-8")
    return json_path, markdown_path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file into object rows.

    Args:
        path: JSONL file path.

    Returns:
        Parsed object rows.

    Raises:
        ValueError: If a non-empty line is not a JSON object.
    """
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path.name}:{line_number} must be a JSON object.")
        rows.append(payload)
    return rows


def _analyze_manifest_image(manifest_path: Path, manifest_row: dict[str, Any]):
    """Analyze a manifest image without returning path or bytes.

    Args:
        manifest_path: Source manifest path.
        manifest_row: Manifest row containing safe image metadata and image path.

    Returns:
        Redacted image-quality report.
    """
    image_path = _resolve_fixture_image_path(manifest_path, str(manifest_row.get("image_path")))
    image_bytes = image_path.read_bytes()
    metadata = ValidatedSupplementImage(
        sha256=str(manifest_row.get("image_sha256") or "0" * 64),
        mime_type=str(manifest_row.get("mime_type") or "application/octet-stream"),
        size_bytes=int(manifest_row.get("file_size_bytes") or len(image_bytes)),
        width=int(manifest_row.get("width") or 0),
        height=int(manifest_row.get("height") or 0),
    )
    return analyze_supplement_label_image_quality(image_bytes, metadata)


def _resolve_fixture_image_path(manifest_path: Path, image_path: str) -> Path:
    """Resolve a manifest image path under an allowlisted root.

    Args:
        manifest_path: Manifest path used for relative paths.
        image_path: Relative, absolute legacy, or ``$ENV/path`` image path.

    Returns:
        Absolute image path used only for local reading.

    Raises:
        ValueError: If an env-token path is unsupported, unset, or unsafe.
    """
    if image_path.startswith("$"):
        env_name, _, relative_text = image_path[1:].partition("/")
        if env_name not in ALLOWED_IMAGE_PATH_ENV_VARS:
            raise ValueError(f"OCR fixture image_path env is not allowlisted: {env_name}")
        env_root = os.environ.get(env_name)
        if not env_root:
            raise ValueError(f"OCR fixture image_path env is not set: {env_name}")
        relative_path = PurePosixPath(relative_text)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError("OCR fixture image_path env suffix must stay under the image root.")
        return (Path(env_root).expanduser() / Path(*relative_path.parts)).resolve()

    path = Path(image_path)
    if path.is_absolute():
        return path.expanduser().resolve()
    return (manifest_path.parent / path).resolve()


def _counter_map_to_dict(counters: dict[str, Counter[str]]) -> dict[str, dict[str, int]]:
    """Convert nested counters to sorted JSON dictionaries."""
    return {
        status: dict(sorted(counter.items()))
        for status, counter in sorted(counters.items(), key=lambda item: item[0])
    }


def _average_metric_values(
    values: dict[str, dict[str, list[float]]],
) -> dict[str, dict[str, float]]:
    """Average metric values per OCR status.

    Args:
        values: Nested metric values by OCR status.

    Returns:
        Rounded averages by status and metric name.
    """
    averaged: dict[str, dict[str, float]] = {}
    for status, metrics in sorted(values.items()):
        averaged[status] = {
            key: round(sum(items) / len(items), 4)
            for key, items in sorted(metrics.items())
            if items
        }
    return averaged


def _render_markdown(summary: dict[str, Any]) -> str:
    """Render a concise Markdown report.

    Args:
        summary: Redacted summary payload.

    Returns:
        Markdown report.
    """
    lines = [
        "# OCR Error Quality Summary",
        "",
        "## Overview",
        "",
        f"- Provider: `{summary['provider']}`",
        f"- Manifest fixtures: `{summary['manifest_fixture_count']}`",
        f"- Observations: `{summary['observation_count']}`",
        f"- OCR error fixtures: `{summary['error_fixture_count']}`",
        "",
        "## Status Counts",
        "",
        "| OCR status | Count |",
        "| --- | ---: |",
    ]
    for status, count in summary["status_counts"].items():
        lines.append(f"| `{status}` | {count} |")

    lines.extend(
        [
            "",
            "## Error Fixtures",
            "",
            "| Fixture | Category | Error | Quality | Issues | Key metrics |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in summary["error_fixtures"]:
        metrics = row["metrics"]
        metric_text = (
            f"edge={metrics.get('edge_variance')}, "
            f"contrast={metrics.get('contrast_stddev')}, "
            f"bright={metrics.get('bright_pixel_ratio')}, "
            f"border={metrics.get('border_ink_ratio')}"
        )
        issues = ", ".join(f"`{code}`" for code in row["issue_codes"]) or "none"
        lines.append(
            "| "
            f"`{row['fixture_id']}` | "
            f"{row.get('category') or ''} | "
            f"`{row.get('error_code') or ''}` | "
            f"`{row['quality_status']}` | "
            f"{issues} | "
            f"{metric_text} |"
        )

    lines.extend(
        [
            "",
            "## Quality Status By OCR Status",
            "",
            "| OCR status | Quality status | Count |",
            "| --- | --- | ---: |",
        ]
    )
    for ocr_status, counts in summary["quality_status_counts_by_ocr_status"].items():
        for quality_status, count in counts.items():
            lines.append(f"| `{ocr_status}` | `{quality_status}` | {count} |")

    lines.extend(
        [
            "",
            "## Privacy",
            "",
            "- Raw OCR text stored: `false`",
            "- Raw provider payload stored: `false`",
            "- Raw model response stored: `false`",
            "- Raw image bytes stored: `false`",
            "- Source paths stored: `false`",
            "",
        ]
    )
    return "\n".join(lines)


def _reject_forbidden_keys(value: Any) -> None:
    """Reject forbidden keys before writing summary artifacts.

    Args:
        value: Candidate JSON value.

    Raises:
        ValueError: If a forbidden key is present.
    """
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in RAW_FORBIDDEN_KEYS:
                raise ValueError(f"forbidden summary key: {key}")
            _reject_forbidden_keys(nested)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden_keys(item)


def _coerce_optional_str(value: Any) -> str | None:
    """Return a short string or None."""
    return str(value)[:160] if value not in {None, ""} else None


def _coerce_optional_int(value: Any) -> int | None:
    """Return an integer or None."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _display_path(path: Path) -> str:
    """Return a stable CLI path without forcing absolute local paths."""
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def main(argv: list[str] | None = None) -> int:
    """Run the redacted OCR error quality summarizer.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--provider", default="paddleocr_local")
    args = parser.parse_args(argv)

    summary = build_summary(
        manifest_path=args.manifest,
        observations_path=args.observations,
        provider=args.provider,
    )
    json_path, markdown_path = write_summary(summary, args.output_dir)
    print(
        json.dumps(
            {
                "json": _display_path(json_path),
                "markdown": _display_path(markdown_path),
                "error_fixture_count": summary["error_fixture_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
