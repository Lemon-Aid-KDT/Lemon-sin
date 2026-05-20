"""FoodQR client contract tests."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from pydantic import SecretStr
from src.config import Settings
from src.nutrition.foodqr_client import FOODQR_PROVIDER, FoodQrClient, FoodQrClientError


def _settings(**overrides: Any) -> Settings:
    """Return test settings for FoodQR.

    Args:
        overrides: Settings overrides.

    Returns:
        Runtime settings.
    """
    values: dict[str, Any] = {
        "_env_file": None,
        "enable_barcode_lookup": True,
        "foodqr_service_key": SecretStr("test-foodqr-key"),
        "foodqr_base_url": "https://apis.data.go.kr/1471000/FoodQrInfoService01",
        "foodqr_product_list_path": "/getFoodQrProdList01",
        "foodqr_max_retries": 0,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.asyncio
async def test_foodqr_lookup_returns_not_configured_without_enabled_key() -> None:
    """Verify missing FoodQR configuration fails closed without provider calls."""
    client = FoodQrClient(Settings(_env_file=None))

    result = await client.lookup_by_barcode("8801234567890")

    assert result.provider == FOODQR_PROVIDER
    assert result.status == "not_configured"
    assert result.products == ()


@pytest.mark.asyncio
async def test_foodqr_lookup_posts_expected_query_and_parses_items() -> None:
    """Verify FoodQR brcd_no query shape and allowlisted response parsing."""
    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        """Capture request and return a FoodQR-like public-data response."""
        captured["url"] = str(request.url)
        captured["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "response": {
                    "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
                    "body": {
                        "items": {
                            "item": [
                                {
                                    "PRDT_NM": "공식 제품",
                                    "BRCD_NO": "8801234567890",
                                    "BSSH_NM": "공식 제조사",
                                    "PRDLST_REPORT_NO": "20070017035202",
                                    "VER_INFO": "1",
                                    "VLD_BGNG_YMD": "20240101",
                                    "VLD_END_YMD": "99991231",
                                    "UNREVIEWED_RAW_FIELD": "must-not-be-copied",
                                }
                            ]
                        }
                    },
                }
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        result = await FoodQrClient(_settings(), client=http_client).lookup_by_barcode(
            "8801234567890"
        )

    assert captured["url"].startswith(
        "https://apis.data.go.kr/1471000/FoodQrInfoService01/getFoodQrProdList01"
    )
    assert captured["params"]["serviceKey"] == "test-foodqr-key"
    assert captured["params"]["type"] == "json"
    assert captured["params"]["brcd_no"] == "8801234567890"
    assert captured["params"]["numOfRows"] == "10"
    assert result.status == "matched"
    assert result.message_code == "00"
    product = result.products[0]
    assert product.product_name == "공식 제품"
    assert product.barcode == "8801234567890"
    assert product.business_name == "공식 제조사"
    assert product.report_no == "20070017035202"
    assert product.source_fields == {
        "product_name": "공식 제품",
        "barcode": "8801234567890",
        "business_name": "공식 제조사",
        "report_no": "20070017035202",
        "version": "1",
        "valid_from": "20240101",
        "valid_to": "99991231",
    }


@pytest.mark.asyncio
async def test_foodqr_fetch_product_list_parses_top_level_public_data_shape() -> None:
    """Verify FoodQR top-level header/body responses are parsed."""
    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        """Capture request and return the live FoodQR response envelope shape."""
        captured["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
                "body": {
                    "pageNo": 1,
                    "totalCount": 1,
                    "numOfRows": 1,
                    "items": [
                        {
                            "PRDT_NM": "공개 제품",
                            "BRCD_NO": "08802259029434",
                            "ENTP_NM": "공개 업체",
                            "VER_INFO": "3",
                            "VLD_BGNG_YMD": "20260420",
                            "VLD_END_YMD": "99991231",
                        }
                    ],
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        result = await FoodQrClient(_settings(), client=http_client).fetch_product_list(
            page_no=2,
            num_of_rows=1,
        )

    assert captured["params"]["pageNo"] == "2"
    assert "brcd_no" not in captured["params"]
    assert result.status == "matched"
    assert result.message_code == "00"
    product = result.products[0]
    assert product.product_name == "공개 제품"
    assert product.business_name == "공개 업체"
    assert product.barcode == "08802259029434"


@pytest.mark.asyncio
async def test_foodqr_product_manufacturing_info_fails_closed_without_configured_path() -> None:
    """Verify FoodQR detail lookup is disabled until the official path is configured."""
    client = FoodQrClient(_settings(foodqr_product_manufacturing_path=None))

    result = await client.fetch_product_manufacturing_info(barcode="08802259029434")

    assert result.status == "not_configured"
    assert result.products == ()
    assert result.message == "FoodQR product-manufacturing endpoint path is not configured."


@pytest.mark.asyncio
async def test_foodqr_product_manufacturing_info_uses_configured_path_and_parses_rows() -> None:
    """Verify opt-in FoodQR detail lookup uses only configured endpoint paths."""
    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        """Capture request and return a configured-path FoodQR-like response."""
        captured["url"] = str(request.url)
        captured["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
                "body": {
                    "items": [
                        {
                            "PRDLST_NM": "상세 제품",
                            "BRCD_NO": "08802259029434",
                            "BSSH_NM": "상세 업체",
                            "PRDLST_REPORT_NO": "20070017035215",
                            "VER_INFO": "3",
                        }
                    ],
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        result = await FoodQrClient(
            _settings(foodqr_product_manufacturing_path="/configured-test-endpoint"),
            client=http_client,
        ).fetch_product_manufacturing_info(
            barcode="08802259029434",
            version="3",
            page_no=2,
            num_of_rows=1,
        )

    assert captured["url"].startswith(
        "https://apis.data.go.kr/1471000/FoodQrInfoService01/configured-test-endpoint"
    )
    assert captured["params"]["serviceKey"] == "test-foodqr-key"
    assert captured["params"]["brcd_no"] == "08802259029434"
    assert captured["params"]["ver_info"] == "3"
    assert captured["params"]["pageNo"] == "2"
    assert captured["params"]["numOfRows"] == "1"
    assert result.status == "matched"
    product = result.products[0]
    assert product.product_name == "상세 제품"
    assert product.report_no == "20070017035215"


@pytest.mark.asyncio
async def test_foodqr_lookup_maps_provider_no_data() -> None:
    """Verify FoodQR no-data codes become not_found instead of exceptions."""

    async def handler(_request: httpx.Request) -> httpx.Response:
        """Return a FoodQR no-data envelope."""
        return httpx.Response(
            200,
            json={
                "response": {
                    "header": {"resultCode": "03", "resultMsg": "NO_DATA"},
                    "body": {"items": {}},
                }
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        result = await FoodQrClient(_settings(), client=http_client).lookup_by_barcode(
            "8800000000000"
        )

    assert result.status == "not_found"
    assert result.message_code == "03"


@pytest.mark.asyncio
async def test_foodqr_lookup_sanitizes_http_errors() -> None:
    """Verify FoodQR HTTP failures do not expose provider credentials."""

    async def handler(_request: httpx.Request) -> httpx.Response:
        """Return a provider HTTP failure."""
        return httpx.Response(500, json={"secret": "test-foodqr-key"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        with pytest.raises(FoodQrClientError) as exc_info:
            await FoodQrClient(_settings(), client=http_client).lookup_by_barcode("8801234567890")

    assert "test-foodqr-key" not in str(exc_info.value)
