"""섭취 영양소 → KDRIs 권장 기준 대조 평가.

음식 인식 → 영양소 조회(`rda_matcher`)로 얻은 섭취 영양소를 사용자별 KDRIs
권장 기준과 대조하여, 영양소별 비율(%)·상태와 정보 문구를 만든다. 발표 슬라이드
"음식 → 영양소 → 한국영양학회 권장 기준과 대조"의 마지막 단계를 구현한다.

해석:
    - 단발 식사에 적용하면 각 비율은 "하루 권장량 대비 이 식사의 비중"이다.
    - 하루 합산 섭취에 적용하면 부족/적정/과잉 판단의 토대가 된다.

본 모듈의 사용자 노출 문구에는 의료적 단정 표현(진단/처방/치료/보장/확실히)을
포함하지 않는다.

Reference:
    docs/dev-guides/06-deficient-nutrient-diagnosis.md §상태 분류
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Final

from src.models.schemas.nutrition import (
    MealNutritionEvaluation,
    NutrientEvaluation,
    NutrientStatus,
    UserKDRIsContext,
)
from src.nutrition.kdris import lookup_kdris_for_user

logger = logging.getLogger(__name__)

DEFICIENT_THRESHOLD_PCT: Final[float] = 35.0
LOW_THRESHOLD_PCT: Final[float] = 70.0
ADEQUATE_UPPER_PCT: Final[float] = 130.0
"""상태 분류 임계값(%).

- 35% 미만: DEFICIENT
- 35% 이상 70% 미만: LOW
- 70% 이상 130% 이하: ADEQUATE
- 130% 초과(상한 이하): EXCESSIVE
- 상한(또는 과잉 경계) 초과: RISKY
"""

_STATUS_PRIORITY: Final[dict[NutrientStatus, int]] = {
    NutrientStatus.RISKY: 0,
    NutrientStatus.DEFICIENT: 1,
    NutrientStatus.LOW: 2,
    NutrientStatus.EXCESSIVE: 3,
    NutrientStatus.ADEQUATE: 4,
}
"""정렬 우선순위. 주의가 필요한 상태를 앞에 둔다."""

# rda_matcher가 내보내는 영양소 키 → KDRIs 표준 코드 매핑.
# 매핑에 없는 키(fat_g, carb_g 등)는 KDRIs 기준이 없어 평가에서 제외한다.
_NUTRIENT_CODE_MAP: Final[dict[str, str]] = {
    "kcal": "energy_kcal",
    "protein_g": "protein_g",
    "fiber_g": "fiber_g",
    "sodium_mg": "sodium_mg",
    "calcium_mg": "calcium_mg",
    "iron_mg": "iron_mg",
    "vitamin_a_ug": "vitamin_a_ug",
    "vitamin_c_mg": "vitamin_c_mg",
}

_FORBIDDEN_TERMS: Final[frozenset[str]] = frozenset({"진단", "처방", "치료", "보장", "확실히"})
"""사용자 노출 문구에 들어가면 안 되는 의료적 단정 표현."""

_LIMIT_NUTRIENTS: Final[frozenset[str]] = frozenset({"sodium_mg"})
"""한도형 영양소 — 적게 섭취할수록 바람직해 '부족'으로 보지 않는다.

나트륨처럼 기준값(AI)보다 적게 먹는 것이 문제되지 않는 영양소. 상한(과잉 경계)
초과만 주의(RISKY)로 보고, 그 이하는 모두 적정(ADEQUATE)으로 처리한다. 이런
영양소에는 '더 섭취하라'는 문구를 만들지 않는다.
"""


def classify_status(
    intake: float,
    reference: float | None,
    upper_limit: float | None,
    *,
    is_limit: bool = False,
) -> tuple[NutrientStatus, float]:
    """섭취량을 기준값 대비 비율로 평가하여 상태를 분류한다.

    Args:
        intake: 섭취량 (표준 단위).
        reference: 기준값(RDA 또는 AI). None이면 ADEQUATE로 처리.
        upper_limit: 상한(또는 과잉 경계) 값. None이면 RISKY 평가를 건너뛴다.
        is_limit: 한도형 영양소(나트륨 등) 여부. True면 상한 이하를 모두
            ADEQUATE로 보고 부족(DEFICIENT/LOW)으로 분류하지 않는다.

    Returns:
        (상태, 기준값 대비 비율%) 튜플. 비율은 소수점 1자리로 반올림한다.

    Examples:
        >>> classify_status(50.0, 100.0, 2000.0)
        (<NutrientStatus.LOW: 'low'>, 50.0)
        >>> classify_status(2500.0, 100.0, 2000.0)
        (<NutrientStatus.RISKY: 'risky'>, 2500.0)
        >>> classify_status(300.0, 1500.0, 2300.0, is_limit=True)
        (<NutrientStatus.ADEQUATE: 'adequate'>, 20.0)
    """
    if upper_limit is not None and intake > upper_limit:
        ratio = (intake / reference * 100.0) if reference else 0.0
        return (NutrientStatus.RISKY, round(ratio, 1))

    if reference is None or reference <= 0:
        return (NutrientStatus.ADEQUATE, 0.0)

    ratio = intake / reference * 100.0
    if is_limit:
        # 한도형: 상한 이하이면 비율과 무관하게 적정(부족 라벨 미적용).
        return (NutrientStatus.ADEQUATE, round(ratio, 1))

    if ratio < DEFICIENT_THRESHOLD_PCT:
        status = NutrientStatus.DEFICIENT
    elif ratio < LOW_THRESHOLD_PCT:
        status = NutrientStatus.LOW
    elif ratio <= ADEQUATE_UPPER_PCT:
        status = NutrientStatus.ADEQUATE
    else:
        status = NutrientStatus.EXCESSIVE
    return (status, round(ratio, 1))


def build_message(
    name_ko: str,
    status: NutrientStatus,
    ratio_pct: float,
    *,
    is_limit: bool = False,
) -> str:
    """상태에 맞는 정보 제공 문구를 생성한다.

    Args:
        name_ko: 영양소 한국어명.
        status: 섭취 상태.
        ratio_pct: 기준값 대비 비율(%).
        is_limit: 한도형 영양소 여부. True면 '더 섭취' 권유 문구를 만들지 않는다.

    Returns:
        사용자 노출용 한국어 문구.

    Raises:
        ValueError: 생성된 문구에 의료적 단정 표현이 포함된 경우.
    """
    pct = round(ratio_pct)
    if status is NutrientStatus.RISKY:
        message = f"{name_ko} 섭취량이 과잉 경계 기준을 넘었어요. 전문가와 상담을 권장해요."
    elif is_limit:
        message = f"{name_ko} 섭취량이 권장 한도 내({pct}% 수준)예요."
    elif status is NutrientStatus.DEFICIENT:
        message = f"{name_ko} 섭취량이 권장 기준의 {pct}% 수준이에요. {name_ko}이(가) 풍부한 식품을 더해보세요."
    elif status is NutrientStatus.LOW:
        message = f"{name_ko} 섭취량이 권장 기준의 {pct}% 수준이에요. 식단에 조금 더해보면 좋아요."
    elif status is NutrientStatus.ADEQUATE:
        message = f"{name_ko} 섭취량이 권장 기준의 {pct}% 수준으로 적정 범위예요."
    else:  # EXCESSIVE
        message = f"{name_ko} 섭취량이 권장 기준의 {pct}%로 다소 많아요. 양을 조절해보세요."

    found = [term for term in _FORBIDDEN_TERMS if term in message]
    if found:
        raise ValueError(f"forbidden medical term in message: {found}")
    return message


def evaluate_intake_against_kdris(
    intake: Mapping[str, float],
    user: UserKDRIsContext,
    rows: list[dict[str, str]] | None = None,
) -> MealNutritionEvaluation:
    """섭취 영양소를 KDRIs 권장 기준과 대조 평가한다.

    `intake`의 키는 ``rda_matcher``가 내보내는 영양소 키(예: "kcal",
    "calcium_mg")를 그대로 사용한다. KDRIs 기준이 없는 영양소(fat_g, carb_g
    등)와 사용자에 매칭되는 KDRIs 행이 없는 영양소는 평가에서 제외하고
    `skipped_codes`에 코드를 남긴다.

    Args:
        intake: 영양소 키 → 섭취량 매핑(표준 단위).
        user: 사용자 KDRIs 컨텍스트.
        rows: 미리 로드한 KDRIs 행. None이면 기본 경로에서 로드(캐시).

    Returns:
        상태 우선순위로 정렬된 `MealNutritionEvaluation`.

    Examples:
        >>> user = UserKDRIsContext(age=50, sex="female")
        >>> result = evaluate_intake_against_kdris({"calcium_mg": 800.0}, user)
        >>> result.evaluations[0].ratio_pct
        100.0
    """
    evaluations: list[NutrientEvaluation] = []
    skipped: list[str] = []

    for raw_code, amount in intake.items():
        kdris_code = _NUTRIENT_CODE_MAP.get(raw_code)
        if kdris_code is None:
            skipped.append(raw_code)
            continue
        kdris = lookup_kdris_for_user(kdris_code, user, rows=rows)
        if kdris is None:
            skipped.append(raw_code)
            continue

        reference = kdris.reference_value
        is_limit = kdris.code in _LIMIT_NUTRIENTS
        status, ratio_pct = classify_status(amount, reference, kdris.ul, is_limit=is_limit)
        evaluations.append(
            NutrientEvaluation(
                code=kdris.code,
                name_ko=kdris.name_ko,
                status=status,
                intake_amount=round(amount, 3),
                reference_amount=reference,
                ratio_pct=ratio_pct,
                unit=kdris.unit,
                upper_limit=kdris.ul,
                message_ko=build_message(kdris.name_ko, status, ratio_pct, is_limit=is_limit),
            )
        )

    evaluations.sort(key=lambda e: (_STATUS_PRIORITY[e.status], -e.ratio_pct))
    summary = _build_summary(evaluations)
    return MealNutritionEvaluation(
        evaluations=evaluations,
        evaluated_count=len(evaluations),
        skipped_codes=skipped,
        summary_message_ko=summary,
    )


def _build_summary(evaluations: list[NutrientEvaluation]) -> str:
    """평가 결과 요약 문구를 만든다.

    Args:
        evaluations: 영양소별 평가 리스트.

    Returns:
        요약 한국어 문구.
    """
    if not evaluations:
        return "KDRIs 권장 기준과 대조할 수 있는 영양소가 없어요."

    risky = sum(1 for e in evaluations if e.status is NutrientStatus.RISKY)
    short = sum(
        1 for e in evaluations if e.status in (NutrientStatus.DEFICIENT, NutrientStatus.LOW)
    )
    summary = f"권장 기준과 대조한 영양소 {len(evaluations)}종 중 부족 {short}종"
    if risky:
        summary += f", 과잉 경계 초과 {risky}종 — 전문가와 상담을 권장해요"
    return summary
