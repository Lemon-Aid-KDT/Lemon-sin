"""Opt-in FoodQR live smoke tests.

These tests call the public FoodQR API only when RUN_FOODQR_LIVE_SMOKE=1 is set.
They validate endpoint/key wiring without printing credentials or raw payloads.
"""

from __future__ import annotations

import os

import pytest
from src.config import Settings
from src.nutrition.foodqr_client import FoodQrClient

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_FOODQR_LIVE_SMOKE") != "1",
    reason="FoodQR smoke test requires RUN_FOODQR_LIVE_SMOKE=1.",
)


@pytest.mark.asyncio
async def test_foodqr_live_smoke_accepts_configured_service_key() -> None:
    """Verify FoodQR accepts the configured key and returns a typed lookup result."""
    settings = Settings()
    assert settings.enable_barcode_lookup is True
    assert settings.foodqr_service_key is not None

    barcode = os.getenv("FOODQR_SMOKE_BARCODE", "08801007325224")
    result = await FoodQrClient(settings).lookup_by_barcode(barcode)

    assert result.provider == "foodqr"
    assert result.status in {"matched", "not_found"}
    assert result.message_code not in {"30", "SERVICE_KEY_IS_NOT_REGISTERED_ERROR"}
    for product in result.products:
        assert "serviceKey" not in product.source_fields
