"""CLOVA OCR fallback provider tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from pydantic import SecretStr
from src.config import Settings
from src.ocr.base import OCRError, OCRImageInput
from src.ocr.clova import ClovaOCR
from src.ocr.providers.clova import CLOVA_OCR_PROVIDER, ClovaOCRAdapter


class _FakeResponse:
    """Fake HTTP response for CLOVA tests."""

    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def json(self) -> Any:
        """Return fake JSON payload.

        Returns:
            Fake payload.
        """
        return self.payload


class _FakeHTTPClient:
    """Fake async HTTP client capturing CLOVA requests."""

    def __init__(
        self,
        payload: Any,
        status_code: int = 200,
        *,
        responses: list[_FakeResponse] | None = None,
    ) -> None:
        self.responses = responses or [_FakeResponse(payload, status_code)]
        self.url: str | None = None
        self.request_json: Mapping[str, Any] | None = None
        self.headers: Mapping[str, str] | None = None
        self.timeouts: list[float | None] = []
        self.call_count = 0

    async def post(
        self,
        url: str,
        *,
        json: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: float | None = None,
    ) -> _FakeResponse:
        """Capture a POST request and return a fake response.

        Args:
            url: Request URL.
            json: Request JSON.
            headers: Request headers.
            timeout: Request timeout.

        Returns:
            Fake response.
        """
        self.url = url
        self.request_json = json
        self.headers = headers
        self.timeouts.append(timeout)
        response_index = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1
        return self.responses[response_index]


def _settings(
    *,
    allow_external_ocr: bool = True,
    timeout_seconds: int = 15,
    max_retries: int = 1,
) -> Settings:
    """Return CLOVA provider settings.

    Args:
        allow_external_ocr: Whether external OCR is allowed.
        timeout_seconds: CLOVA request timeout.
        max_retries: CLOVA retry count for transient failures.

    Returns:
        Settings object.
    """
    return Settings(
        _env_file=None,
        enable_clova_ocr=True,
        allow_external_ocr=allow_external_ocr,
        clova_ocr_api_url="https://example.apigw.ntruss.com/custom/v1/infer",
        clova_ocr_secret=SecretStr("test-secret"),
        clova_ocr_timeout_seconds=timeout_seconds,
        clova_ocr_max_retries=max_retries,
    )


def _image_input() -> OCRImageInput:
    """Return a minimal OCR image input.

    Returns:
        OCR image input.
    """
    return OCRImageInput(
        image_bytes=b"fake-png-bytes",
        mime_type="image/png",
        width=10,
        height=8,
    )


@pytest.mark.asyncio
async def test_clova_adapter_normalizes_fields_into_layout() -> None:
    """Verify CLOVA fields are normalized into the shared OCR layout contract."""
    client = _FakeHTTPClient(
        {
            "images": [
                {
                    "inferResult": "SUCCESS",
                    "convertedImageInfo": {"width": 1200, "height": 800},
                    "fields": [
                        {
                            "inferText": "비타민",
                            "inferConfidence": 0.91,
                            "lineBreak": False,
                            "boundingPoly": {
                                "vertices": [
                                    {"x": 1, "y": 2},
                                    {"x": 10, "y": 2},
                                    {"x": 10, "y": 8},
                                    {"x": 1, "y": 8},
                                ]
                            },
                        },
                        {
                            "inferText": "D 1000",
                            "inferConfidence": 0.87,
                            "lineBreak": True,
                        },
                        {"inferText": "비타민 D 25 ug", "inferConfidence": 0.80},
                    ],
                }
            ]
        }
    )
    adapter = ClovaOCRAdapter(_settings(), client=client)

    result = await adapter.extract_text(_image_input())

    assert result.provider == CLOVA_OCR_PROVIDER
    assert result.text == "비타민 D 1000\n비타민 D 25 ug"
    assert result.confidence == pytest.approx(0.86)
    assert len(result.pages) == 1
    page = result.pages[0]
    assert (page.width, page.height) == (1200, 800)
    assert len(page.blocks) == 1
    assert page.blocks[0].block_type == "TEXT"
    assert page.blocks[0].paragraphs[0].text == "비타민 D 1000\n비타민 D 25 ug"
    first_word = page.blocks[0].paragraphs[0].words[0]
    assert first_word.text == "비타민"
    assert first_word.bounding_box is not None
    assert first_word.bounding_box.vertices[0].x == 1
    assert client.url == "https://example.apigw.ntruss.com/custom/v1/infer"
    assert client.headers is not None
    assert client.headers["X-OCR-SECRET"] == "test-secret"
    assert client.request_json is not None
    assert client.request_json["version"] == "V2"
    assert client.timeouts == [15.0]


def test_clova_adapter_exposes_handoff_alias() -> None:
    """Verify the handoff import path points at the provider implementation."""
    assert ClovaOCR is ClovaOCRAdapter


@pytest.mark.asyncio
async def test_clova_adapter_normalizes_tables_as_separate_blocks() -> None:
    """Verify CLOVA table cells are preserved as a table block for layout parsing."""
    client = _FakeHTTPClient(
        {
            "images": [
                {
                    "inferResult": "SUCCESS",
                    "fields": [{"inferText": "원료명", "inferConfidence": 0.90}],
                    "tables": [
                        {
                            "cells": [
                                {
                                    "cellTextLines": [
                                        {
                                            "cellWords": [
                                                {
                                                    "inferText": "비타민D",
                                                    "inferConfidence": 0.82,
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {"inferText": "25 ug", "inferConfidence": 0.88},
                            ]
                        }
                    ],
                }
            ]
        }
    )
    adapter = ClovaOCRAdapter(_settings(), client=client)

    result = await adapter.extract_text(_image_input())

    assert result.text == "원료명\n비타민D 25 ug"
    assert result.confidence == pytest.approx(0.875)
    assert len(result.pages) == 1
    text_block, table_block = result.pages[0].blocks
    assert text_block.block_type == "TEXT"
    assert table_block.block_type == "TABLE"
    assert table_block.paragraphs[0].words[0].text == "비타민D"
    assert table_block.paragraphs[0].words[1].text == "25 ug"


@pytest.mark.asyncio
async def test_clova_adapter_returns_empty_result_for_empty_success() -> None:
    """Verify a successful but empty CLOVA response degrades as empty OCR text."""
    adapter = ClovaOCRAdapter(
        _settings(),
        client=_FakeHTTPClient({"images": [{"inferResult": "SUCCESS", "fields": []}]}),
    )

    result = await adapter.extract_text(_image_input())

    assert result.provider == CLOVA_OCR_PROVIDER
    assert result.text == ""
    assert result.confidence is None
    assert result.pages == ()


@pytest.mark.asyncio
async def test_clova_adapter_requires_external_ocr_gate() -> None:
    """Verify CLOVA cannot send image bytes without the external OCR gate."""
    adapter = ClovaOCRAdapter(
        _settings(allow_external_ocr=False),
        client=_FakeHTTPClient({"images": []}),
    )

    with pytest.raises(OCRError, match="ALLOW_EXTERNAL_OCR"):
        await adapter.extract_text(_image_input())


@pytest.mark.asyncio
async def test_clova_adapter_rejects_provider_error() -> None:
    """Verify unsuccessful CLOVA inference is not accepted."""
    adapter = ClovaOCRAdapter(
        _settings(),
        client=_FakeHTTPClient({"images": [{"inferResult": "ERROR", "fields": []}]}),
    )

    with pytest.raises(OCRError, match="inference failed"):
        await adapter.extract_text(_image_input())


@pytest.mark.asyncio
async def test_clova_adapter_retries_transient_http_status() -> None:
    """Verify transient CLOVA HTTP failures are retried with the CLOVA retry setting."""
    client = _FakeHTTPClient(
        {},
        responses=[
            _FakeResponse({"code": "0501", "message": "OCR service error."}, status_code=503),
            _FakeResponse(
                {
                    "images": [
                        {
                            "inferResult": "SUCCESS",
                            "fields": [
                                {
                                    "inferText": "비타민 D 1000",
                                    "inferConfidence": 0.91,
                                }
                            ],
                        }
                    ]
                }
            ),
        ],
    )
    adapter = ClovaOCRAdapter(
        _settings(timeout_seconds=7, max_retries=1),
        client=client,
    )

    result = await adapter.extract_text(_image_input())

    assert result.text == "비타민 D 1000"
    assert client.call_count == 2
    assert client.timeouts == [7.0, 7.0]


@pytest.mark.asyncio
async def test_clova_adapter_sanitizes_http_errors() -> None:
    """Verify HTTP errors expose status/code without leaking request body or secret."""
    adapter = ClovaOCRAdapter(
        _settings(max_retries=0),
        client=_FakeHTTPClient(
            {"code": "0002", "message": "Secret key validate failed."},
            status_code=401,
        ),
    )

    with pytest.raises(OCRError) as exc_info:
        await adapter.extract_text(_image_input())

    error_message = str(exc_info.value)
    assert "status 401" in error_message
    assert "code=0002" in error_message
    assert "test-secret" not in error_message
    assert "fake-png-bytes" not in error_message
