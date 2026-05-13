"""Weight prediction selector tests."""

from __future__ import annotations

from typing import Any

from src.prediction.selector import (
    HALL_LITE_WARNING,
    WeightPredictionEngine,
    predict_weight_periods_selected,
)
from src.prediction.weight import predict_weight_periods


def _base_kwargs() -> dict[str, Any]:
    """Return the shared 50F weight prediction fixture.

    Returns:
        Keyword arguments accepted by the selector and static predictor.
    """
    return {
        "weight_kg": 68.0,
        "height_cm": 160.0,
        "age": 50,
        "sex": "female",
        "daily_steps": 6500,
        "daily_intake_kcal": 1500.0,
        "periods_days": [7, 30, 90],
    }


def test_selector_default_matches_static_7step_response() -> None:
    """Verify the selector is API-compatible by default."""
    kwargs = _base_kwargs()

    selected = predict_weight_periods_selected(**kwargs)
    static = predict_weight_periods(**kwargs)

    assert selected == static


def test_selector_feature_flag_false_forces_static_even_when_engine_is_hall() -> None:
    """Verify Hall-lite cannot run when the feature flag is disabled."""
    kwargs = _base_kwargs()

    selected = predict_weight_periods_selected(
        **kwargs,
        feature_hall_lite_weight_prediction=False,
        weight_prediction_engine=WeightPredictionEngine.HALL_LITE,
    )
    static = predict_weight_periods(**kwargs)

    assert selected == static


def test_selector_static_engine_forces_static_when_feature_enabled() -> None:
    """Verify explicit static engine preserves existing fallback behavior."""
    kwargs = _base_kwargs()

    selected = predict_weight_periods_selected(
        **kwargs,
        feature_hall_lite_weight_prediction=True,
        weight_prediction_engine=WeightPredictionEngine.STATIC_7STEP,
    )
    static = predict_weight_periods(**kwargs)

    assert selected == static


def test_selector_auto_uses_hall_only_for_long_term_candidate() -> None:
    """Verify auto mode keeps short periods static and upgrades long periods."""
    kwargs = _base_kwargs()

    selected = predict_weight_periods_selected(
        **kwargs,
        feature_hall_lite_weight_prediction=True,
        weight_prediction_engine=WeightPredictionEngine.AUTO,
    )
    static = predict_weight_periods(**kwargs)

    assert selected.predictions[0] == static.predictions[0]
    assert selected.predictions[1] == static.predictions[1]
    assert selected.predictions[2].warning == HALL_LITE_WARNING
    assert selected.predictions[2].predicted_weight_kg != static.predictions[2].predicted_weight_kg


def test_selector_underage_falls_back_to_static() -> None:
    """Verify Hall-lite adult approximation is not used for underage inputs."""
    kwargs = _base_kwargs()
    kwargs["age"] = 17

    selected = predict_weight_periods_selected(
        **kwargs,
        feature_hall_lite_weight_prediction=True,
        weight_prediction_engine=WeightPredictionEngine.HALL_LITE,
    )
    static = predict_weight_periods(**kwargs)

    assert selected == static
