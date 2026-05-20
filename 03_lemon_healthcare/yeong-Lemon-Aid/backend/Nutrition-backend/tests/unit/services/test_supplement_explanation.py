"""Supplement recommendation explanation service tests."""

from __future__ import annotations

import pytest
from src.config import Settings
from src.models.schemas.supplement_recommendation import (
    SupplementImpactDataStatus,
    SupplementImpactPreviewResponse,
    SupplementRecommendationExplainRequest,
)
from src.services.supplement_explanation import (
    build_deterministic_explanation,
    explain_supplement_recommendation,
)
from src.services.supplement_recommendation import SUPPLEMENT_IMPACT_DISCLAIMER


def _preview(
    *, clinical_disclaimer: str = "client controlled disclaimer"
) -> SupplementImpactPreviewResponse:
    """Return a deterministic supplement impact preview fixture.

    Args:
        clinical_disclaimer: Client-supplied disclaimer candidate.

    Returns:
        Supplement impact preview response fixture.
    """
    return SupplementImpactPreviewResponse(
        reference_version="2025",
        source_manifest_version="kdris-source-v1",
        data_status=SupplementImpactDataStatus.READY,
        current_supplement_contributions=[],
        deficiency_support_candidates=[],
        excess_or_duplicate_risks=[],
        missing_profile_fields=[],
        safe_user_message="현재 입력 기준으로 표시할 추가 보충제 영향 항목이 없습니다.",
        clinical_disclaimer=clinical_disclaimer,
        warnings=[],
        requires_user_confirmation=True,
    )


def test_build_deterministic_explanation_stamps_server_disclaimer() -> None:
    """Verify deterministic explanations do not trust client disclaimer text."""
    request = SupplementRecommendationExplainRequest(preview=_preview())

    response = build_deterministic_explanation(request, warnings=())

    assert response.clinical_disclaimer == SUPPLEMENT_IMPACT_DISCLAIMER
    assert response.llm_used is False


@pytest.mark.asyncio
async def test_explain_supplement_recommendation_stamps_server_disclaimer() -> None:
    """Verify public explanation service overwrites client disclaimer text."""
    request = SupplementRecommendationExplainRequest(preview=_preview(), use_local_llm=False)

    response = await explain_supplement_recommendation(request, Settings())

    assert response.clinical_disclaimer == SUPPLEMENT_IMPACT_DISCLAIMER
    assert "client controlled disclaimer" not in response.model_dump_json()
