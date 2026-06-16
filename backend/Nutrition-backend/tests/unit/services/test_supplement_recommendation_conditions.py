"""Unit tests for chronic-condition auto-load in supplement impact preview."""

from __future__ import annotations

import pytest
from src.models.schemas.user import UserProfile
from src.services import supplement_recommendation as svc
from src.services.medical_records import MedicalContextSummary


def _profile(chronic: list[str] | None = None) -> UserProfile:
    return UserProfile(
        age=44,
        sex="female",
        height_cm=160,
        weight_kg=58,
        chronic_diseases=chronic or [],
    )


def _summary(codes: tuple[str, ...]) -> MedicalContextSummary:
    return MedicalContextSummary(
        condition_count=len(codes),
        canonical_condition_codes=codes,
    )


@pytest.mark.asyncio
async def test_stored_conditions_merge_into_profile(monkeypatch) -> None:
    """Recorded conditions are auto-loaded into an otherwise condition-free profile."""

    async def _fake_summary(*_args, **_kwargs):
        return _summary(("diabetes",))

    monkeypatch.setattr(svc, "get_current_medical_context_summary", _fake_summary)

    result = await svc._apply_stored_chronic_conditions(object(), object(), _profile())

    assert result is not None
    assert "diabetes" in result.chronic_diseases


@pytest.mark.asyncio
async def test_stored_conditions_dedupe_with_existing(monkeypatch) -> None:
    """Auto-load merges without duplicating conditions already on the profile."""

    async def _fake_summary(*_args, **_kwargs):
        return _summary(("diabetes", "hypertension"))

    monkeypatch.setattr(svc, "get_current_medical_context_summary", _fake_summary)

    result = await svc._apply_stored_chronic_conditions(
        object(), object(), _profile(["diabetes"])
    )

    assert result is not None
    assert result.chronic_diseases.count("diabetes") == 1
    assert "hypertension" in result.chronic_diseases


@pytest.mark.asyncio
async def test_no_stored_conditions_keeps_profile_unchanged(monkeypatch) -> None:
    """A profile is returned unchanged when no recorded conditions apply."""

    async def _fake_summary(*_args, **_kwargs):
        return _summary(())

    monkeypatch.setattr(svc, "get_current_medical_context_summary", _fake_summary)

    profile = _profile(["hypertension"])
    result = await svc._apply_stored_chronic_conditions(object(), object(), profile)

    assert result is profile


@pytest.mark.asyncio
async def test_none_profile_returns_none() -> None:
    """A missing profile stays missing (no medical-records lookup needed)."""
    result = await svc._apply_stored_chronic_conditions(object(), object(), None)
    assert result is None
