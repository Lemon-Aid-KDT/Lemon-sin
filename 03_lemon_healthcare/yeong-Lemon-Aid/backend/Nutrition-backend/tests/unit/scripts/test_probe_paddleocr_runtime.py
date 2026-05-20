"""Tests for the explicit PaddleOCR runtime probe."""

from __future__ import annotations

from src.ocr.base import OCRResult

from scripts.probe_paddleocr_runtime import _failure_summary, _success_summary


def test_probe_success_summary_redacts_ocr_text() -> None:
    """Verify the runtime probe reports counts without raw OCR text."""
    summary = _success_summary(
        OCRResult(
            text="Vitamin D 25 ug\nZinc 10 mg",
            provider="paddleocr_local",
            confidence=0.91,
        )
    )

    assert summary["ok"] is True
    assert summary["text_present"] is True
    assert summary["text_line_count"] == 2
    assert "Vitamin D" not in str(summary)
    assert summary["raw_ocr_text_stored"] is False


def test_probe_failure_summary_reports_import_error_without_raw_artifacts() -> None:
    """Verify import/runtime failures are emitted as redacted JSON fields."""
    summary = _failure_summary(
        stage="import",
        exc=ModuleNotFoundError("No module named 'langchain.docstore'"),
    )

    assert summary["ok"] is False
    assert summary["stage"] == "import"
    assert summary["error_type"] == "ModuleNotFoundError"
    assert "langchain.docstore" in str(summary["message"])
    assert summary["raw_image_stored"] is False
    assert summary["raw_provider_payload_stored"] is False
