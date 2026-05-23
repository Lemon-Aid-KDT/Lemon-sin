"""Tests for official OCR KPI readiness gate."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import check_ocr_kpi_readiness as checker


def _write_evaluation(path: Path, payload: dict[str, object]) -> None:
    """Write an evaluation JSON file.

    Args:
        path: Destination path.
        payload: Evaluation summary payload.
    """
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def _ready_payload() -> dict[str, object]:
    """Return a minimal official-KPI-ready payload.

    Returns:
        Redacted evaluation summary.
    """
    return {
        "fixture_count": 16,
        "scoreable_fixture_count": 16,
        "provisional_fixture_count": 0,
        "expected_quality_warnings": [],
        "raw_artifacts_stored": False,
        "raw_ocr_text_stored": False,
        "providers": {
            "paddleocr_local": {
                "errors": 0,
                "scoreable_ingredient_name_exact_rate": 0.95,
            }
        },
    }


def test_check_kpi_readiness_accepts_verified_scoreable_metric(tmp_path: Path) -> None:
    """Verify a fully scoreable, non-provisional evaluation passes."""
    evaluation = tmp_path / "evaluation.json"
    _write_evaluation(evaluation, _ready_payload())

    result = checker.check_kpi_readiness(evaluation_path=evaluation)

    assert result.ok is True
    assert result.findings == ()


def test_check_kpi_readiness_rejects_provisional_expected(tmp_path: Path) -> None:
    """Verify provisional expected rows cannot support official KPI claims."""
    evaluation = tmp_path / "evaluation.json"
    payload = _ready_payload()
    payload["scoreable_fixture_count"] = 7
    payload["provisional_fixture_count"] = 16
    payload["expected_quality_warnings"] = [{"code": "provisional_expected_fixture"}]
    payload["providers"] = {
        "paddleocr_local": {
            "errors": 2,
            "scoreable_ingredient_name_exact_rate": 0.1111,
        }
    }
    _write_evaluation(evaluation, payload)

    result = checker.check_kpi_readiness(evaluation_path=evaluation)

    assert result.ok is False
    assert [(finding.code, finding.detail) for finding in result.findings] == [
        ("scoreable_fixture_count_below_min", "value=7 min=16"),
        ("provisional_fixture_count_exceeded", "value=16 max=0"),
        ("expected_quality_warnings_exceeded", "value=1 max=0"),
        ("provider_errors_exceeded", "provider=paddleocr_local value=2 max=0"),
        (
            "metric_below_min",
            "provider=paddleocr_local metric=scoreable_ingredient_name_exact_rate "
            "value=0.1111 min=0.95",
        ),
    ]


def test_check_kpi_readiness_rejects_raw_storage_flags(tmp_path: Path) -> None:
    """Verify privacy flags must remain explicitly false."""
    evaluation = tmp_path / "evaluation.json"
    payload = _ready_payload()
    payload["raw_artifacts_stored"] = True
    payload["raw_ocr_text_stored"] = None
    _write_evaluation(evaluation, payload)

    result = checker.check_kpi_readiness(evaluation_path=evaluation)

    assert result.ok is False
    assert [(finding.code, finding.detail) for finding in result.findings] == [
        ("raw_artifacts_flag_not_false", "value=True"),
        ("raw_ocr_text_flag_not_false", "value=None"),
    ]


def test_check_kpi_readiness_reports_missing_provider(tmp_path: Path) -> None:
    """Verify missing provider metrics fail closed."""
    evaluation = tmp_path / "evaluation.json"
    payload = _ready_payload()
    payload["providers"] = {}
    _write_evaluation(evaluation, payload)

    result = checker.check_kpi_readiness(evaluation_path=evaluation)

    assert result.ok is False
    assert [(finding.code, finding.detail) for finding in result.findings] == [
        ("provider_missing", "provider=paddleocr_local")
    ]


def test_check_kpi_readiness_rejects_non_finite_metric(tmp_path: Path) -> None:
    """Verify non-finite metric values cannot bypass the rate threshold."""
    evaluation = tmp_path / "evaluation.json"
    payload = _ready_payload()
    payload["providers"] = {
        "paddleocr_local": {
            "errors": 0,
            "scoreable_ingredient_name_exact_rate": float("nan"),
        }
    }
    _write_evaluation(evaluation, payload)

    result = checker.check_kpi_readiness(evaluation_path=evaluation)

    assert result.ok is False
    assert [(finding.code, finding.detail) for finding in result.findings] == [
        (
            "metric_missing",
            "provider=paddleocr_local metric=scoreable_ingredient_name_exact_rate",
        )
    ]


def test_main_prints_bounded_failures(tmp_path: Path, capsys) -> None:
    """Verify CLI output contains bounded counts and no artifact contents."""
    evaluation = tmp_path / "evaluation.json"
    payload = _ready_payload()
    payload["provisional_fixture_count"] = 1
    _write_evaluation(evaluation, payload)

    exit_code = checker.main(["--evaluation", str(evaluation)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "provisional_fixture_count_exceeded value=1 max=0" in captured.err
    assert "raw_ocr_text" not in captured.err
    assert str(evaluation) not in captured.err


def test_main_allows_explicit_research_thresholds(tmp_path: Path, capsys) -> None:
    """Verify callers can lower thresholds for provisional research baselines."""
    evaluation = tmp_path / "evaluation.json"
    payload = _ready_payload()
    payload["scoreable_fixture_count"] = 4
    payload["provisional_fixture_count"] = 16
    payload["expected_quality_warnings"] = [{"code": "provisional_expected_fixture"}] * 16
    payload["providers"] = {
        "paddleocr_local": {
            "errors": 2,
            "scoreable_ingredient_name_exact_rate": 1.0,
        }
    }
    _write_evaluation(evaluation, payload)

    exit_code = checker.main(
        [
            "--evaluation",
            str(evaluation),
            "--min-scoreable-fixtures",
            "4",
            "--max-provisional-fixtures",
            "16",
            "--max-expected-quality-warnings",
            "16",
            "--max-provider-errors",
            "2",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "ocr_kpi_ready provider=paddleocr_local" in captured.out
