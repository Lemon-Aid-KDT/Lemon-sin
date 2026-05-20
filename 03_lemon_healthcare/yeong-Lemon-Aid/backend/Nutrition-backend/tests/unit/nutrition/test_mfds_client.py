"""MFDS OpenAPI client contract tests."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from pydantic import SecretStr
from src.config import Settings
from src.nutrition.mfds_client import (
    MFDS_C003_SERVICE_ID,
    MFDS_PROVIDER,
    MfdsClientError,
    MfdsOpenAPIClient,
)


def _settings(**overrides: Any) -> Settings:
    """Return test settings for MFDS OpenAPI.

    Args:
        overrides: Settings overrides.

    Returns:
        Runtime settings.
    """
    values: dict[str, Any] = {
        "_env_file": None,
        "enable_barcode_lookup": True,
        "mfds_api_key": SecretStr("test-mfds-key"),
        "mfds_openapi_base_url": "http://openapi.foodsafetykorea.go.kr/api",
        "mfds_openapi_max_retries": 0,
        "mfds_openapi_page_size": 100,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.asyncio
async def test_mfds_lookup_returns_not_configured_without_enabled_key() -> None:
    """Verify missing MFDS configuration fails closed without provider calls."""
    client = MfdsOpenAPIClient(Settings(_env_file=None))

    result = await client.get_product_by_report_no("20070017035202")

    assert result.provider == MFDS_PROVIDER
    assert result.service_id == MFDS_C003_SERVICE_ID
    assert result.status == "not_configured"
    assert result.products == ()


@pytest.mark.asyncio
async def test_mfds_get_product_by_report_no_builds_c003_query_and_parses_rows() -> None:
    """Verify C003 PRDLST_REPORT_NO path shape and allowlisted parsing."""
    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        """Capture request and return an MFDS C003-like response."""
        captured["url"] = str(request.url)
        captured["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "C003": {
                    "total_count": "1",
                    "row": [
                        {
                            "PRDLST_REPORT_NO": "20070017035202",
                            "PRDLST_NM": "공식 건강기능식품",
                            "BSSH_NM": "공식 업소",
                            "LCNS_NO": "1234567890",
                            "NTK_MTHD": "1일 1회",
                            "PRIMARY_FNCLTY": "영양 보충",
                            "IFTKN_ATNT_MATR_CN": "주의 문구",
                            "RAWMTRL_NM": "비타민 C",
                            "UNREVIEWED_RAW_FIELD": "must-not-be-copied",
                        }
                    ],
                    "RESULT": {"MSG": "정상처리되었습니다.", "CODE": "INFO-000"},
                }
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        result = await MfdsOpenAPIClient(
            _settings(),
            client=http_client,
        ).get_product_by_report_no("20070017035202")

    assert captured["url"].startswith(
        "http://openapi.foodsafetykorea.go.kr/api/test-mfds-key/C003/json/1/100/"
        "PRDLST_REPORT_NO=20070017035202"
    )
    assert captured["params"] == {}
    assert result.status == "matched"
    assert result.total_count == 1
    assert result.message_code == "INFO-000"
    product = result.products[0]
    assert product.product_name == "공식 건강기능식품"
    assert product.business_name == "공식 업소"
    assert product.report_no == "20070017035202"
    assert product.source_fields == {
        "product_name": "공식 건강기능식품",
        "business_name": "공식 업소",
        "report_no": "20070017035202",
        "license_no": "1234567890",
        "intake_method": "1일 1회",
        "primary_functionality": "영양 보충",
        "attention": "주의 문구",
        "raw_material_name": "비타민 C",
    }


@pytest.mark.asyncio
async def test_mfds_no_data_code_maps_to_not_found() -> None:
    """Verify MFDS INFO-200 maps to a not_found result."""

    async def handler(_request: httpx.Request) -> httpx.Response:
        """Return an MFDS no-data response."""
        return httpx.Response(
            200,
            json={"C003": {"RESULT": {"MSG": "해당하는 데이터가 없습니다.", "CODE": "INFO-200"}}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        result = await MfdsOpenAPIClient(
            _settings(),
            client=http_client,
        ).get_product_by_report_no("00000000000000")

    assert result.status == "not_found"
    assert result.message_code == "INFO-200"


@pytest.mark.asyncio
async def test_mfds_html_provider_error_maps_to_typed_result() -> None:
    """Verify MFDS HTML/script provider errors are normalized without raw HTML."""

    async def handler(_request: httpx.Request) -> httpx.Response:
        """Return an MFDS script error body."""
        return httpx.Response(
            200,
            text="<script>alert('인증키가 유효하지 않습니다.'); history.back();</script>",
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        result = await MfdsOpenAPIClient(
            _settings(),
            client=http_client,
        ).get_product_by_report_no("20070017035202")

    assert result.status == "provider_error"
    assert result.message_code == "INFO-100"
    assert result.message == "MFDS rejected the key for this service."


@pytest.mark.asyncio
async def test_mfds_html_authorization_error_maps_to_info_400() -> None:
    """Verify MFDS authorization HTML is classified without storing raw HTML."""

    async def handler(_request: httpx.Request) -> httpx.Response:
        """Return a provider authorization error body."""
        return httpx.Response(
            200,
            text="<html><body>권한이 없습니다. 관리자에게 문의하십시오.</body></html>",
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        result = await MfdsOpenAPIClient(
            _settings(),
            client=http_client,
        ).get_product_by_report_no("20070017035202")

    assert result.status == "provider_error"
    assert result.message_code == "INFO-400"
    assert result.message == "MFDS key is not authorized for this service."


@pytest.mark.asyncio
async def test_mfds_fetch_sample_service_rows_uses_documented_sample_key() -> None:
    """Verify public sample diagnostics do not require a configured private key."""
    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        """Capture request and return an MFDS sample response."""
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "C003": {
                    "total_count": "1",
                    "row": [
                        {
                            "PRDLST_REPORT_NO": "20070017035215",
                            "PRDLST_NM": "유한m 오메가-3 비거파워",
                        }
                    ],
                    "RESULT": {"MSG": "정상처리되었습니다.", "CODE": "INFO-000"},
                }
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        result = await MfdsOpenAPIClient(
            _settings(enable_barcode_lookup=False, mfds_api_key=None),
            client=http_client,
        ).fetch_sample_service_rows(service_id=MFDS_C003_SERVICE_ID, start_idx=1, end_idx=5)

    assert captured["url"] == "http://openapi.foodsafetykorea.go.kr/api/sample/C003/json/1/5"
    assert result.status == "matched"
    assert result.message_code == "INFO-000"


@pytest.mark.asyncio
async def test_mfds_search_products_rejects_empty_query() -> None:
    """Verify C003 fuzzy search cannot run with an empty query."""
    result = await MfdsOpenAPIClient(_settings()).search_products()

    assert result.status == "invalid_request"


@pytest.mark.asyncio
async def test_mfds_lookup_sanitizes_http_errors() -> None:
    """Verify MFDS HTTP failures do not expose provider credentials."""

    async def handler(_request: httpx.Request) -> httpx.Response:
        """Return a provider HTTP failure."""
        return httpx.Response(500, json={"secret": "test-mfds-key"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        with pytest.raises(MfdsClientError) as exc_info:
            await MfdsOpenAPIClient(_settings(), client=http_client).get_product_by_report_no(
                "20070017035202"
            )

    assert "test-mfds-key" not in str(exc_info.value)
