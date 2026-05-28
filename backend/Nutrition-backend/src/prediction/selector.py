"""Safe model selector for weight prediction."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Final

from src.models.schemas.algorithm import WeightPredictionResponse, WeightPredictionStep
from src.models.schemas.user import Sex
from src.prediction.hall import HallLiteResult, predict_with_hall
from src.prediction.weight import KCAL_PER_KG_FAT, predict_weight_n_days, predict_weight_periods

LONG_TERM_HALL_CANDIDATE_DAYS: Final[int] = 90
HALL_LITE_MIN_AGE_YEARS: Final[int] = 18
ROUND_KCAL_DECIMALS: Final[int] = 1
ROUND_CHANGE_DECIMALS: Final[int] = 3
HALL_LITE_WARNING = "Hall-lite 동적 시뮬레이션 참고값입니다. 실제 체중 변화는 개인 상태와 측정 오차에 따라 달라질 수 있습니다."
MEDICAL_LIMITER_WARNING = (
    "갑상선 질환, 만성 콩팥병, 간질환, 스테로이드 복용, 당뇨 약물처럼 "
    "체중 변동에 큰 영향을 줄 수 있는 맥락에서는 장기 자동 예측을 낮은 신뢰도 "
    "참고값으로만 봐야 합니다."
)
MEDICAL_LIMITER_LONG_TERM_DAYS: Final[int] = 90
MEDICAL_LIMITER_TERMS: Final[frozenset[str]] = frozenset(
    {
        "thyroid",
        "thyroid_disease",
        "갑상선",
        "ckd",
        "chronic_kidney_disease",
        "kidney_disease",
        "콩팥",
        "신장질환",
        "liver",
        "liver_disease",
        "간질환",
        "steroid",
        "systemic_steroid",
        "스테로이드",
        "insulin",
        "sglt2",
        "glp1",
        "sulfonylurea",
        "diabetes_medication",
        "당뇨약",
    }
)


class WeightPredictionEngine(StrEnum):
    """Supported internal weight prediction engines.

    Attributes:
        STATIC_7STEP: Existing static 7-step fallback model.
        HALL_LITE: Hall-lite dynamic simulator.
        AUTO: Static model for short periods and Hall-lite for long-period candidates.
    """

    STATIC_7STEP = "static_7step"
    HALL_LITE = "hall_lite"
    AUTO = "auto"


def _coerce_engine(engine: str | WeightPredictionEngine) -> WeightPredictionEngine:
    """Coerce a settings value into a prediction engine enum.

    Args:
        engine: Raw engine value from settings or tests.

    Returns:
        Parsed prediction engine.

    Raises:
        ValueError: If the engine value is unsupported.
    """
    if isinstance(engine, WeightPredictionEngine):
        return engine
    return WeightPredictionEngine(engine)


def _should_use_hall_lite(
    *,
    feature_hall_lite_weight_prediction: bool,
    engine: WeightPredictionEngine,
    age: int,
    days: int,
) -> bool:
    """Decide whether a period should use Hall-lite.

    Args:
        feature_hall_lite_weight_prediction: Hall-lite feature flag.
        engine: Configured prediction engine.
        age: User age in years.
        days: Prediction period in days.

    Returns:
        True when Hall-lite is enabled and appropriate for the input.
    """
    if not feature_hall_lite_weight_prediction:
        return False
    if age < HALL_LITE_MIN_AGE_YEARS:
        return False
    if engine == WeightPredictionEngine.HALL_LITE:
        return True
    return engine == WeightPredictionEngine.AUTO and days >= LONG_TERM_HALL_CANDIDATE_DAYS


def _flatten_risk_context_values(risk_context: Mapping[str, object] | None) -> tuple[str, ...]:
    """Return normalized string tokens from a flexible risk context mapping."""
    if not risk_context:
        return ()

    values: list[str] = []
    for value in risk_context.values():
        if isinstance(value, str):
            values.append(value.casefold())
            continue
        if isinstance(value, list | tuple | set):
            values.extend(str(item).casefold() for item in value)
            continue
        if value is not None:
            values.append(str(value).casefold())
    return tuple(values)


def _has_medical_limiter(risk_context: Mapping[str, object] | None) -> bool:
    """Check whether long-term automatic weight prediction should be downgraded."""
    values = _flatten_risk_context_values(risk_context)
    return any(
        limiter in value or value in limiter
        for value in values
        for limiter in MEDICAL_LIMITER_TERMS
    )


def _with_medical_limiter_warnings(
    response: WeightPredictionResponse,
) -> WeightPredictionResponse:
    """Attach low-confidence warnings to long-term periods without changing schema."""
    return response.model_copy(
        update={
            "predictions": [
                step.model_copy(update={"warning": MEDICAL_LIMITER_WARNING})
                if step.days >= MEDICAL_LIMITER_LONG_TERM_DAYS
                else step
                for step in response.predictions
            ]
        }
    )


def _hall_result_to_weight_step(
    *,
    result: HallLiteResult,
    daily_intake_kcal: float,
    days: int,
) -> WeightPredictionStep:
    """Map an internal Hall-lite result to the existing response step shape.

    Args:
        result: Internal Hall-lite simulation result.
        daily_intake_kcal: Scenario intake in kcal/day.
        days: Prediction period in days.

    Returns:
        Existing API-compatible weight prediction step.
    """
    initial_daily_balance_kcal = daily_intake_kcal - result.initial_tdee_kcal
    initial_cumulative_balance_kcal = initial_daily_balance_kcal * days
    theoretical_change_kg = initial_cumulative_balance_kcal / KCAL_PER_KG_FAT

    return WeightPredictionStep(
        days=days,
        estimated_bmr=result.initial_bmr_kcal,
        estimated_tdee=result.initial_tdee_kcal,
        daily_balance_kcal=round(initial_daily_balance_kcal, ROUND_KCAL_DECIMALS),
        cumulative_balance_kcal=round(
            result.cumulative_energy_balance_kcal,
            ROUND_KCAL_DECIMALS,
        ),
        theoretical_change_kg=round(theoretical_change_kg, ROUND_CHANGE_DECIMALS),
        corrected_change_kg=round(result.weight_change_kg, ROUND_CHANGE_DECIMALS),
        predicted_weight_kg=result.predicted_weight_kg,
        warning=HALL_LITE_WARNING,
    )


def _predict_one_period(
    *,
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: Sex,
    daily_steps: int,
    daily_intake_kcal: float,
    days: int,
    feature_hall_lite_weight_prediction: bool,
    engine: WeightPredictionEngine,
) -> WeightPredictionStep:
    """Predict one period using Hall-lite when enabled, otherwise 7-step.

    Args:
        weight_kg: Current body weight in kilograms.
        height_cm: Height in centimeters.
        age: Age in years.
        sex: Biological sex accepted by the current algorithm schemas.
        daily_steps: Daily step count.
        daily_intake_kcal: Daily intake in kcal/day.
        days: Prediction period in days.
        feature_hall_lite_weight_prediction: Hall-lite feature flag.
        engine: Configured prediction engine.

    Returns:
        API-compatible weight prediction step.
    """
    if _should_use_hall_lite(
        feature_hall_lite_weight_prediction=feature_hall_lite_weight_prediction,
        engine=engine,
        age=age,
        days=days,
    ):
        try:
            result = predict_with_hall(
                weight_kg=weight_kg,
                height_cm=height_cm,
                age=age,
                sex=sex,
                daily_steps=daily_steps,
                daily_intake_kcal=daily_intake_kcal,
                n_days=days,
            )
            return _hall_result_to_weight_step(
                result=result,
                daily_intake_kcal=daily_intake_kcal,
                days=days,
            )
        except ValueError:
            pass

    return predict_weight_n_days(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        sex=sex,
        daily_steps=daily_steps,
        daily_intake_kcal=daily_intake_kcal,
        days=days,
    )


def predict_weight_periods_selected(
    *,
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: Sex,
    daily_steps: int,
    daily_intake_kcal: float,
    periods_days: list[int],
    feature_hall_lite_weight_prediction: bool = False,
    weight_prediction_engine: str | WeightPredictionEngine = WeightPredictionEngine.STATIC_7STEP,
    risk_context: Mapping[str, object] | None = None,
) -> WeightPredictionResponse:
    """Predict periods through the configured safe model selector.

    Args:
        weight_kg: Current body weight in kilograms.
        height_cm: Height in centimeters.
        age: Age in years.
        sex: Biological sex accepted by the current algorithm schemas.
        daily_steps: Daily step count.
        daily_intake_kcal: Daily intake in kcal/day.
        periods_days: Prediction periods in days.
        feature_hall_lite_weight_prediction: Hall-lite feature flag.
        weight_prediction_engine: Configured prediction engine.
        risk_context: Optional condition/medication context used only to downgrade
            long-term automatic predictions.

    Returns:
        Existing API-compatible response.

    Raises:
        ValueError: If the configured prediction engine is unsupported.
    """
    engine = _coerce_engine(weight_prediction_engine)
    if _has_medical_limiter(risk_context):
        static_response = predict_weight_periods(
            weight_kg=weight_kg,
            height_cm=height_cm,
            age=age,
            sex=sex,
            daily_steps=daily_steps,
            daily_intake_kcal=daily_intake_kcal,
            periods_days=periods_days,
        )
        return _with_medical_limiter_warnings(static_response)

    if not feature_hall_lite_weight_prediction or engine == WeightPredictionEngine.STATIC_7STEP:
        return predict_weight_periods(
            weight_kg=weight_kg,
            height_cm=height_cm,
            age=age,
            sex=sex,
            daily_steps=daily_steps,
            daily_intake_kcal=daily_intake_kcal,
            periods_days=periods_days,
        )

    predictions = [
        _predict_one_period(
            weight_kg=weight_kg,
            height_cm=height_cm,
            age=age,
            sex=sex,
            daily_steps=daily_steps,
            daily_intake_kcal=daily_intake_kcal,
            days=days,
            feature_hall_lite_weight_prediction=feature_hall_lite_weight_prediction,
            engine=engine,
        )
        for days in periods_days
    ]
    return WeightPredictionResponse(predictions=predictions)
