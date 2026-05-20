"""Tests for redacted MFDS C003 access diagnostics."""

from __future__ import annotations

import pytest
from src.nutrition.mfds_client import (
    MFDS_C003_SERVICE_ID,
    MFDS_I0760_SERVICE_ID,
    MFDS_PROVIDER,
    MfdsLookupResult,
)

from scripts.diagnose_mfds_c003_access import _authorization_hint, diagnose_mfds_c003_access


class FakeMfdsDiagnosticClient:
    """Fake MFDS client returning deterministic diagnostic statuses."""

    async def fetch_sample_service_rows(
        self,
        *,
        service_id: str,
        start_idx: int = 1,
        end_idx: int = 5,
    ) -> MfdsLookupResult:
        """Return a public sample success result.

        Args:
            service_id: MFDS service id.
            start_idx: One-based start index.
            end_idx: End index.

        Returns:
            Normalized lookup result.
        """
        assert start_idx == 1
        assert end_idx == 5
        return MfdsLookupResult(
            provider=MFDS_PROVIDER,
            service_id=service_id,
            status="matched",
            total_count=1,
            message_code="INFO-000",
        )

    async def fetch_service_rows(
        self,
        *,
        service_id: str,
        start_idx: int = 1,
        end_idx: int | None = None,
    ) -> MfdsLookupResult:
        """Return a private C003 authorization error.

        Args:
            service_id: MFDS service id.
            start_idx: One-based start index.
            end_idx: Optional end index.

        Returns:
            Normalized lookup result.
        """
        assert start_idx == 1
        assert end_idx == 5
        return MfdsLookupResult(
            provider=MFDS_PROVIDER,
            service_id=service_id,
            status="provider_error",
            message_code="INFO-400",
        )

    async def get_product_by_report_no(self, report_no: str) -> MfdsLookupResult:
        """Return a C003 exact-report authorization error.

        Args:
            report_no: MFDS report number.

        Returns:
            Normalized lookup result.
        """
        assert report_no == "20070017035202"
        return MfdsLookupResult(
            provider=MFDS_PROVIDER,
            service_id=MFDS_C003_SERVICE_ID,
            status="provider_error",
            message_code="INFO-400",
        )

    async def get_ingredient_rows(self) -> MfdsLookupResult:
        """Return an I0760 success result.

        Returns:
            Normalized lookup result.
        """
        return MfdsLookupResult(
            provider=MFDS_PROVIDER,
            service_id=MFDS_I0760_SERVICE_ID,
            status="matched",
            total_count=1,
            message_code="INFO-000",
        )


def test_authorization_hint_maps_provider_codes() -> None:
    """Verify known MFDS codes become stable access hints."""
    result = MfdsLookupResult(
        provider=MFDS_PROVIDER,
        service_id=MFDS_C003_SERVICE_ID,
        status="provider_error",
        message_code="INFO-400",
    )

    assert _authorization_hint(result) == "service_not_authorized"


@pytest.mark.asyncio
async def test_diagnosis_summary_contains_redacted_observations_only() -> None:
    """Verify diagnostics do not persist credentials, URLs, or raw provider payloads."""
    summary = await diagnose_mfds_c003_access(
        report_no="20070017035202",
        client=FakeMfdsDiagnosticClient(),
    )

    assert summary["credentials_stored"] is False
    assert summary["raw_provider_payload_stored"] is False
    checks = summary["checks"]
    assert isinstance(checks, list)
    assert len(checks) == 4
    assert checks[0]["check"] == "mfds_c003_sample_first_page"
    assert checks[0]["authorization_hint"] == "reachable"
    assert checks[1]["authorization_hint"] == "service_not_authorized"
    for check in checks:
        assert check["credentials_stored"] is False
        assert check["raw_provider_payload_stored"] is False
        assert "request_url" not in check
        assert "raw_payload" not in check
        assert "keyId" not in check
