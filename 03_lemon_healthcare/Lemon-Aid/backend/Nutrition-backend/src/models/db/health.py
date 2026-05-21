"""Health metric sync and daily summary ORM models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.models.db.mixins import TimestampMixin


class HealthSyncBatch(TimestampMixin, Base):
    """Persist one current-user health data sync intake batch.

    Attributes:
        id: Stable sync batch identifier.
        owner_subject: Issuer-qualified authenticated subject.
        client_batch_id: Optional client idempotency key for replay protection.
        source_platform: Health data source platform.
        record_count: Number of records received from the client.
        accepted_count: Number of records accepted after validation.
        rejected_count: Number of records rejected after validation.
        input_snapshot: Sanitized bounded sync request metadata.
        result_snapshot: Sanitized bounded sync outcome metadata.
        synced_at: Time when the server accepted the batch.
        created_at: Server-side record creation timestamp.
        updated_at: Server-side record update timestamp.
    """

    __tablename__ = "health_sync_batches"
    __table_args__ = (
        UniqueConstraint(
            "owner_subject",
            "client_batch_id",
            name="uq_health_sync_batches_owner_client_batch",
        ),
        CheckConstraint(
            "source_platform IN ('ios_healthkit', 'android_health_connect', 'manual', 'mixed')",
            name="source_platform_allowed",
        ),
        CheckConstraint("record_count >= 0", name="record_count_nonnegative"),
        CheckConstraint("accepted_count >= 0", name="accepted_count_nonnegative"),
        CheckConstraint("rejected_count >= 0", name="rejected_count_nonnegative"),
        CheckConstraint(
            "accepted_count + rejected_count <= record_count",
            name="accepted_rejected_count_valid",
        ),
        Index("ix_health_sync_batches_owner_synced_at", "owner_subject", "synced_at"),
    )

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_subject: Mapped[str] = mapped_column(String(512), nullable=False)
    client_batch_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_platform: Mapped[str] = mapped_column(String(32), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, nullable=False, default=dict
    )
    result_snapshot: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, nullable=False, default=dict
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class HealthDailySummary(TimestampMixin, Base):
    """Persist one owner-scoped daily health metric summary.

    Attributes:
        id: Stable health summary identifier.
        owner_subject: Issuer-qualified authenticated subject.
        measured_date: User-local date represented by the client.
        source_platform: Health data source platform.
        steps: Daily step count when available.
        weight_kg: Body weight in kilograms when available.
        resting_heart_rate_bpm: Resting heart rate when available.
        active_energy_kcal: Active energy estimate when available.
        source_record_hash: Optional hash for client-side duplicate detection.
        synced_at: Time when the server accepted the summary.
        created_at: Server-side record creation timestamp.
        updated_at: Server-side record update timestamp.
    """

    __tablename__ = "health_daily_summaries"
    __table_args__ = (
        UniqueConstraint(
            "owner_subject",
            "measured_date",
            "source_platform",
            name="uq_health_daily_summaries_owner_date_platform",
        ),
        CheckConstraint(
            "source_platform IN ('ios_healthkit', 'android_health_connect', 'manual')",
            name="source_platform_allowed",
        ),
        CheckConstraint(
            (
                "steps IS NOT NULL OR weight_kg IS NOT NULL OR "
                "resting_heart_rate_bpm IS NOT NULL OR active_energy_kcal IS NOT NULL"
            ),
            name="health_metric_present",
        ),
        CheckConstraint("steps IS NULL OR (steps >= 0 AND steps <= 200000)", name="steps_range"),
        CheckConstraint(
            "weight_kg IS NULL OR (weight_kg >= 20 AND weight_kg <= 300)",
            name="weight_kg_range",
        ),
        CheckConstraint(
            (
                "resting_heart_rate_bpm IS NULL OR "
                "(resting_heart_rate_bpm >= 20 AND resting_heart_rate_bpm <= 240)"
            ),
            name="resting_heart_rate_range",
        ),
        CheckConstraint(
            "active_energy_kcal IS NULL OR (active_energy_kcal >= 0 AND active_energy_kcal <= 20000)",
            name="active_energy_kcal_range",
        ),
        Index("ix_health_daily_summaries_owner_measured_date", "owner_subject", "measured_date"),
        Index(
            "ix_health_daily_summaries_owner_source_date",
            "owner_subject",
            "source_platform",
            "measured_date",
        ),
    )

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_subject: Mapped[str] = mapped_column(String(512), nullable=False)
    measured_date: Mapped[date] = mapped_column(Date, nullable=False, primary_key=True)
    source_platform: Mapped[str] = mapped_column(String(32), nullable=False)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    resting_heart_rate_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_energy_kcal: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    source_record_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
