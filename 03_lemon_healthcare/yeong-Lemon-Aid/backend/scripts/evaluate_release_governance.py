"""Evaluate cross-cutting release governance from redacted reports.

The input manifest must contain aggregate metrics and artifact provenance only.
This script does not call OCR providers, read raw images, or store raw OCR text.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path

from src.services.governance import (
    GovernanceGateError,
    evaluate_release_governance_manifest,
)


def main() -> None:
    """Run the release-governance evaluator from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=False, type=Path)
    args = parser.parse_args()

    summary = evaluate_manifest(args.manifest)
    if args.output_dir is None:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "release-governance-report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "release-governance-report.md").write_text(
        _render_markdown(summary),
        encoding="utf-8",
    )


def evaluate_manifest(manifest_path: Path) -> dict[str, object]:
    """Evaluate one release-governance manifest.

    Args:
        manifest_path: JSON manifest path containing redacted reports.

    Returns:
        Governance gate report as a JSON-serializable dictionary.

    Raises:
        GovernanceGateError: If the manifest contains raw fields or invalid data.
    """
    parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise GovernanceGateError("Governance manifest must be a JSON object.")
    report = evaluate_release_governance_manifest(parsed)
    return report.model_dump(mode="json")


def _render_markdown(summary: Mapping[str, object]) -> str:
    """Render a compact Markdown release-governance report.

    Args:
        summary: Governance gate summary.

    Returns:
        Markdown report text.
    """
    lines = [
        "# Release Governance Report",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Target environment: `{summary['target_environment']}`",
        f"- Release target: `{summary['release_target']}`",
        f"- Gate mode: `{summary['gate_mode']}`",
        f"- Overall status: `{summary['overall_status']}`",
        "",
        "## Pipeline Status",
    ]
    statuses = summary.get("pipeline_statuses", [])
    if isinstance(statuses, list):
        for status in statuses:
            if not isinstance(status, Mapping):
                continue
            lines.append(
                "- "
                f"`{status.get('pipeline')}`: `{status.get('status')}` "
                f"(blocked: `{status.get('release_blocked')}`)"
            )
            reasons = status.get("reasons", [])
            if isinstance(reasons, list) and reasons:
                lines.append(f"  - reasons: `{', '.join(str(item) for item in reasons)}`")
    lines.extend(
        [
            "",
            "## Privacy Posture",
            "",
            "- Raw image artifacts stored: `false`",
            "- Raw OCR text stored: `false`",
            "- Raw provider payload stored: `false`",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
