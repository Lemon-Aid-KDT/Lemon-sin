"""Barcode normalization tests."""

from __future__ import annotations

import pytest
from src.barcode.normalization import (
    BarcodeNormalizationError,
    barcode_value_hash,
    normalize_barcode_text,
)


def test_normalize_barcode_text_accepts_foodqr_gtin14() -> None:
    """Verify FoodQR public GTIN-14 examples normalize for lookup."""
    identifier = normalize_barcode_text(" 08801007325224 ", scanner_format="ean-13")

    assert identifier.normalized_value == "08801007325224"
    assert identifier.symbology == "gtin14"
    assert identifier.scanner_format == "EAN_13"
    assert identifier.check_digit_valid is True
    assert barcode_value_hash(identifier.normalized_value).startswith("sha256:")


def test_normalize_barcode_text_extracts_brcd_no_from_qr_url() -> None:
    """Verify QR URLs can expose an allowlisted FoodQR barcode parameter."""
    identifier = normalize_barcode_text(
        "https://example.test/qr?brcd_no=08802259029434&ver_info=3",
        scanner_format="QR_CODE",
    )

    assert identifier.normalized_value == "08802259029434"
    assert identifier.symbology == "gtin14"
    assert identifier.scanner_format == "QR_CODE"


@pytest.mark.parametrize(
    ("barcode_text", "error_code"),
    [
        ("not-a-barcode", "barcode_not_numeric"),
        ("12345", "barcode_length_unsupported"),
        ("8801234567890", "barcode_check_digit_invalid"),
    ],
)
def test_normalize_barcode_text_rejects_invalid_values(
    barcode_text: str,
    error_code: str,
) -> None:
    """Verify unsupported barcode values fail before provider lookup."""
    with pytest.raises(BarcodeNormalizationError) as exc_info:
        normalize_barcode_text(barcode_text)

    assert exc_info.value.code == error_code
