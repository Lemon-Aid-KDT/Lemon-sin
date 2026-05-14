"""KDRIs 샘플 룩업과 영양 분석 테스트."""

from __future__ import annotations

import pytest

from src.models.schemas.nutrition import NutrientIntake, NutrientStatus
from src.models.schemas.user import UserProfile
from src.nutrition.deficiency_analysis import analyze_nutrient_intakes, contains_forbidden_terms
from src.nutrition.kdris import get_dataset_status, get_kdris_for_profile, lookup_kdris_reference
from src.nutrition.unit_converter import convert_amount


def test_kdris_sample_loads_30_major_nutrients() -> None:
    """성인 남성 기본 조건에서 30종 샘플 영양소를 로드한다."""
    references = get_kdris_for_profile(age=30, sex="male")

    assert len(references) == 30
    assert get_dataset_status() == "implementation_sample_not_official_reference_table"
    assert references[0].dataset_version == "2020-sample"
    assert references[0].source_manifest_version == "2.0"


def test_kdris_lookup_by_nutrient_code() -> None:
    """영양소 코드로 기준값을 조회한다."""
    reference = lookup_kdris_reference("vitamin_c_mg", age=30, sex="female")

    assert reference is not None
    assert reference.reference_amount == 100
    assert reference.reference_unit == "mg"


def test_pregnancy_specific_reference_overrides_baseline_only_for_matching_nutrient() -> None:
    """임신 조건에서는 특수 기준값이 있는 영양소만 baseline을 대체한다."""
    references = get_kdris_for_profile(age=30, sex="female", pregnancy_status="pregnant")
    by_code = {reference.nutrient_code: reference for reference in references}

    assert len(references) == 30
    assert by_code["vitamin_c_mg"].pregnancy_status == "pregnant"
    assert by_code["vitamin_c_mg"].reference_amount == 110
    assert by_code["protein_g"].pregnancy_status == "none"


def test_unit_conversion_supports_mass_and_vitamin_d_iu() -> None:
    """질량 단위와 비타민D IU 환산을 검증한다."""
    assert convert_amount(1, "g", "mg") == 1000
    assert convert_amount(1000, "ug", "mg") == 1
    assert convert_amount(400, "iu", "ug", nutrient_code="vitamin_d_ug") == 10


def test_nutrient_analysis_flags_deficient_and_risky() -> None:
    """비타민C 부족 가능성과 비타민A UL 초과 가능성을 분류한다."""
    profile = UserProfile(age=30, sex="male", height_cm=170, weight_kg=70)
    response = analyze_nutrient_intakes(
        profile=profile,
        intakes=[
            NutrientIntake(nutrient_code="vitamin_c_mg", amount=30, unit="mg"),
            NutrientIntake(nutrient_code="vitamin_a_ug", amount=5000, unit="ug"),
        ],
    )

    by_code = {result.nutrient_code: result for result in response.results}

    assert by_code["vitamin_c_mg"].status == NutrientStatus.DEFICIENT
    assert by_code["vitamin_c_mg"].reference_type == "RDA"
    assert by_code["vitamin_c_mg"].source_id == "local_kdris_2020_sample_fixture"
    assert by_code["vitamin_c_mg"].priority == 1
    assert by_code["vitamin_a_ug"].status == NutrientStatus.RISKY
    assert response.dataset_version == "2020-sample"
    assert response.source_manifest_version == "2.0"
    assert not contains_forbidden_terms([result.user_message for result in response.results])


def test_chronic_priority_boosts_only_low_or_deficient_nutrients() -> None:
    """만성질환 룩업은 이미 낮음/부족인 영양소의 확인 순서에만 반영한다."""
    profile = UserProfile(
        age=30,
        sex="male",
        height_cm=170,
        weight_kg=70,
        chronic_diseases=["htn"],
    )
    response = analyze_nutrient_intakes(
        profile=profile,
        intakes=[
            NutrientIntake(nutrient_code="vitamin_c_mg", amount=20, unit="mg"),
            NutrientIntake(nutrient_code="potassium_mg", amount=2000, unit="mg"),
            NutrientIntake(nutrient_code="magnesium_mg", amount=350, unit="mg"),
        ],
    )

    by_code = {result.nutrient_code: result for result in response.results}

    assert by_code["vitamin_c_mg"].status == NutrientStatus.DEFICIENT
    assert by_code["vitamin_c_mg"].ratio == 0.2
    assert by_code["vitamin_c_mg"].priority == 2
    assert by_code["potassium_mg"].status == NutrientStatus.LOW
    assert by_code["potassium_mg"].ratio == 0.57
    assert by_code["potassium_mg"].priority == 1
    assert by_code["potassium_mg"].priority_context == ["hypertension"]
    assert by_code["potassium_mg"].priority_source_ids == ["nhlbi_dash"]
    assert by_code["potassium_mg"].user_message == (
        "현재 입력과 만성질환 정보를 함께 볼 때 우선 확인 대상입니다."
    )
    assert by_code["magnesium_mg"].status == NutrientStatus.ADEQUATE
    assert by_code["magnesium_mg"].priority == 0
    assert by_code["magnesium_mg"].priority_context == []


def test_unknown_chronic_disease_keeps_ratio_based_priority() -> None:
    """미정의 만성질환 코드는 무시하고 기존 ratio 기반 우선순위를 유지한다."""
    profile = UserProfile(
        age=30,
        sex="male",
        height_cm=170,
        weight_kg=70,
        chronic_diseases=["unknown-condition"],
    )
    response = analyze_nutrient_intakes(
        profile=profile,
        intakes=[
            NutrientIntake(nutrient_code="vitamin_c_mg", amount=20, unit="mg"),
            NutrientIntake(nutrient_code="potassium_mg", amount=2000, unit="mg"),
        ],
    )

    by_code = {result.nutrient_code: result for result in response.results}

    assert by_code["vitamin_c_mg"].priority == 1
    assert by_code["potassium_mg"].priority == 2
    assert by_code["potassium_mg"].priority_context == []


def test_ckd_caution_nutrients_do_not_receive_priority_boost() -> None:
    """신장질환 주의 영양소는 자동으로 부족 우선순위를 올리지 않는다."""
    profile = UserProfile(
        age=30,
        sex="male",
        height_cm=170,
        weight_kg=70,
        chronic_diseases=["ckd"],
    )
    response = analyze_nutrient_intakes(
        profile=profile,
        intakes=[
            NutrientIntake(nutrient_code="vitamin_c_mg", amount=20, unit="mg"),
            NutrientIntake(nutrient_code="potassium_mg", amount=2000, unit="mg"),
        ],
    )

    by_code = {result.nutrient_code: result for result in response.results}

    assert by_code["vitamin_c_mg"].priority == 1
    assert by_code["potassium_mg"].priority == 2
    assert by_code["potassium_mg"].priority_context == []


def test_chronic_priority_messages_do_not_contain_forbidden_terms() -> None:
    """만성질환 우선 확인 문구가 치료·처방 표현을 포함하지 않는지 검증한다."""
    profile = UserProfile(
        age=30,
        sex="male",
        height_cm=170,
        weight_kg=70,
        chronic_diseases=["diabetes", "hypertension"],
    )
    response = analyze_nutrient_intakes(
        profile=profile,
        intakes=[
            NutrientIntake(nutrient_code="fiber_g", amount=10, unit="g"),
            NutrientIntake(nutrient_code="potassium_mg", amount=2000, unit="mg"),
        ],
    )

    messages = [result.user_message for result in response.results]
    assert all("우선 확인 대상" in result.user_message for result in response.results)
    assert not contains_forbidden_terms(messages)


def test_unknown_nutrient_reference_raises() -> None:
    """기준값이 없는 영양소는 명확한 오류로 처리한다."""
    profile = UserProfile(age=30, sex="male", height_cm=170, weight_kg=70)

    with pytest.raises(ValueError, match="KDRIs reference not found"):
        analyze_nutrient_intakes(
            profile=profile,
            intakes=[NutrientIntake(nutrient_code="unknown", amount=1, unit="mg")],
        )
