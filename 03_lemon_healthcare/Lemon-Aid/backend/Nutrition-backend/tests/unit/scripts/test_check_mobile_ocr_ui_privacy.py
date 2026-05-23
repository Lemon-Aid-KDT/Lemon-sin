"""Tests for mobile OCR UI privacy source checks."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_privacy_module() -> ModuleType:
    """Load the repo-level mobile OCR UI privacy script under test."""
    module_path = Path(__file__).resolve().parents[4] / "scripts/check_mobile_ocr_ui_privacy.py"
    spec = importlib.util.spec_from_file_location("check_mobile_ocr_ui_privacy", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"missing module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_mobile_ocr_ui_privacy"] = module
    spec.loader.exec_module(module)
    return module


privacy = _load_privacy_module()


def test_scan_allows_redacted_storage_flag_names(tmp_path: Path) -> None:
    """Verify redacted OCR storage flags are allowed in runtime models."""
    _write_source(
        tmp_path,
        "mobile/lib/features/supplements/supplement_models.dart",
        "\n".join(
            [
                "final rawOcrTextStored = json['raw_ocr_text_stored'] == true;",
                "final rawProviderPayloadStored = json['raw_provider_payload_stored'] == true;",
            ]
        ),
    )

    assert privacy.scan_mobile_runtime_source(tmp_path) == []


def test_scan_allows_auth_transport_and_error_redaction_plumbing(tmp_path: Path) -> None:
    """Verify non-OCR auth plumbing and error redaction markers are not false positives."""
    _write_source(
        tmp_path,
        "mobile/lib/core/api/api_client.dart",
        "headers['Authorization'] = 'Bearer ${_bearerToken.trim()}';\n",
    )
    _write_source(
        tmp_path,
        "mobile/lib/core/api/api_error.dart",
        "\n".join(
            [
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
            ]
        ),
    )

    assert privacy.scan_mobile_runtime_source(tmp_path) == []


def test_scan_rejects_raw_ocr_text_key(tmp_path: Path) -> None:
    """Verify raw OCR text keys are blocked in product runtime code."""
    _write_source(
        tmp_path,
        "mobile/lib/features/supplements/bad.dart",
        "final payload = {'raw_ocr_text': value};\n",
    )

    findings = privacy.scan_mobile_runtime_source(tmp_path)

    assert [(finding.code, finding.detail) for finding in findings] == [
        ("raw_ocr_text_key", "runtime_source_marker")
    ]


def test_scan_rejects_manual_ocr_parse_surface(tmp_path: Path) -> None:
    """Verify the mobile manual OCR parse surface cannot return silently."""
    _write_source(
        tmp_path,
        "mobile/lib/app_controller.dart",
        "\n".join(
            [
                "Future<void> parseOcrText(String value) async {}",
                "final request = SupplementOCRTextParseRequest(ocrText: value);",
                "const endpoint = '/supplements/analyses/id/ocr-text';",
            ]
        ),
    )

    findings = privacy.scan_mobile_runtime_source(tmp_path)

    assert [finding.code for finding in findings] == [
        "parse_ocr_text_method",
        "ocr_text_parse_request",
        "ocr_text_endpoint",
    ]


def test_scan_rejects_visible_ocr_text_label(tmp_path: Path) -> None:
    """Verify visible raw OCR text review labels are blocked."""
    _write_source(
        tmp_path,
        "mobile/lib/features/supplements/supplement_flow_screen.dart",
        "const Text('OCR text review');\n",
    )

    findings = privacy.scan_mobile_runtime_source(tmp_path)

    assert [(finding.code, finding.detail) for finding in findings] == [
        ("raw_ocr_ui_label", "runtime_source_marker")
    ]


def test_scan_ignores_tests_outside_runtime_source(tmp_path: Path) -> None:
    """Verify tests may keep negative raw marker assertions."""
    _write_source(
        tmp_path,
        "mobile/test/unit/app_controller_error_privacy_test.dart",
        "expect(error.toString(), isNot(contains('raw_ocr_text')));\n",
    )

    assert privacy.scan_mobile_runtime_source(tmp_path) == []


def test_main_reports_bounded_findings(tmp_path: Path, capsys) -> None:
    """Verify CLI findings do not echo matched source text."""
    _write_source(
        tmp_path,
        "mobile/lib/features/supplements/bad.dart",
        "const Text('Parse OCR text');\n",
    )

    exit_code = privacy.main(["--project-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "raw_ocr_ui_label runtime_source_marker" in captured.err
    assert "Parse OCR text" not in captured.err


def test_main_reports_success(tmp_path: Path, capsys) -> None:
    """Verify CLI success output includes the scanned file count."""
    _write_source(
        tmp_path,
        "mobile/lib/features/supplements/ok.dart",
        "const title = 'Supplement preview';\n",
    )

    exit_code = privacy.main(["--project-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "mobile_ocr_ui_privacy_ok files=1" in captured.out


def _write_source(project_root: Path, relative_path: str, content: str) -> Path:
    """Write a test source file under a temporary project root."""
    path = project_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
