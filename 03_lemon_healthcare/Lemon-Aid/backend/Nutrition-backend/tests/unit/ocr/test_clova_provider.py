"""CLOVA OCR fallback provider tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from pydantic import SecretStr
from src.config import Settings
from src.ocr.base import OCRError, OCRImageInput
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

    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.url: str | None = None
        self.request_json: Mapping[str, Any] | None = None
        self.headers: Mapping[str, str] | None = None

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
        _ = timeout
        self.url = url
        self.request_json = json
        self.headers = headers
        return _FakeResponse(self.payload, self.status_code)


def _settings(
    *,
    allow_external_ocr: bool = True,
    enable_clova_ocr: bool = False,
) -> Settings:
    """Return CLOVA provider settings.

    Args:
        allow_external_ocr: Whether external OCR is allowed.
        enable_clova_ocr: Whether fallback auto-run is enabled.

    Returns:
        Settings object.
    """
    return Settings(
        _env_file=None,
        enable_clova_ocr=enable_clova_ocr,
        allow_external_ocr=allow_external_ocr,
        clova_ocr_api_url="https://example.apigw.ntruss.com/custom/v1/infer",
        clova_ocr_secret=SecretStr("test-secret"),
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
async def test_clova_adapter_flattens_fields() -> None:
    """Verify CLOVA fields are joined into one OCR result."""
    client = _FakeHTTPClient(
        {
            "images": [
                {
                    "inferResult": "SUCCESS",
                    "fields": [
                        {"inferText": "비타민 D 1000", "inferConfidence": 0.91},
                        {"inferText": "비타민 D 25 ug", "inferConfidence": 0.87},
                    ],
                }
            ]
        }
    )
    adapter = ClovaOCRAdapter(_settings(), client=client)

    result = await adapter.extract_text(_image_input())

    assert result.provider == CLOVA_OCR_PROVIDER
    assert result.text == "비타민 D 1000\n비타민 D 25 ug"
    assert result.confidence == pytest.approx(0.89)
    assert client.url == "https://example.apigw.ntruss.com/custom/v1/infer"
    assert client.headers is not None
    assert client.headers["X-OCR-SECRET"] == "test-secret"
    assert client.request_json is not None
    assert client.request_json["version"] == "V2"


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
