"""Google Vision OCR provider tests."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest
from src.ocr.base import OCRError, OCRImageInput
from src.ocr.google_vision import GoogleVisionOCR
from src.ocr.providers.google_vision import (
    GOOGLE_VISION_PROVIDER,
    GoogleVisionOCRAdapter,
    build_google_vision_endpoint,
)
from src.ocr.providers.google_vision_auth import GoogleVisionApiKeyAuthHeaders


def test_google_vision_compatibility_alias_points_to_adapter() -> None:
    """Verify the handoff import path stays compatible with the provider package."""
    assert GoogleVisionOCR is GoogleVisionOCRAdapter


def _image_input() -> OCRImageInput:
    """Return a tiny validated image input.

    Returns:
        OCR image input fixture.
    """
    return OCRImageInput(
        image_bytes=b"fake-image-bytes",
        mime_type="image/png",
        width=3,
        height=2,
    )


@pytest.mark.asyncio
async def test_google_vision_provider_posts_document_text_request_with_api_key_header() -> None:
    """Verify request shape and header handling for Google Vision OCR."""
    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        """Capture the outgoing request and return a fake Google response."""
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "responses": [
                    {
                        "fullTextAnnotation": {
                            "text": "비타민 D 1000\nVitamin D 25 ug",
                            "pages": [
                                {
                                    "width": 300,
                                    "height": 200,
                                    "confidence": 0.87,
                                    "blocks": [
                                        {
                                            "blockType": "TEXT",
                                            "confidence": 0.88,
                                            "boundingBox": {
                                                "vertices": [
                                                    {"x": 1, "y": 2},
                                                    {"x": 100, "y": 2},
                                                    {"x": 100, "y": 30},
                                                    {"x": 1, "y": 30},
                                                ]
                                            },
                                            "paragraphs": [
                                                {
                                                    "confidence": 0.89,
                                                    "words": [
                                                        {
                                                            "confidence": 0.91,
                                                            "boundingBox": {
                                                                "vertices": [
                                                                    {"x": 1, "y": 2},
                                                                    {"x": 30, "y": 2},
                                                                    {"x": 30, "y": 20},
                                                                    {"x": 1, "y": 20},
                                                                ]
                                                            },
                                                            "symbols": [
                                                                {"text": "비"},
                                                                {"text": "타"},
                                                                {"text": "민"},
                                                            ],
                                                        },
                                                        {
                                                            "confidence": 0.93,
                                                            "symbols": [
                                                                {"text": "D"},
                                                            ],
                                                        },
                                                    ],
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GoogleVisionOCRAdapter(
            auth_headers=GoogleVisionApiKeyAuthHeaders("secret-key"),
            language_hints=("ko", "en"),
            max_retries=0,
            client=client,
        )
        result = await adapter.extract_text(_image_input())

    assert result.provider == GOOGLE_VISION_PROVIDER
    assert result.text == "비타민 D 1000\nVitamin D 25 ug"
    assert result.confidence == pytest.approx(0.92)
    assert len(result.pages) == 1
    page = result.pages[0]
    assert page.width == 300
    assert page.height == 200
    assert page.confidence == pytest.approx(0.87)
    block = page.blocks[0]
    assert block.block_type == "TEXT"
    assert block.text == "비타민 D"
    assert block.bounding_box is not None
    assert block.bounding_box.vertices[0].x == 1
    paragraph = block.paragraphs[0]
    assert paragraph.text == "비타민 D"
    assert paragraph.words[0].text == "비타민"
    assert paragraph.words[0].confidence == pytest.approx(0.91)
    assert paragraph.words[0].block_index == 0
    assert paragraph.words[0].paragraph_index == 0
    assert paragraph.words[0].word_index == 0
    assert paragraph.words[0].bounding_box is not None
    assert paragraph.words[0].bounding_box.vertices[2].y == 20
    assert "key=" not in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == "secret-key"
    request_body = captured["body"]["requests"][0]
    assert request_body["features"] == [{"type": "DOCUMENT_TEXT_DETECTION"}]
    assert request_body["image"]["content"] == base64.b64encode(b"fake-image-bytes").decode("ascii")
    assert request_body["imageContext"] == {"languageHints": ["ko", "en"]}


@pytest.mark.asyncio
async def test_google_vision_provider_falls_back_to_text_annotations() -> None:
    """Verify textAnnotations fallback when fullTextAnnotation is absent."""

    async def handler(_request: httpx.Request) -> httpx.Response:
        """Return a fake textAnnotations-only response."""
        return httpx.Response(
            200,
            json={"responses": [{"textAnnotations": [{"description": "fallback text"}]}]},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GoogleVisionOCRAdapter(
            auth_headers=GoogleVisionApiKeyAuthHeaders("secret-key"),
            max_retries=0,
            client=client,
        )
        result = await adapter.extract_text(_image_input())

    assert result.text == "fallback text"
    assert result.confidence is None
    assert result.pages == ()


@pytest.mark.asyncio
async def test_google_vision_provider_returns_empty_text_without_fake_confidence() -> None:
    """Verify empty OCR responses do not invent confidence scores."""

    async def handler(_request: httpx.Request) -> httpx.Response:
        """Return an empty but successful Google response."""
        return httpx.Response(200, json={"responses": [{}]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GoogleVisionOCRAdapter(
            auth_headers=GoogleVisionApiKeyAuthHeaders("secret-key"),
            max_retries=0,
            client=client,
        )
        result = await adapter.extract_text(_image_input())

    assert result.text == ""
    assert result.confidence is None


@pytest.mark.asyncio
async def test_google_vision_provider_sanitizes_provider_errors() -> None:
    """Verify provider error details do not expose raw request content."""

    async def handler(_request: httpx.Request) -> httpx.Response:
        """Return a fake provider error response."""
        return httpx.Response(
            200,
            json={"responses": [{"error": {"status": "PERMISSION_DENIED", "message": "secret"}}]},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GoogleVisionOCRAdapter(
            auth_headers=GoogleVisionApiKeyAuthHeaders("secret-key"),
            max_retries=0,
            client=client,
        )
        with pytest.raises(OCRError, match="PERMISSION_DENIED") as exc_info:
            await adapter.extract_text(_image_input())

    assert "secret-key" not in str(exc_info.value)
    assert "fake-image-bytes" not in str(exc_info.value)


def test_build_google_vision_endpoint_uses_global_and_regional_urls() -> None:
    """Verify endpoint selection follows Google Vision REST locations."""
    assert build_google_vision_endpoint(project_id=None, location="global") == (
        "https://vision.googleapis.com/v1/images:annotate"
    )
    assert build_google_vision_endpoint(project_id="lemon-prod", location="eu") == (
        "https://eu-vision.googleapis.com/v1/projects/lemon-prod/locations/eu/images:annotate"
    )


def test_build_google_vision_endpoint_requires_project_for_regional_url() -> None:
    """Verify regional Google Vision endpoints fail closed without project id."""
    with pytest.raises(ValueError, match="GOOGLE_CLOUD_PROJECT"):
        build_google_vision_endpoint(project_id=None, location="us")
