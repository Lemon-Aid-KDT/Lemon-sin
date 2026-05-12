"""Health device sync API contract schemas."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class HealthDataSourcePlatform(StrEnum):
    """Supported health data source platforms.

    Attributes:
        IOS_HEALTHKIT: iOS HealthKit aggregate data.
        ANDROID_HEALTH_CONNECT: Android Health Connect aggregate data.
        MANUAL: User-entered fallback values.
    """

    IOS_HEALTHKIT = "ios_healthkit"
    ANDROID_HEALTH_CONNECT = "android_health_connect"
    MANUAL = "manual"


class HealthDailyAggregate(BaseModel):
    """One day of health data aggregate values.

    Attributes:
        measured_date: Local calendar date for the aggregate.
        source_platform: Platform that produced the values.
        steps: Daily step count.
        weight_kg: Body weight in kilograms.
        resting_heart_rate_bpm: Resting heart rate in beats per minute.
        active_energy_kcal: Active energy in kilocalories.
        source_record_hash: Optional client-side source hash for duplicate tracing.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    measured_date: date
    source_platform: HealthDataSourcePlatform
    steps: int | None = Field(default=None, ge=0, le=200000)
    weight_kg: float | None = Field(default=None, ge=20, le=300)
    resting_heart_rate_bpm: int | None = Field(default=None, ge=20, le=240)
    active_energy_kcal: float | None = Field(default=None, ge=0, le=20000)
    source_record_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[a-fA-F0-9]{64}$",
    )

    @model_validator(mode="after")
    def validate_health_daily_aggregate(self) -> HealthDailyAggregate:
        """Validate aggregate-level invariants.

        Returns:
            Validated aggregate model.

        Raises:
            ValueError: If no metric is present or the measured date is too far ahead.
        """
        if (
            self.steps is None
            and self.weight_kg is None
            and self.resting_heart_rate_bpm is None
            and self.active_energy_kcal is None
        ):
            raise ValueError("At least one health metric must be present.")
        if self.measured_date > datetime.now(UTC).date() + timedelta(days=1):
            raise ValueError("measured_date cannot be more than one day in the future.")
        return self


class HealthSyncRequest(BaseModel):
    """Request body for syncing health aggregates.

    Attributes:
        client_batch_id: Optional client idempotency key for safe retries.
        records: Daily aggregate records from the client. P1 stores aggregates,
            not raw high-frequency health samples.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    client_batch_id: str | None = Field(default=None, min_length=1, max_length=80)
    records: list[HealthDailyAggregate] = Field(min_length=1, max_length=366)


class HealthSyncResponse(BaseModel):
    """Response for a health aggregate sync request.

    Attributes:
        batch_id: Persisted health sync batch id.
        accepted_count: Number of accepted daily records.
        rejected_count: Number of rejected daily records.
        synced_at: Server-side sync timestamp.
    """

    batch_id: UUID | None = None
    accepted_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    synced_at: datetime
