"""Diagnose MFDS C003 access without storing credentials or raw payloads.

This script is a live smoke helper for the external blocker around C003 service
authorization. It records typed provider status only: no key, full request URL,
query string, HTML body, or raw provider payload is written.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.config import Settings  # noqa: E402
from src.nutrition.mfds_client import (  # noqa: E402
    MFDS_C003_SERVICE_ID,
    MFDS_I0760_SERVICE_ID,
    MFDS_PROVIDER,
    MfdsClientError,
    MfdsLookupResult,
    MfdsOpenAPIClient,
)

AUTHORIZATION_HINTS = {
    "INFO-000": "reachable",
    "INFO-100": "key_rejected_or_wrong_key_type",
    "INFO-200": "reachable_no_data",
    "INFO-300": "quota_exceeded",
    "INFO-400": "service_not_authorized",
    "ERROR-310": "service_id_rejected",
    "NON_JSON_PROVIDER_ERROR": "non_json_provider_error",
}


class MfdsDiagnosticClient(Protocol):
    """Protocol for the MFDS client calls used by diagnostics."""

    def fetch_sample_service_rows(
        self,
        *,
        service_id: str,
        start_idx: int = 1,
        end_idx: int = 5,
    ) -> Awaitable[MfdsLookupResult]:
        """Fetch public sample rows.

        Args:
            service_id: MFDS service id.
            start_idx: One-based start index.
            end_idx: End index.

        Returns:
            Normalized lookup result.
        """

    def fetch_service_rows(
        self,
        *,
        service_id: str,
        start_idx: int = 1,
        end_idx: int | None = None,
    ) -> Awaitable[MfdsLookupResult]:
        """Fetch private-key service rows.

        Args:
            service_id: MFDS service id.
            start_idx: One-based start index.
            end_idx: Optional end index.

        Returns:
            Normalized lookup result.
        """

    def get_product_by_report_no(self, report_no: str) -> Awaitable[MfdsLookupResult]:
        """Fetch one C003 product by report number.

        Args:
            report_no: MFDS report number.

        Returns:
            Normalized lookup result.
        """

    def get_ingredient_rows(self) -> Awaitable[MfdsLookupResult]:
        """Fetch I0760 ingredient rows.

        Returns:
            Normalized lookup result.
        """


def main() -> None:
    """Run the MFDS C003 access diagnosis from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report-no", default="20070017035202")
    parser.add_argument("--sample-end-idx", type=int, default=5)
    args = parser.parse_args()

    summary = asyncio.run(
        diagnose_mfds_c003_access(
            report_no=args.report_no,
            sample_end_idx=args.sample_end_idx,
        )
    )
    rendered = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        sys.stdout.write(rendered)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")


async def diagnose_mfds_c003_access(
    *,
    report_no: str,
    sample_end_idx: int = 5,
    client: MfdsDiagnosticClient | None = None,
) -> dict[str, object]:
    """Run redacted C003/I0760 live access checks.

    Args:
        report_no: C003 품목제조보고번호 used for exact-key diagnosis.
        sample_end_idx: End index for public sample rows.
        client: Optional injected client for tests.

    Returns:
        JSON-serializable diagnostic summary.
    """
    diagnostic_client = client or MfdsOpenAPIClient(Settings())
    checks = [
        await _observe(
            check_name="mfds_c003_sample_first_page",
            service_id=MFDS_C003_SERVICE_ID,
            lookup=lambda: diagnostic_client.fetch_sample_service_rows(
                service_id=MFDS_C003_SERVICE_ID,
                start_idx=1,
                end_idx=sample_end_idx,
            ),
        ),
        await _observe(
            check_name="mfds_c003_first_page",
            service_id=MFDS_C003_SERVICE_ID,
            lookup=lambda: diagnostic_client.fetch_service_rows(
                service_id=MFDS_C003_SERVICE_ID,
                start_idx=1,
                end_idx=5,
            ),
        ),
        await _observe(
            check_name="mfds_c003_report_no",
            service_id=MFDS_C003_SERVICE_ID,
            lookup=lambda: diagnostic_client.get_product_by_report_no(report_no),
        ),
        await _observe(
            check_name="mfds_i0760_first_page",
            service_id=MFDS_I0760_SERVICE_ID,
            lookup=diagnostic_client.get_ingredient_rows,
        ),
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "checks": checks,
        "credentials_stored": False,
        "raw_provider_payload_stored": False,
        "interpretation": (
            "This is an access diagnosis only. It is not barcode matching accuracy, "
            "MFDS coverage, or OCR improvement evidence."
        ),
    }


async def _observe(
    *,
    check_name: str,
    service_id: str,
    lookup: Callable[[], Awaitable[MfdsLookupResult]],
) -> dict[str, object]:
    """Run one provider lookup and convert it to a redacted observation.

    Args:
        check_name: Stable diagnostic check name.
        service_id: MFDS service id.
        lookup: Async lookup function.

    Returns:
        Redacted observation dictionary.
    """
    try:
        result = await lookup()
    except MfdsClientError:
        return {
            "check": check_name,
            "provider": MFDS_PROVIDER,
            "service_id": service_id,
            "status": "provider_error",
            "message_code": "CLIENT_ERROR",
            "item_count": 0,
            "total_count": None,
            "authorization_hint": "client_error",
            "credentials_stored": False,
            "raw_provider_payload_stored": False,
        }

    return {
        "check": check_name,
        "provider": result.provider,
        "service_id": result.service_id,
        "status": result.status,
        "message_code": result.message_code,
        "item_count": len(result.products),
        "total_count": result.total_count,
        "authorization_hint": _authorization_hint(result),
        "credentials_stored": False,
        "raw_provider_payload_stored": False,
    }


def _authorization_hint(result: MfdsLookupResult) -> str:
    """Map a typed MFDS result to an operational access hint.

    Args:
        result: Normalized MFDS lookup result.

    Returns:
        Stable diagnostic hint string.
    """
    if result.message_code in AUTHORIZATION_HINTS:
        return AUTHORIZATION_HINTS[result.message_code]
    if result.status == "not_configured":
        return "credentials_not_configured"
    if result.status == "provider_error":
        return "provider_error"
    if result.status in {"matched", "not_found"}:
        return "reachable"
    return "unknown"


if __name__ == "__main__":
    main()
