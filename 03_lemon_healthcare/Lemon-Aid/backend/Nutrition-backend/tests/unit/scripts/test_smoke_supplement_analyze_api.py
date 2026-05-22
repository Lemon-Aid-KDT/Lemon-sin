"""Tests for the supplement analyze API smoke helper."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from scripts import smoke_supplement_analyze_api as smoke


def test_assert_no_forbidden_raw_fields_rejects_nested_ocr_text() -> None:
    """Verify raw OCR text cannot pass through smoke summaries."""
    with pytest.raises(SystemExit, match=r"provider_observations.*raw_ocr_text"):
        smoke.assert_no_forbidden_raw_fields(
            {
                "provider_observations": [
                    {
                        "provider": "paddleocr_local",
                        "raw_ocr_text": "visible label text must not be returned",
                    }
                ]
            }
        )


def test_summarize_preview_counts_safe_provider_observations() -> None:
    """Verify a successful preview is reduced to bounded routing metadata."""
    summary = smoke.summarize_preview(
        {
            "analysis_id": "00000000-0000-0000-0000-000000000001",
            "status": "requires_confirmation",
            "ingredient_candidates": [{"display_name": "비타민 C"}],
            "provider_observations": [
                {
                    "provider": "paddleocr_local",
                    "stage": "primary",
                    "status": "completed",
                    "text_non_empty": True,
                    "raw_ocr_text_stored": False,
                    "raw_provider_payload_stored": False,
                }
            ],
            "warnings": ["review required"],
            "action_required": "review_required",
            "image_quality_report": {"status": "needs_review"},
        },
        status_code=202,
    )

    assert summary == {
        "status_code": 202,
        "api_status": "requires_confirmation",
        "analysis_id_present": True,
        "ingredient_candidate_count": 1,
        "provider_observation_count": 1,
        "providers": ["paddleocr_local"],
        "stages": ["primary"],
        "provider_statuses": ["completed"],
        "text_non_empty_observations": 1,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "warning_count": 1,
        "action_required": "review_required",
        "image_quality_status": "needs_review",
        "raw_forbidden": False,
    }


def test_build_smoke_request_rejects_non_loopback_without_opt_in(tmp_path: Path) -> None:
    """Verify local smoke cannot accidentally send images to a remote API."""
    image_path = tmp_path / "label.jpg"
    image_path.write_bytes(b"fake")
    args = _args(
        base_url="https://api.example.com/api/v1",
        image=image_path,
        provider="paddleocr",
    )

    with pytest.raises(SystemExit, match="Non-loopback"):
        smoke.build_smoke_request(args)


def test_build_smoke_request_rejects_external_provider_without_opt_in(tmp_path: Path) -> None:
    """Verify external OCR selectors require an explicit operator flag."""
    image_path = tmp_path / "label.jpg"
    image_path.write_bytes(b"fake")
    args = _args(
        base_url="http://127.0.0.1:8000/api/v1",
        image=image_path,
        provider="clova",
    )

    with pytest.raises(SystemExit, match="External OCR"):
        smoke.build_smoke_request(args)


def test_build_smoke_request_accepts_loopback_paddle(tmp_path: Path) -> None:
    """Verify the default local PaddleOCR smoke request is accepted."""
    image_path = tmp_path / "label.jpg"
    image_path.write_bytes(b"fake")

    request = smoke.build_smoke_request(
        _args(
            base_url="http://127.0.0.1:8000/api/v1/",
            image=image_path,
            provider="paddleocr",
        )
    )

    assert request.base_url == "http://127.0.0.1:8000/api/v1"
    assert request.image_path == image_path.resolve()
    assert request.provider == "paddleocr"
    assert request.bearer_token is None


def _args(
    *,
    base_url: str,
    image: Path,
    provider: str,
    allow_external_provider: bool = False,
    allow_non_loopback: bool = False,
) -> argparse.Namespace:
    """Build parsed-argument stand-ins for smoke helper tests."""
    return argparse.Namespace(
        base_url=base_url,
        image=image,
        provider=provider,
        client_request_id="test-request",
        token_env="LEMON_API_TOKEN_TEST_ONLY",
        timeout=1.0,
        output_summary=None,
        dry_run=False,
        allow_external_provider=allow_external_provider,
        allow_non_loopback=allow_non_loopback,
    )
