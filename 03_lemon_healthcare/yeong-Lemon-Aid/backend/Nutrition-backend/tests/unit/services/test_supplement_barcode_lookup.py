"""Supplement barcode lookup service tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import Settings
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.supplement import SupplementAnalysisStatus
from src.nutrition.foodqr_client import FoodQrClientError, FoodQrLookupResult, FoodQrProduct
from src.nutrition.mfds_client import MfdsLookupResult
from src.services.supplement_barcode_lookup import (
    BARCODE_LOOKUP_MULTIPLE_ROWS_WARNING,
    C003_PROVIDER_ERROR_WARNING,
    SupplementBarcodeLookupService,
    attach_barcode_lookup_to_analysis,
)


class _FakeFoodQrClient:
    """Fake FoodQR client for service tests."""

    def __init__(
        self,
        result: FoodQrLookupResult | None = None,
        *,
        fail: bool = False,
    ) -> None:
        self.result = result
        self.fail = fail
        self.calls: list[str] = []

    async def lookup_by_barcode(self, barcode: str) -> FoodQrLookupResult:
        """Return a configured FoodQR result.

        Args:
            barcode: Normalized barcode.

        Returns:
            Configured FoodQR result.

        Raises:
            FoodQrClientError: When configured to fail.
        """

        self.calls.append(barcode)
        if self.fail:
            raise FoodQrClientError("fake FoodQR failure")
        assert self.result is not None
        return self.result


class _FakeMfdsClient:
    """Fake MFDS client for C003 lookups."""

    def __init__(self, result: MfdsLookupResult | None = None) -> None:
        self.result = result or MfdsLookupResult(
            provider="mfds_openapi",
            service_id="C003",
            status="not_found",
            message_code="INFO-200",
        )
        self.calls: list[str] = []

    async def get_product_by_report_no(self, report_no: str) -> MfdsLookupResult:
        """Return a configured C003 result.

        Args:
            report_no: MFDS report number.

        Returns:
            Configured MFDS result.
        """

        self.calls.append(report_no)
        return self.result


class _FakeSession:
    """Fake async session for snapshot attachment."""

    def __init__(self) -> None:
        self.committed = False
        self.refreshed = False

    async def commit(self) -> None:
        """Record commit.

        Returns:
            None.
        """

        self.committed = True

    async def refresh(self, _record: object) -> None:
        """Record refresh.

        Args:
            _record: Ignored ORM object.

        Returns:
            None.
        """

        self.refreshed = True


def _settings(*, enable_barcode_lookup: bool = True) -> Settings:
    """Return service test settings.

    Args:
        enable_barcode_lookup: Feature flag value.

    Returns:
        Settings object.
    """

    return Settings(
        _env_file=None,
        enable_barcode_lookup=enable_barcode_lookup,
        foodqr_service_key=SecretStr("test-foodqr-key"),
        mfds_api_key=SecretStr("test-mfds-key"),
    )


def _foodqr_product(
    *,
    product_name: str = "공식 제품",
    barcode: str = "08801007325224",
    report_no: str | None = None,
    version: str = "1",
) -> FoodQrProduct:
    """Return a FoodQR product fixture.

    Args:
        product_name: Product name.
        barcode: Barcode value.
        report_no: Optional MFDS report number.
        version: FoodQR version.

    Returns:
        FoodQR product row.
    """

    return FoodQrProduct(
        product_name=product_name,
        barcode=barcode,
        business_name="공식 업체",
        report_no=report_no,
        version=version,
        valid_from="20250101",
        valid_to="99991231",
        source_fields={"product_name": product_name},
    )


def _analysis_run() -> SupplementAnalysisRun:
    """Return a supplement analysis row fixture.

    Returns:
        Supplement analysis row.
    """

    now = datetime.now(UTC)
    return SupplementAnalysisRun(
        id=uuid4(),
        owner_subject="local-development::local-dev-user",
        status=SupplementAnalysisStatus.REQUIRES_CONFIRMATION.value,
        image_sha256="a" * 64,
        image_mime_type="image/png",
        image_size_bytes=128,
        ocr_provider="intake-only",
        parsed_snapshot={"parsed_product": {}, "ingredient_candidates": []},
        match_snapshot={"matched_product_candidates": []},
        warnings=[],
        algorithm_version="supplement-intake-v1.0.0",
        expires_at=now + timedelta(minutes=30),
    )


@pytest.mark.asyncio
async def test_barcode_lookup_fails_closed_when_feature_disabled() -> None:
    """Verify disabled lookup returns not_configured without provider calls."""
    foodqr_client = _FakeFoodQrClient()
    service = SupplementBarcodeLookupService(
        _settings(enable_barcode_lookup=False),
        foodqr_client=foodqr_client,  # type: ignore[arg-type]
    )

    result = await service.lookup("08801007325224")

    assert result.status == "not_configured"
    assert foodqr_client.calls == []


@pytest.mark.asyncio
async def test_barcode_lookup_rejects_invalid_checksum_before_provider_call() -> None:
    """Verify invalid barcode values do not call FoodQR."""
    foodqr_client = _FakeFoodQrClient()
    service = SupplementBarcodeLookupService(
        _settings(),
        foodqr_client=foodqr_client,  # type: ignore[arg-type]
    )

    result = await service.lookup("8801234567890")

    assert result.status == "invalid_request"
    assert result.error_code == "barcode_check_digit_invalid"
    assert foodqr_client.calls == []


@pytest.mark.asyncio
async def test_barcode_lookup_returns_review_required_foodqr_candidate() -> None:
    """Verify a single FoodQR row becomes a review-only candidate."""
    foodqr_result = FoodQrLookupResult(
        provider="foodqr",
        status="matched",
        products=(_foodqr_product(),),
        message_code="00",
    )
    service = SupplementBarcodeLookupService(
        _settings(),
        foodqr_client=_FakeFoodQrClient(foodqr_result),  # type: ignore[arg-type]
        mfds_client=_FakeMfdsClient(),  # type: ignore[arg-type]
    )

    result = await service.lookup("08801007325224", barcode_format="GTIN_14")

    assert result.status == "review_required"
    assert result.identifier is not None
    assert result.identifier.normalized_value == "08801007325224"
    assert len(result.candidates) == 1
    assert result.candidates[0].product_name == "공식 제품"
    assert result.candidates[0].review_required_reason == "user_confirmation_required"


@pytest.mark.asyncio
async def test_barcode_lookup_keeps_multiple_foodqr_rows_review_only() -> None:
    """Verify duplicate FoodQR rows are surfaced without auto-confirmation."""
    foodqr_result = FoodQrLookupResult(
        provider="foodqr",
        status="matched",
        products=(
            _foodqr_product(product_name="공식 제품 v1", version="1"),
            _foodqr_product(product_name="공식 제품 v2", version="2"),
        ),
        message_code="00",
    )
    service = SupplementBarcodeLookupService(
        _settings(),
        foodqr_client=_FakeFoodQrClient(foodqr_result),  # type: ignore[arg-type]
        mfds_client=_FakeMfdsClient(),  # type: ignore[arg-type]
    )

    result = await service.lookup("08801007325224")

    assert result.status == "review_required"
    assert len(result.candidates) == 2
    assert BARCODE_LOOKUP_MULTIPLE_ROWS_WARNING in result.warnings
    assert all(candidate.match_score < 0.8 for candidate in result.candidates)


@pytest.mark.asyncio
async def test_barcode_lookup_c003_provider_error_does_not_block_foodqr_candidate() -> None:
    """Verify C003 authorization errors degrade without losing FoodQR candidates."""
    foodqr_result = FoodQrLookupResult(
        provider="foodqr",
        status="matched",
        products=(_foodqr_product(report_no="202400000001"),),
        message_code="00",
    )
    mfds_result = MfdsLookupResult(
        provider="mfds_openapi",
        service_id="C003",
        status="provider_error",
        message_code="NON_JSON_PROVIDER_ERROR",
    )
    mfds_client = _FakeMfdsClient(mfds_result)
    service = SupplementBarcodeLookupService(
        _settings(),
        foodqr_client=_FakeFoodQrClient(foodqr_result),  # type: ignore[arg-type]
        mfds_client=mfds_client,  # type: ignore[arg-type]
    )

    result = await service.lookup("08801007325224")

    assert result.status == "review_required"
    assert len(result.candidates) == 1
    assert mfds_client.calls == ["202400000001"]
    assert C003_PROVIDER_ERROR_WARNING in result.warnings
    assert result.observations[-1].provider == "mfds_c003"


@pytest.mark.asyncio
async def test_attach_barcode_lookup_to_analysis_persists_sanitized_snapshot() -> None:
    """Verify preview snapshots store candidate metadata without raw provider payloads."""
    foodqr_result = FoodQrLookupResult(
        provider="foodqr",
        status="matched",
        products=(_foodqr_product(),),
        message_code="00",
    )
    service = SupplementBarcodeLookupService(
        _settings(),
        foodqr_client=_FakeFoodQrClient(foodqr_result),  # type: ignore[arg-type]
        mfds_client=_FakeMfdsClient(),  # type: ignore[arg-type]
    )
    lookup_result = await service.lookup("08801007325224")
    record = _analysis_run()
    session = _FakeSession()

    updated = await attach_barcode_lookup_to_analysis(
        cast(AsyncSession, session),
        record,
        lookup_result,
    )

    assert session.committed is True
    assert session.refreshed is True
    barcode_snapshot = updated.parsed_snapshot["barcode_lookup"]
    assert barcode_snapshot["status"] == "review_required"
    assert barcode_snapshot["raw_provider_payload_stored"] is False
    assert "raw_payload" not in str(barcode_snapshot)
    assert updated.match_snapshot["barcode_lookup"]["auto_confirmed"] is False
    assert updated.match_snapshot["matched_product_candidates"][0]["source_id"].startswith(
        "foodqr:"
    )
