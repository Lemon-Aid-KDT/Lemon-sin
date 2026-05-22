"""Tests for the detect-secrets baseline audit helper."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import audit_detect_secrets_baseline as audit


def test_audit_classifies_known_low_risk_contexts(tmp_path: Path) -> None:
    """Verify common baseline false-positive contexts are bounded."""
    repo_root = tmp_path
    local_url = "postgresql://user" + ":pass@host/db"
    _write(repo_root / "backend/.env.example", "DATABASE_URL=" + local_url + "\n")
    _write(repo_root / "data/nutrition_reference/kdris/manifest.json", '"sha256": "' + "a" * 64)
    _write(repo_root / "mobile/.metadata", "project_type: app\n")
    _write(repo_root / "backend/Nutrition-backend/tests/unit/test_config.py", "TOKEN='test'\n")
    baseline_path = _write_baseline(
        repo_root,
        {
            "backend/.env.example": [{"type": "Basic Auth Credentials", "line_number": 1}],
            "data/nutrition_reference/kdris/manifest.json": [
                {"type": "Hex High Entropy String", "line_number": 1}
            ],
            "mobile/.metadata": [{"type": "Hex High Entropy String", "line_number": 1}],
            "backend/Nutrition-backend/tests/unit/test_config.py": [
                {"type": "Secret Keyword", "line_number": 1}
            ],
        },
    )

    result = audit.audit_baseline(baseline_path=baseline_path, repo_root=repo_root)

    assert [(finding.category, finding.severity) for finding in result.findings] == [
        ("env_example_placeholder", "low"),
        ("test_fixture", "low"),
        ("content_hash", "low"),
        ("framework_identifier", "low"),
    ]
    assert result.manual_review_count == 0


def test_audit_keeps_documentation_as_medium_review(tmp_path: Path) -> None:
    """Verify docs candidates remain visible without being high severity."""
    repo_root = tmp_path
    local_url = "postgresql://user" + ":pass@host/db"
    _write(repo_root / "docs/setup.md", "DATABASE_URL=" + local_url + "\n")
    baseline_path = _write_baseline(
        repo_root,
        {"docs/setup.md": [{"type": "Basic Auth Credentials", "line_number": 1}]},
    )

    result = audit.audit_baseline(baseline_path=baseline_path, repo_root=repo_root)

    assert [(finding.category, finding.severity) for finding in result.findings] == [
        ("documented_placeholder", "medium")
    ]
    assert result.manual_review_count == 0


def test_report_never_prints_candidate_line_content(tmp_path: Path) -> None:
    """Verify report output excludes candidate line text."""
    repo_root = tmp_path
    candidate_value = "token-value-that-should-not-appear"
    _write(repo_root / "unknown.txt", "API_" + "TOKEN=" + candidate_value + "\n")
    baseline_path = _write_baseline(
        repo_root,
        {"unknown.txt": [{"type": "Secret Keyword", "line_number": 1}]},
    )

    result = audit.audit_baseline(baseline_path=baseline_path, repo_root=repo_root)
    report = audit.render_text_report(result)

    assert "unknown.txt:1" in report
    assert "manual_review=1" in report
    assert candidate_value not in report
    assert "API_TOKEN" not in report


def test_main_can_fail_on_manual_review(tmp_path: Path, capsys) -> None:
    """Verify CLI can fail when unclassified findings remain."""
    repo_root = tmp_path
    _write(repo_root / "unknown.txt", "value\n")
    baseline_path = _write_baseline(
        repo_root,
        {"unknown.txt": [{"type": "Secret Keyword", "line_number": 1}]},
    )

    exit_code = audit.main(
        [
            "--baseline",
            str(baseline_path),
            "--repo-root",
            str(repo_root),
            "--fail-on-manual-review",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "manual_review=1" in captured.out


def _write(path: Path, text: str) -> None:
    """Write text to a fixture path.

    Args:
        path: Fixture path.
        text: Fixture content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_baseline(repo_root: Path, results: dict[str, list[dict[str, object]]]) -> Path:
    """Write a minimal detect-secrets baseline.

    Args:
        repo_root: Fixture project root.
        results: Baseline results payload.

    Returns:
        Baseline path.
    """
    baseline_path = repo_root / ".secrets.baseline"
    baseline_path.write_text(
        json.dumps({"version": "1.5.0", "results": results}),
        encoding="utf-8",
    )
    return baseline_path
