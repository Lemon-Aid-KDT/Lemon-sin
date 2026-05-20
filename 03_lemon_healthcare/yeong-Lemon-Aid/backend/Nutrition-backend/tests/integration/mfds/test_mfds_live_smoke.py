"""Opt-in MFDS OpenAPI live smoke tests.

These tests call FoodSafetyKorea OpenAPI only when RUN_MFDS_LIVE_SMOKE=1 is set.
They validate keyId/endpoint wiring without printing credentials or raw payloads.
"""

from __future__ import annotations

import os

import pytest
from src.config import Settings
from src.nutrition.mfds_client import MFDS_C003_SERVICE_ID, MFDS_I0760_SERVICE_ID, MfdsOpenAPIClient

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_MFDS_LIVE_SMOKE") != "1",
    reason="MFDS smoke test requires RUN_MFDS_LIVE_SMOKE=1.",
)


@pytest.mark.asyncio
async def test_mfds_c003_live_smoke_returns_typed_result() -> None:
    """Verify MFDS C003 returns a typed result or provider authorization error."""
    settings = Settings()
    assert settings.enable_barcode_lookup is True
    assert settings.mfds_api_key is not None

    report_no = os.getenv("MFDS_SMOKE_REPORT_NO", "20070017035202")
    result = await MfdsOpenAPIClient(settings).get_product_by_report_no(report_no)

    assert result.provider == "mfds_openapi"
    assert result.service_id == MFDS_C003_SERVICE_ID
    assert result.status in {"matched", "not_found", "provider_error"}
    assert result.message_code != "INFO-100"
    for product in result.products:
        assert "keyId" not in product.source_fields


@pytest.mark.asyncio
async def test_mfds_i0760_live_smoke_accepts_configured_key() -> None:
    """Verify MFDS I0760 can be reached for ingredient enrichment wiring."""
    settings = Settings()
    assert settings.enable_barcode_lookup is True
    assert settings.mfds_api_key is not None

    result = await MfdsOpenAPIClient(settings).get_ingredient_rows()

    assert result.provider == "mfds_openapi"
    assert result.service_id == MFDS_I0760_SERVICE_ID
    assert result.status in {"matched", "not_found"}
    assert result.message_code != "INFO-100"
