"""Dashboard summary API contract schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardNutrientSummary(BaseModel):
    """Nutrition summary for dashboard display.

    Attributes:
        data_status: Whether a persisted nutrition analysis is available.
        latest_result_id: Latest persisted nutrition result identifier.
        low_count: Number of nutrients below configured reference range.
        high_count: Number of nutrients above configured reference range.
        dataset_version: KDRIs dataset version used for the summary.
        source_manifest_version: Source manifest version used for the summary.
    """

    data_status: str = Field(default="not_ready", pattern=r"^(ready|not_ready)$")
    latest_result_id: UUID | None = None
    low_count: int = Field(ge=0)
    high_count: int = Field(ge=0)
    dataset_version: str | None = None
    source_manifest_version: str | None


class DashboardActivitySummary(BaseModel):
    """Activity summary for dashboard display.

    Attributes:
        data_status: Whether current-user activity data is available.
        latest_steps: Latest synced daily step count.
        latest_resting_heart_rate_bpm: Latest synced resting heart rate.
        latest_active_energy_kcal: Latest synced active energy estimate.
        latest_activity_score: Latest computed activity score.
        measured_date: Date for the latest activity values.
    """

    data_status: str = Field(default="not_ready", pattern=r"^(ready|not_ready)$")
    latest_steps: int | None = Field(default=None, ge=0)
    latest_resting_heart_rate_bpm: int | None = Field(default=None, ge=20, le=240)
    latest_active_energy_kcal: float | None = Field(default=None, ge=0, le=20000)
    latest_activity_score: float | None = Field(default=None, ge=0, le=120)
    measured_date: date | None = None


class DashboardWeightSummary(BaseModel):
    """Weight summary for dashboard display.

    Attributes:
        data_status: Whether current-user weight data is available.
        latest_weight_kg: Latest synced or entered weight.
        predicted_weight_kg: Latest short-term predicted weight.
        measured_date: Date for the latest weight value.
    """

    data_status: str = Field(default="not_ready", pattern=r"^(ready|not_ready)$")
    latest_weight_kg: float | None = Field(default=None, ge=20, le=300)
    predicted_weight_kg: float | None = Field(default=None, ge=20, le=300)
    measured_date: date | None = None


class DashboardSupplementSummary(BaseModel):
    """Supplement summary for dashboard display.

    Attributes:
        registered_count: Current-user registered supplement count.
        requires_review_count: Count of supplement records that need user review.
    """

    registered_count: int = Field(ge=0)
    requires_review_count: int = Field(ge=0)


class DashboardSummaryResponse(BaseModel):
    """Current-user dashboard summary response.

    Attributes:
        as_of: Server-side summary timestamp.
        nutrition: Nutrition summary.
        activity: Activity summary.
        weight: Weight summary.
        supplements: Supplement summary.
        disclaimers: User-facing safety notices.
        algorithm_version: Dashboard aggregation contract version.
    """

    as_of: datetime
    nutrition: DashboardNutrientSummary
    activity: DashboardActivitySummary
    weight: DashboardWeightSummary
    supplements: DashboardSupplementSummary
    disclaimers: list[str]
    algorithm_version: str
