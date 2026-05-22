"""Audit a detect-secrets baseline without printing candidate values.

The baseline is a local safety gate for preventing new credential material from
entering the repository. This script provides a second, bounded review layer:
it classifies existing findings by context while keeping candidate line content
out of stdout, stderr, and generated reports.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

LOW_SEVERITY = "low"
MEDIUM_SEVERITY = "medium"
HIGH_SEVERITY = "high"
KNOWN_LOW_RISK_CATEGORIES = frozenset(
    {
        "content_hash",
        "design_asset",
        "documented_placeholder",
        "local_dev_default",
        "env_example_placeholder",
        "framework_identifier",
        "keyword_reference",
        "sample_key_parameter",
        "test_fixture",
    }
)


@dataclass(frozen=True)
class BaselineFinding:
    """One detect-secrets baseline finding with no candidate value.

    Attributes:
        path: Project-relative path from the detect-secrets baseline.
        line_number: One-based line number reported by detect-secrets.
        detector_type: Detect-secrets detector type.
        category: Local bounded classification.
        severity: Review severity.
        reason: Short reason that does not include line content.
    """

    path: str
    line_number: int
    detector_type: str
    category: str
    severity: str
    reason: str


@dataclass(frozen=True)
class BaselineAudit:
    """Classified detect-secrets baseline audit result.

    Attributes:
        findings: Classified findings.
        files: Number of files with baseline findings.
    """

    findings: tuple[BaselineFinding, ...]
    files: int

    @property
    def finding_count(self) -> int:
        """Return the total classified finding count."""
        return len(self.findings)

    @property
    def manual_review_count(self) -> int:
        """Return the number of high-severity manual-review findings."""
        return sum(1 for finding in self.findings if finding.severity == HIGH_SEVERITY)


def audit_baseline(*, baseline_path: Path, repo_root: Path) -> BaselineAudit:
    """Classify findings in a detect-secrets baseline.

    Args:
        baseline_path: Path to ``.secrets.baseline``.
        repo_root: Lemon Aid project root used only for bounded line inspection.

    Returns:
        Classified baseline audit.

    Raises:
        ValueError: If the baseline is not a JSON object.
    """
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("baseline_must_be_json_object")
    results = payload.get("results", {})
    if not isinstance(results, dict):
        raise ValueError("baseline_results_must_be_json_object")

    findings: list[BaselineFinding] = []
    for raw_path, entries in sorted(results.items()):
        if not isinstance(entries, list):
            continue
        path = str(raw_path)
        line_cache: dict[int, str] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            line_number = int(entry.get("line_number", 0))
            detector_type = str(entry.get("type", "unknown"))
            line_text = _line_text(repo_root / path, line_number, line_cache)
            category, severity, reason = _classify(path, detector_type, line_text)
            findings.append(
                BaselineFinding(
                    path=path,
                    line_number=line_number,
                    detector_type=detector_type,
                    category=category,
                    severity=severity,
                    reason=reason,
                )
            )
    return BaselineAudit(findings=tuple(findings), files=len(results))


def _line_text(path: Path, line_number: int, cache: dict[int, str]) -> str:
    """Read one source line for classification without returning it to callers.

    Args:
        path: Candidate file path.
        line_number: One-based line number.
        cache: Mutable cache keyed by line number.

    Returns:
        Source line text for local classification, or an empty string.
    """
    if line_number <= 0:
        return ""
    if line_number in cache:
        return cache[line_number]
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        cache[line_number] = ""
        return ""
    text = lines[line_number - 1] if line_number <= len(lines) else ""
    cache[line_number] = text
    return text


def _classify(path: str, detector_type: str, line_text: str) -> tuple[str, str, str]:
    """Classify one baseline finding using path and bounded local context.

    Args:
        path: Project-relative candidate path.
        detector_type: Detect-secrets detector type.
        line_text: Source line text. This value must not be printed or persisted.

    Returns:
        ``(category, severity, reason)`` tuple.
    """
    normalized_path = path.replace("\\", "/")
    lowered_line = line_text.lower()

    classification: tuple[str, str, str] | None = None
    if "/tests/" in f"/{normalized_path}":
        classification = ("test_fixture", LOW_SEVERITY, "candidate is inside test code")
    elif normalized_path == "backend/.env.example":
        classification = (
            "env_example_placeholder",
            LOW_SEVERITY,
            "candidate is in committed example environment file",
        )
    elif _looks_like_local_dev_default(normalized_path, lowered_line):
        classification = (
            "local_dev_default",
            LOW_SEVERITY,
            "candidate is local development sentinel",
        )
    elif (
        normalized_path.startswith("mobile/uiux/") and detector_type == "Base64 High Entropy String"
    ):
        classification = ("design_asset", LOW_SEVERITY, "candidate is embedded design asset data")
    elif _looks_like_content_hash(normalized_path, detector_type, lowered_line):
        classification = (
            "content_hash",
            LOW_SEVERITY,
            "candidate is checksum or source artifact hash",
        )
    elif _looks_like_framework_identifier(normalized_path, detector_type):
        classification = (
            "framework_identifier",
            LOW_SEVERITY,
            "candidate is tool-generated identifier",
        )
    elif _looks_like_keyword_reference(normalized_path, detector_type, lowered_line):
        classification = (
            "keyword_reference",
            LOW_SEVERITY,
            "candidate is a secret field name reference",
        )
    elif normalized_path == "backend/Nutrition-backend/src/nutrition/mfds_client.py":
        classification = ("sample_key_parameter", LOW_SEVERITY, "candidate is sample key parameter")
    elif _is_documentation_path(normalized_path):
        classification = (
            "documented_placeholder",
            MEDIUM_SEVERITY,
            "candidate is in documentation",
        )
    else:
        classification = ("manual_review", HIGH_SEVERITY, "candidate needs human review")
    return classification


def _looks_like_local_dev_default(path: str, lowered_line: str) -> bool:
    """Return whether a finding is an explicit local development default.

    Args:
        path: Project-relative candidate path.
        lowered_line: Lowercase source line.

    Returns:
        Whether the line is a known local-only sentinel/default.
    """
    if path == "backend/Nutrition-backend/src/config.py":
        return "localhost" in lowered_line or "development-insecure" in lowered_line
    if path == "config/implementation-readiness.settings.json":
        return "default_for_local_example" in lowered_line and "localhost" in lowered_line
    return False


def _looks_like_content_hash(path: str, detector_type: str, lowered_line: str) -> bool:
    """Return whether a finding appears to be a content hash.

    Args:
        path: Project-relative candidate path.
        detector_type: Detect-secrets detector type.
        lowered_line: Lowercase source line.

    Returns:
        Whether local context indicates checksum-style content.
    """
    if detector_type != "Hex High Entropy String":
        return False
    if "sha256" in lowered_line or "digest" in lowered_line or "hash" in lowered_line:
        return True
    return "kdris" in path or path == "backend/scripts/prepare_kdris_2025_digitization.py"


def _looks_like_framework_identifier(path: str, detector_type: str) -> bool:
    """Return whether a finding appears to be a generated framework ID.

    Args:
        path: Project-relative candidate path.
        detector_type: Detect-secrets detector type.

    Returns:
        Whether path/type are known framework identifier contexts.
    """
    if detector_type != "Hex High Entropy String":
        return False
    return path in {
        "mobile/.metadata",
        "mobile/ios/Runner.xcodeproj/xcshareddata/xcschemes/Runner.xcscheme",
    }


def _looks_like_keyword_reference(path: str, detector_type: str, lowered_line: str) -> bool:
    """Return whether a finding is a code reference to secret-shaped fields.

    Args:
        path: Project-relative candidate path.
        detector_type: Detect-secrets detector type.
        lowered_line: Lowercase source line.

    Returns:
        Whether the line appears to name a secret field without storing a value.
    """
    if detector_type != "Secret Keyword":
        return False
    return (
        path.endswith(".py") and any(token in lowered_line for token in ("secretstr", "secret_key"))
    ) or path == "config/implementation-readiness.settings.json"


def _is_documentation_path(path: str) -> bool:
    """Return whether a finding lives in documentation or generated guide text.

    Args:
        path: Project-relative candidate path.

    Returns:
        Whether the path is a documentation/report path.
    """
    return (
        path.startswith("docs/")
        or path.startswith("outputs/")
        or path.startswith("records/")
        or path in {"PROJECT_GUIDE.md", "README.md", "guide.html"}
    )


def render_text_report(audit: BaselineAudit) -> str:
    """Render a bounded text report without candidate values.

    Args:
        audit: Classified baseline audit.

    Returns:
        Multi-line report safe for stdout or repo-local documentation.
    """
    by_category = Counter(finding.category for finding in audit.findings)
    by_severity = Counter(finding.severity for finding in audit.findings)
    by_detector = Counter(finding.detector_type for finding in audit.findings)
    lines = [
        (
            "detect_secrets_baseline_audit "
            f"files={audit.files} findings={audit.finding_count} "
            f"manual_review={audit.manual_review_count} cleartext_values_printed=false"
        ),
        "by_severity:",
    ]
    lines.extend(f"  {key}={by_severity[key]}" for key in sorted(by_severity))
    lines.append("by_category:")
    lines.extend(f"  {key}={by_category[key]}" for key in sorted(by_category))
    lines.append("by_detector:")
    lines.extend(f"  {key}={by_detector[key]}" for key in sorted(by_detector))
    manual_findings = [
        finding for finding in audit.findings if finding.category not in KNOWN_LOW_RISK_CATEGORIES
    ]
    if manual_findings:
        lines.append("review_items:")
        for finding in manual_findings:
            lines.append(
                "  "
                f"{finding.path}:{finding.line_number} "
                f"type={finding.detector_type} "
                f"category={finding.category} "
                f"severity={finding.severity} "
                f"reason={finding.reason}"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the detect-secrets baseline audit CLI.

    Args:
        argv: Optional CLI argument list.

    Returns:
        Process exit code. Non-zero only when requested fail conditions occur.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path(".secrets.baseline"),
        help="Path to the detect-secrets baseline.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Lemon Aid project root.",
    )
    parser.add_argument(
        "--fail-on-manual-review",
        action="store_true",
        help="Return non-zero when high-severity findings remain.",
    )
    args = parser.parse_args(argv)

    audit = audit_baseline(baseline_path=args.baseline, repo_root=args.repo_root)
    report = render_text_report(audit)
    print(report)
    if args.fail_on_manual_review and audit.manual_review_count:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
