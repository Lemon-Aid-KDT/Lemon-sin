"""통합 건강 요약 서비스 단위 테스트.

mock 사용자 + 하루 섭취로 기업 과제 Output(부족 영양소·섭취량 권고·체중 예측·
활동 권고)이 산출되는지, 기여도(충족률) 표시와 컴플라이언스를 검증한다.
"""

from __future__ import annotations

from src.models.schemas.algorithm import BMICategory
from src.models.schemas.nutrition import NutrientStatus
from src.models.schemas.user import UserProfile
from src.services.health_summary import build_health_summary

_FORBIDDEN = ("진단", "처방", "치료", "보장", "확실히")

# mock: 52세 남성, 168cm 78kg, 하루 7,200보
_USER = UserProfile(age=52, sex="male", height_cm=168, weight_kg=78.0)
_STEPS = 7200
# mock 하루 섭취(끼니 합산): 나트륨 과잉 + 칼슘·식이섬유·비타민 부족
_INTAKE = {
    "kcal": 1700.0,
    "protein_g": 45.0,
    "fiber_g": 12.0,
    "sodium_mg": 3500.0,
    "calcium_mg": 400.0,
    "iron_mg": 7.0,
    "vitamin_a_ug": 350.0,
    "vitamin_c_mg": 40.0,
}


class TestHealthSummaryOutputs:
    """4대 Output 산출."""

    def test_bmi_classified(self) -> None:
        """BMI 27.6 → 비만 1단계."""
        summary = build_health_summary(_USER, _STEPS, _INTAKE)
        assert summary.bmi == 27.6
        assert summary.bmi_category is BMICategory.OBESE_1

    def test_deficient_recommendations(self) -> None:
        """부족 영양소 4종(식이섬유·칼슘·비타민A·비타민C) + 보충 식품·부족분."""
        summary = build_health_summary(_USER, _STEPS, _INTAKE)
        codes = {c.code for c in summary.deficient_recommendations}
        assert codes == {"fiber_g", "calcium_mg", "vitamin_a_ug", "vitamin_c_mg"}
        for c in summary.deficient_recommendations:
            assert c.food_suggestion != ""
            assert c.shortfall_amount > 0

    def test_contribution_shows_fulfillment(self) -> None:
        """기여도(충족률)가 영양소별로 표시된다 (칼슘 ≈ 53%)."""
        summary = build_health_summary(_USER, _STEPS, _INTAKE)
        calcium = next(c for c in summary.nutrient_contributions if c.code == "calcium_mg")
        assert calcium.fulfillment_pct == 53.3
        assert "채웠어요" in calcium.message_ko

    def test_sodium_flagged_excess_not_deficient(self) -> None:
        """나트륨은 과잉(RISKY)이며 부족 추천에 포함되지 않는다."""
        summary = build_health_summary(_USER, _STEPS, _INTAKE)
        sodium = next(c for c in summary.nutrient_contributions if c.code == "sodium_mg")
        assert sodium.status is NutrientStatus.RISKY
        assert sodium.food_suggestion == ""
        assert "sodium_mg" not in {c.code for c in summary.deficient_recommendations}

    def test_weight_predictions_show_loss(self) -> None:
        """체중 예측 1주/1개월/3개월, 감량 추세."""
        summary = build_health_summary(_USER, _STEPS, _INTAKE)
        preds = summary.weight_predictions
        assert preds.month_1.predicted_weight < 78.0
        assert preds.month_3.predicted_weight < preds.month_1.predicted_weight

    def test_activity_advice(self) -> None:
        """권장 걸음수·부족분·v1 점수."""
        summary = build_health_summary(_USER, _STEPS, _INTAKE)
        assert summary.activity.recommended_steps == 7920
        assert summary.activity.step_gap == 720
        assert 0 <= summary.activity.v1_score <= 100


class TestCompliance:
    """의료적 단정 표현 차단."""

    def test_no_forbidden_terms_anywhere(self) -> None:
        """모든 사용자 노출 문구에 금지 표현 0건."""
        summary = build_health_summary(_USER, _STEPS, _INTAKE)
        messages = [summary.summary_message_ko, summary.activity.message_ko]
        messages += [c.message_ko for c in summary.nutrient_contributions]
        for message in messages:
            for term in _FORBIDDEN:
                assert term not in message
