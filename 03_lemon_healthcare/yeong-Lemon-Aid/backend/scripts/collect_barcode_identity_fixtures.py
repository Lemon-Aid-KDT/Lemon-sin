"""Collect redacted FoodQR barcode identity fixtures.

The collector uses only public FoodQR rows and optional MFDS C003 observations.
It writes allowlisted fields only: no service keys, full request URLs, or raw
provider payloads are persisted.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.config import Settings  # noqa: E402
from src.nutrition.foodqr_client import (  # noqa: E402
    FoodQrClient,
    FoodQrLookupResult,
    FoodQrProduct,
)
from src.nutrition.mfds_client import MfdsLookupResult, MfdsOpenAPIClient  # noqa: E402


def main() -> None:
    """Run the fixture collector from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--page-size", type=int, default=25)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--mfds-check-limit", type=int, default=5)
    args = parser.parse_args()

    rows = asyncio.run(
        collect_fixture_rows(
            limit=args.limit,
            page_size=args.page_size,
            max_pages=args.max_pages,
            mfds_check_limit=args.mfds_check_limit,
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


async def collect_fixture_rows(
    *,
    limit: int,
    page_size: int,
    max_pages: int,
    mfds_check_limit: int,
) -> list[dict[str, object]]:
    """Collect allowlisted FoodQR fixture rows.

    Args:
        limit: Maximum fixture rows to collect.
        page_size: FoodQR page size.
        max_pages: Maximum FoodQR pages to scan.
        mfds_check_limit: Maximum rows with report numbers to verify against C003.

    Returns:
        JSON-serializable fixture rows.
    """
    if limit < 1 or page_size < 1 or max_pages < 1:
        raise ValueError("limit, page_size, and max_pages must be positive.")

    settings = Settings()
    foodqr_client = FoodQrClient(settings)
    mfds_client = MfdsOpenAPIClient(settings)
    rows: list[dict[str, object]] = []
    seen_barcodes: set[str] = set()
    mfds_checks = 0

    for page_no in range(1, max_pages + 1):
        result = await foodqr_client.fetch_product_list(page_no=page_no, num_of_rows=page_size)
        if result.status != "matched":
            continue
        for product in result.products:
            barcode = product.barcode
            if not barcode or barcode in seen_barcodes:
                continue
            seen_barcodes.add(barcode)
            foodqr_lookup = await foodqr_client.lookup_by_barcode(barcode)
            if foodqr_lookup.status != "matched" or not foodqr_lookup.products:
                continue
            matched_product = _select_matching_product(foodqr_lookup, barcode=barcode)
            mfds_result: MfdsLookupResult | None = None
            if matched_product.report_no and mfds_checks < mfds_check_limit:
                mfds_result = await mfds_client.get_product_by_report_no(matched_product.report_no)
                mfds_checks += 1
            rows.append(
                _fixture_row(
                    matched_product,
                    foodqr_result=foodqr_lookup,
                    mfds_result=mfds_result,
                    index=len(rows) + 1,
                )
            )
            if len(rows) >= limit:
                return rows
    return rows


def _select_matching_product(
    result: FoodQrLookupResult,
    *,
    barcode: str,
) -> FoodQrProduct:
    """Select the exact barcode product from a matched FoodQR lookup.

    Args:
        result: FoodQR exact lookup result.
        barcode: Barcode value used for exact lookup.

    Returns:
        Matching product row, or the first provider row if the exact value is
        absent despite a matched provider status.
    """
    for product in result.products:
        if product.barcode == barcode:
            return product
    return result.products[0]


def _fixture_row(
    product: FoodQrProduct,
    *,
    foodqr_result: FoodQrLookupResult,
    mfds_result: MfdsLookupResult | None,
    index: int,
) -> dict[str, object]:
    """Build one redacted fixture row.

    Args:
        product: FoodQR product row.
        mfds_result: Optional C003 observation.
        index: Fixture sequence number.

    Returns:
        JSON-serializable fixture row.
    """
    observations: list[dict[str, object]] = [
        {
            "provider": "foodqr",
            "status": foodqr_result.status,
            "message_code": foodqr_result.message_code,
            "item_count": len(foodqr_result.products),
        }
    ]
    if mfds_result is not None:
        observations.append(
            {
                "provider": "mfds_c003",
                "status": mfds_result.status,
                "message_code": mfds_result.message_code,
                "item_count": len(mfds_result.products),
            }
        )

    return {
        "fixture_id": f"foodqr-public-{index:03d}",
        "source_rights": "public_foodqr_openapi",
        "barcode_text": product.barcode,
        "barcode_format": "unknown_public_provider_value",
        "expected_foodqr": {
            "status": "matched",
            "product_name": product.product_name,
            "business_name": product.business_name,
            "report_no": product.report_no,
            "version": product.version,
            "valid_from": product.valid_from,
            "valid_to": product.valid_to,
        },
        "observations": observations,
        "notes": "Allowlisted FoodQR public API row. No raw provider payload or credentials stored.",
    }


if __name__ == "__main__":
    main()
