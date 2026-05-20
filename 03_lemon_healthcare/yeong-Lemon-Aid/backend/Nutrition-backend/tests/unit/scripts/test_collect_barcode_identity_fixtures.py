"""Tests for redacted barcode fixture collection helpers."""

from __future__ import annotations

from src.nutrition.foodqr_client import FoodQrLookupResult, FoodQrProduct
from src.nutrition.mfds_client import MfdsLookupResult

from scripts.collect_barcode_identity_fixtures import _fixture_row


def test_fixture_row_contains_allowlisted_fields_only() -> None:
    """Verify collected fixture rows exclude credentials and raw payloads."""
    product = FoodQrProduct(
        product_name="공개 제품",
        barcode="08802259029434",
        business_name="공개 업체",
        report_no="202400000001",
        version="3",
        valid_from="20260420",
        valid_to="99991231",
        source_fields={"product_name": "공개 제품"},
    )
    mfds_result = MfdsLookupResult(
        provider="mfds_openapi",
        service_id="C003",
        status="provider_error",
        message_code="NON_JSON_PROVIDER_ERROR",
    )
    foodqr_result = FoodQrLookupResult(
        provider="foodqr",
        status="matched",
        products=(product,),
        message_code="00",
    )

    row = _fixture_row(product, foodqr_result=foodqr_result, mfds_result=mfds_result, index=1)

    assert row["fixture_id"] == "foodqr-public-001"
    assert row["source_rights"] == "public_foodqr_openapi"
    assert row["barcode_text"] == "08802259029434"
    assert "serviceKey" not in row
    assert "raw_payload" not in row
    observations = row["observations"]
    assert isinstance(observations, list)
    assert observations[0] == {
        "provider": "foodqr",
        "status": "matched",
        "message_code": "00",
        "item_count": 1,
    }
    assert observations[1] == {
        "provider": "mfds_c003",
        "status": "provider_error",
        "message_code": "NON_JSON_PROVIDER_ERROR",
        "item_count": 0,
    }
