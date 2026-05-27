"""5-card 종합 분석 산출 로직.

OCR 으로 추출된 ingredient + 사용자 프로필을 받아 KDRIs 권장량/상한과 비교하고
만성질환 매트릭스(`chronic_disease_supplement_matrix.json`)와 교차하여 5-card
UI 의 5종 카드를 모두 채울 수 있는 데이터를 계산한다.

MVP 단계에서는 KDRIs 룩업을 inline static dict 로 처리하고, 추후 정식 KDRIs
모듈(`src/nutrition/kdris.py`)과 통합한다.

Reference:
    docs/Nutrition-docs/09-data-catalog.md (KDRIs)
    data/nutrition_reference/chronic_disease_supplement_matrix.json
"""

from __future__ import annotations

from typing import Literal, TypedDict

from src.models.schemas.chronic_disease_matrix import ChronicCondition
from src.models.schemas.supplement_comprehensive import (
    CautionaryComponent,
    ComprehensiveAnalysisRequest,
    ComprehensiveIngredient,
    DeficientNutrient,
    ExcessiveNutrient,
    PersonaTag,
    PurposeTarget,
    ScoreLabel,
    SupplementComprehensiveAnalysis,
    UserProfileInput,
)
from src.utils.chronic_disease_matrix import (
    category_to_conditions,
    load_matrix,
)

ALGORITHM_VERSION = "comprehensive-v1"
"""5-card 산출 로직 버전 (회귀 추적용)."""

_DEFICIT_NOISE_THRESHOLD = 0.05
"""5% 미만 부족은 노이즈로 무시한다."""

_MAX_NUTRIENTS_PER_CARD = 5
"""카드당 최대 항목 수 (UX: 한 화면에 너무 많은 정보 회피)."""

_SCORE_EXCELLENT = 90
_SCORE_GOOD = 75
_SCORE_MODERATE = 55
_SCORE_WARNING = 35
"""diet_score 라벨링 임계값."""

_SCORE_PENALTY_DEFICIENT = 5.0
_SCORE_PENALTY_EXCESSIVE = 8.0
_SCORE_PENALTY_CAUTION_HIGH = 12.0
_SCORE_PENALTY_CAUTION_MEDIUM = 6.0
_SCORE_PENALTY_CAUTION_LOW = 2.0
_PERSONA_B_CAUTION_WEIGHT = 1.2
"""diet_score 산출 가중치."""

_USER_CONDITION_BOOST = 0.15
"""사용자가 명시한 chronic_condition 의 relevance_score 가중치."""
_SMOKER_BETA_CAROTENE_WARNING_MG = 6.0
_VITAMIN_A_UL_UG = 3000.0
_AUDIT_KR_RISK_CUTOFF = 3
_AUDIT_KR_DEPENDENCE_MALE = 10
_AUDIT_KR_DEPENDENCE_FEMALE = 8
_HIGH_RISK_DRUGS = {
    "warfarin",
    "levothyroxine",
    "methotrexate",
    "chemo",
    "bisphosphonate",
    "maoi",
    "ssri",
    "statin",
    "metformin",
    "acetaminophen",
}


class _KdrisEntry:
    """KDRIs 단일 영양소 권장량/상한 (MVP inline 룩업)."""

    __slots__ = ("display_name", "recommended", "unit", "upper_limit")

    def __init__(
        self,
        display_name: str,
        unit: str,
        recommended: float,
        upper_limit: float,
    ) -> None:
        self.display_name = display_name
        self.unit = unit
        self.recommended = recommended
        self.upper_limit = upper_limit


# MVP: 핵심 영양소만 inline 등록. 추후 KDRIs 2020 풀 룩업으로 교체.
# 일반 성인 (19~64세) 기준값.
_KDRIS_TABLE: dict[str, _KdrisEntry] = {
    "vitamin_a_ug": _KdrisEntry("비타민 A", "ug", 750, 3000),
    "vitamin_b1_mg": _KdrisEntry("비타민 B1", "mg", 1.2, 1000),
    "vitamin_b6_mg": _KdrisEntry("비타민 B6", "mg", 1.4, 100),
    "vitamin_b12_ug": _KdrisEntry("비타민 B12", "ug", 2.4, 2000),
    "vitamin_c_mg": _KdrisEntry("비타민 C", "mg", 100, 2000),
    "vitamin_d_ug": _KdrisEntry("비타민 D", "ug", 10, 100),
    "vitamin_e_mg": _KdrisEntry("비타민 E", "mg", 12, 540),
    "vitamin_k_ug": _KdrisEntry("비타민 K", "ug", 75, 1000),
    "calcium_mg": _KdrisEntry("칼슘", "mg", 800, 2500),
    "magnesium_mg": _KdrisEntry("마그네슘", "mg", 350, 350),
    "iron_mg": _KdrisEntry("철분", "mg", 10, 45),
    "zinc_mg": _KdrisEntry("아연", "mg", 10, 35),
    "omega3_mg": _KdrisEntry("오메가-3", "mg", 1000, 3000),
}


def _compute_intake_by_code(
    ingredients: list[ComprehensiveIngredient],
) -> dict[str, tuple[float, str, str]]:
    """ingredient 리스트를 nutrient_code 별 (intake, unit, display_name) 으로 집계.

    같은 nutrient_code 가 여러 번 등장하면 amount 를 합산한다 (단위 충돌 시 첫 단위 유지).

    Args:
        ingredients: 요청에서 받은 ingredient 리스트.

    Returns:
        nutrient_code 키 → (총 섭취량, 단위, 표시명) 매핑.
    """
    aggregated: dict[str, list[float]] = {}
    metadata: dict[str, tuple[str, str]] = {}
    for ing in ingredients:
        if not ing.nutrient_code or ing.amount is None:
            continue
        aggregated.setdefault(ing.nutrient_code, []).append(ing.amount)
        metadata.setdefault(
            ing.nutrient_code,
            (ing.unit or "", ing.display_name),
        )
    return {
        code: (sum(values), metadata[code][0], metadata[code][1])
        for code, values in aggregated.items()
    }


def _compute_deficient(
    intake_by_code: dict[str, tuple[float, str, str]],
) -> list[DeficientNutrient]:
    """KDRIs 권장량 대비 부족 영양소를 산출한다."""
    deficient: list[DeficientNutrient] = []
    for code, kdris in _KDRIS_TABLE.items():
        current, _unit, display = intake_by_code.get(code, (0.0, kdris.unit, kdris.display_name))
        if current >= kdris.recommended:
            continue
        ratio = 1.0 - (current / kdris.recommended) if kdris.recommended > 0 else 0.0
        if ratio < _DEFICIT_NOISE_THRESHOLD:
            continue  # 5% 미만 부족은 노이즈로 간주
        deficient.append(
            DeficientNutrient(
                nutrient_code=code,
                display_name=display,
                current_intake=round(current, 2),
                recommended_intake=kdris.recommended,
                unit=kdris.unit,
                deficit_ratio=round(min(ratio, 1.0), 4),
            )
        )
    # 가장 부족한 순으로 정렬, 상위 5개만 반환
    deficient.sort(key=lambda d: d.deficit_ratio, reverse=True)
    return deficient[:_MAX_NUTRIENTS_PER_CARD]


def _compute_excessive(
    intake_by_code: dict[str, tuple[float, str, str]],
) -> list[ExcessiveNutrient]:
    """KDRIs 상한 대비 과다 섭취 영양소를 산출한다."""
    excessive: list[ExcessiveNutrient] = []
    for code, (current, _unit, display) in intake_by_code.items():
        kdris = _KDRIS_TABLE.get(code)
        if kdris is None or kdris.upper_limit <= 0:
            continue
        if current <= kdris.upper_limit:
            continue
        ratio = current / kdris.upper_limit
        excessive.append(
            ExcessiveNutrient(
                nutrient_code=code,
                display_name=display,
                current_intake=round(current, 2),
                upper_limit=kdris.upper_limit,
                unit=kdris.unit,
                excess_ratio=round(ratio, 2),
            )
        )
    excessive.sort(key=lambda e: e.excess_ratio, reverse=True)
    return excessive[:5]


def _ingredient_to_category_hint(display_name: str) -> str | None:
    """ingredient display_name 으로 chronic disease matrix 의 카테고리 키를 추정한다.

    MVP: 단순 substring 매칭. 추후 nutrient_code → matrix 카테고리 정식 매핑으로 교체.
    """
    text = display_name.casefold()
    candidates = [
        ("오메가3", ["omega", "오메가", "epa", "dha", "fish oil"]),
        ("코엔자임Q10", ["coenzyme", "coq10", "ubiquinol", "유비퀴놀"]),
        ("혈관_낫토_폴리코사놀", ["폴리코사놀", "policosanol", "낫토", "natto"]),
        ("식이섬유", ["식이섬유", "fiber", "psyllium", "차전자"]),
        ("비타민D", ["비타민 d", "vitamin d", "vitamin_d"]),
        ("비타민K", ["비타민 k", "vitamin k", "vitamin_k"]),
        ("마그네슘", ["마그네슘", "magnesium"]),
        ("강황_커큐민", ["강황", "커큐민", "curcumin", "turmeric"]),
        ("칼슘", ["칼슘", "calcium"]),
        ("밀크씨슬_간", ["밀크씨슬", "milk thistle", "silymarin", "실리마린"]),
        ("뇌_은행잎", ["은행잎", "ginkgo"]),
        ("수면_멜라토닌", ["멜라토닌", "melatonin"]),
        ("스트레스_아쉬와간다", ["아쉬와간다", "ashwagandha"]),
        ("아르기닌_시트룰린", ["아르기닌", "arginine", "시트룰린", "citrulline"]),
        ("비타민B", ["비타민 b", "vitamin b", "thiamin", "리보플라빈"]),
        ("비타민C", ["비타민 c", "vitamin c"]),
        ("유산균_프로바이오틱", ["유산균", "프로바이오틱", "lactobacillus", "bifido"]),
        ("철분", ["철분", "iron", "철"]),
        ("아연", ["아연", "zinc"]),
        ("루테인_눈", ["루테인", "lutein"]),
    ]
    for category, keywords in candidates:
        if any(k in text for k in keywords):
            return category
    return None


class _ConditionInfo(TypedDict):
    """`_compute_chronic_indications_and_targets` 내부 임시 매핑."""

    evidence_level: str
    notes: str
    category: str


def _compute_chronic_indications_and_targets(
    ingredients: list[ComprehensiveIngredient],
    user: UserProfileInput,
) -> tuple[list[ChronicCondition], list[PurposeTarget]]:
    """매트릭스를 통해 chronic_disease_indications + purpose_targets 산출."""
    matrix = load_matrix()
    seen_conditions: dict[ChronicCondition, _ConditionInfo] = {}
    for ing in ingredients:
        category = _ingredient_to_category_hint(ing.display_name)
        if category is None:
            continue
        for target in category_to_conditions(category, matrix=matrix, min_evidence="weak"):
            existing = seen_conditions.get(target.condition)
            if existing is None or _evidence_rank(target.evidence_level) > _evidence_rank(
                existing["evidence_level"]
            ):
                seen_conditions[target.condition] = _ConditionInfo(
                    evidence_level=target.evidence_level,
                    notes=target.notes,
                    category=category,
                )

    indications: list[ChronicCondition] = sorted(seen_conditions.keys())

    purpose_targets: list[PurposeTarget] = []
    for condition, info in seen_conditions.items():
        relevance = _RELEVANCE_BY_EVIDENCE.get(info["evidence_level"], 0.3)
        is_user_target = condition in user.chronic_conditions
        if is_user_target:
            relevance = min(1.0, relevance + 0.15)
        message = _build_purpose_message(condition, info["evidence_level"], is_user_target)
        evidence_level_value = info["evidence_level"]
        assert evidence_level_value in {"strong", "moderate", "weak", "insufficient"}
        purpose_targets.append(
            PurposeTarget(
                condition=condition,
                relevance_score=round(relevance, 2),
                evidence_level=evidence_level_value,  # type: ignore[arg-type]
                message=message,
            )
        )
    purpose_targets.sort(key=lambda t: t.relevance_score, reverse=True)
    return indications, purpose_targets


_RELEVANCE_BY_EVIDENCE: dict[str, float] = {
    "strong": 0.85,
    "moderate": 0.65,
    "weak": 0.4,
    "insufficient": 0.2,
}


def _evidence_rank(level: str) -> int:
    """증거 등급의 정수 순위."""
    order = {"insufficient": 0, "weak": 1, "moderate": 2, "strong": 3}
    return order.get(level, 0)


def _build_purpose_message(
    condition: ChronicCondition,
    evidence_level: str,
    is_user_target: bool,
) -> str:
    """만성질환별 한국어 안내문."""
    condition_label = _CONDITION_LABELS.get(condition, condition)
    evidence_label = _EVIDENCE_LABELS.get(evidence_level, evidence_level)
    if is_user_target:
        return f"{condition_label} 관리에 ({evidence_label}) 도움이 될 수 있어요."
    return f"{condition_label}에 대한 효능은 {evidence_label} 단계 근거가 있어요."


_CONDITION_LABELS: dict[str, str] = {
    "diabetes": "당뇨 관련 영양 균형",
    "hypertension": "고혈압 관련 영양 균형",
    "dyslipidemia": "이상지질혈증 관련 영양 균형",
    "cardiovascular": "심혈관 건강",
    "osteoporosis": "골다공증·뼈 건강",
    "chronic_kidney_disease": "신장 기능 보조",
    "liver_disease": "간 건강",
    "cognitive_decline": "인지·기억 건강",
}

_EVIDENCE_LABELS: dict[str, str] = {
    "strong": "강한 근거",
    "moderate": "중간 근거",
    "weak": "제한적 근거",
    "insufficient": "근거 부족",
}


def _compute_cautions(
    ingredients: list[ComprehensiveIngredient],
    user: UserProfileInput,
) -> list[CautionaryComponent]:
    """매트릭스의 cautions 필드와 사용자 만성질환을 교차해 주의 성분 산출."""
    matrix = load_matrix()
    seen: list[CautionaryComponent] = []
    for ing in ingredients:
        category = _ingredient_to_category_hint(ing.display_name)
        if category is None:
            continue
        profile = matrix.categories.get(category)
        if profile is None:
            continue
        for caution in profile.cautions:
            severity: Literal["low", "medium", "high"] = "medium"
            if any(
                token in caution.lower()
                for token in ("출혈", "bleeding", "fatal", "심각", "회피", "절대")
            ):
                severity = "high"
            elif any(
                token in caution.lower() for token in ("주의", "monitor", "상호작용", "interaction")
            ):
                severity = "medium"
            else:
                severity = "low"
            seen.append(
                CautionaryComponent(
                    component=f"{ing.display_name} ({category})",
                    reason=caution,
                    severity=severity,
                    message=_format_caution_message(caution, ing.display_name),
                )
            )
        # 회피 권장 페르소나일 때 추가 경고
        if profile.persona_recommendation in {"avoid_for_chronic", "avoid_for_ckd"}:
            seen.append(
                CautionaryComponent(
                    component=ing.display_name,
                    reason=f"persona_avoid:{profile.persona_recommendation}",
                    severity="high",
                    message=f"{ing.display_name}은(는) 만성질환자에게 일반적으로 권장되지 않아요.",
                )
            )

    seen.extend(_compute_profile_safety_cautions(ingredients, user))
    return seen[:5]


def _compute_profile_safety_cautions(
    ingredients: list[ComprehensiveIngredient],
    user: UserProfileInput,
) -> list[CautionaryComponent]:
    """사용자 흡연·음주·약물 프로필 기반 P0 안전 경고를 산출한다.

    Args:
        ingredients: 분석 대상 성분.
        user: 사용자 프로필.

    Returns:
        추가 안전 경고 목록.
    """
    cautions: list[CautionaryComponent] = []
    is_smoker = user.smoking_status in {"former_lt_1y", "current_light", "current_heavy"}
    has_alcohol_risk = (
        user.audit_kr_score is not None and user.audit_kr_score >= _AUDIT_KR_RISK_CUTOFF
    )
    medication_codes = {medication.casefold() for medication in user.medications}

    for ingredient in ingredients:
        code = (ingredient.nutrient_code or "").casefold()
        name = ingredient.display_name.casefold()
        amount = ingredient.amount or 0.0

        is_beta_carotene = "beta" in name or "베타카로틴" in name or "beta_carotene" in code
        is_vitamin_a = code == "vitamin_a_ug" or "vitamin a" in name or "비타민 a" in name
        if is_smoker and (
            (is_beta_carotene and amount >= _SMOKER_BETA_CAROTENE_WARNING_MG)
            or (is_vitamin_a and amount >= _VITAMIN_A_UL_UG)
        ):
            cautions.append(
                CautionaryComponent(
                    component=ingredient.display_name,
                    reason="smoker_beta_carotene_vitamin_a_risk",
                    severity="high",
                    message=(
                        f"{ingredient.display_name}: 흡연자는 베타카로틴 또는 고함량 비타민 A "
                        "보충제 섭취 전 전문가 상담이 필요합니다."
                    ),
                )
            )

        if has_alcohol_risk and is_vitamin_a and amount >= _VITAMIN_A_UL_UG:
            cautions.append(
                CautionaryComponent(
                    component=ingredient.display_name,
                    reason="alcohol_vitamin_a_liver_risk",
                    severity="high",
                    message=f"{ingredient.display_name}: 음주 위험이 있으면 고함량 비타민 A는 간 안전성 확인이 필요합니다.",
                )
            )

    if has_alcohol_risk and "acetaminophen" in medication_codes:
        cautions.append(
            CautionaryComponent(
                component="acetaminophen",
                reason="alcohol_acetaminophen_liver_risk",
                severity="high",
                message="음주 위험이 있으면 아세트아미노펜 성분 약물과 보충제 선택 전 전문가 상담이 필요합니다.",
            )
        )

    if medication_codes & _HIGH_RISK_DRUGS:
        cautions.append(
            CautionaryComponent(
                component="user_medications",
                reason="drug_supplement_interaction_review",
                severity="high",
                message="입력된 약물과 보충제 간 상호작용 가능성이 있어 약사 또는 의사 상담을 권장합니다.",
            )
        )

    if user.audit_kr_score is not None:
        dependence_cutoff = (
            _AUDIT_KR_DEPENDENCE_MALE if user.sex == "male" else _AUDIT_KR_DEPENDENCE_FEMALE
        )
        if user.audit_kr_score >= dependence_cutoff:
            cautions.append(
                CautionaryComponent(
                    component="audit_kr",
                    reason="audit_kr_dependence_cutoff",
                    severity="high",
                    message="AUDIT-KR 점수가 높아 영양제 선택보다 전문 상담 연결이 우선입니다.",
                )
            )

    return cautions


def _format_caution_message(caution_token: str, display_name: str) -> str:
    """매트릭스의 raw caution 문자열을 한국어 사용자 친화 메시지로 변환."""
    mapping: dict[str, str] = {
        "high_dose_atrial_fibrillation_risk": "고용량 시 부정맥 위험이 있어요.",
        "anticoagulant_bleeding_risk": "항응고제(와파린 등) 복용 시 출혈 위험이 커요.",
        "drug_interaction:warfarin": "와파린(혈액 응고 억제제) 복용 시 효능에 영향이 있어요.",
    }
    msg = mapping.get(caution_token)
    if msg:
        return f"{display_name}: {msg}"
    # token 형식 cleanup
    cleaned = caution_token.replace("_", " ").replace(":", " — ")
    return f"{display_name}: {cleaned}"


def _compute_diet_score(
    deficient: list[DeficientNutrient],
    excessive: list[ExcessiveNutrient],
    cautions: list[CautionaryComponent],
    persona: PersonaTag,
) -> tuple[int, ScoreLabel, str]:
    """간단한 가중치 기반 식단/영양제 점수 (0~100).

    Baseline 100 에서 deficient(-5), excessive(-8), high-severity caution(-12),
    medium-severity caution(-6) 만큼 감점한다. 페르소나 B 는 만성질환자라 caution
    영향이 더 크다 (가중치 1.2x).
    """
    score = 100.0
    score -= 5.0 * len(deficient)
    score -= 8.0 * len(excessive)
    caution_weight = 1.2 if persona == "B" else 1.0
    for caution in cautions:
        if caution.severity == "high":
            score -= 12.0 * caution_weight
        elif caution.severity == "medium":
            score -= 6.0 * caution_weight
        else:
            score -= 2.0 * caution_weight
    score = max(0.0, min(100.0, score))
    final = round(score)
    label, message = _score_to_label(final, persona)
    return final, label, message


def _score_to_label(score: int, persona: PersonaTag) -> tuple[ScoreLabel, str]:
    """점수 → 라벨 + 한국어 메시지."""
    if score >= _SCORE_EXCELLENT:
        return "excellent", "균형 잡힌 선택이에요. 잘하고 있어요!"
    if score >= _SCORE_GOOD:
        return "good", "양호한 구성이에요. 일부 영양소만 보완해보세요."
    if score >= _SCORE_MODERATE:
        return "moderate", "보완이 필요한 영양소가 보여요. 가이드를 확인해주세요."
    if score >= _SCORE_WARNING:
        persona_extra = " 만성질환자에게는 권장 구성이 아니에요." if persona == "B" else ""
        return "warning", f"주의가 필요한 항목이 많아요.{persona_extra}"
    persona_extra = "" if persona == "A" else " 전문가 상담을 권장해요."
    return "critical", f"전반적 검토가 필요해요.{persona_extra}"


def compute_comprehensive(
    request: ComprehensiveAnalysisRequest,
) -> SupplementComprehensiveAnalysis:
    """요청을 받아 5-card 종합 분석을 산출한다.

    Args:
        request: 검증된 요청 본문.

    Returns:
        모든 카드를 채울 수 있는 종합 분석 결과.
    """
    warnings: list[str] = []
    intake_by_code = _compute_intake_by_code(request.ingredients)
    if not intake_by_code:
        warnings.append("no_recognized_nutrient_codes")
    dependence_cutoff = (
        _AUDIT_KR_DEPENDENCE_MALE
        if request.user_profile.sex == "male"
        else _AUDIT_KR_DEPENDENCE_FEMALE
    )
    if (
        request.user_profile.audit_kr_score is not None
        and request.user_profile.audit_kr_score >= dependence_cutoff
    ):
        warnings.append("supplement_recommendation_paused_audit_kr")

    deficient = _compute_deficient(intake_by_code)
    excessive = _compute_excessive(intake_by_code)
    cautions = _compute_cautions(request.ingredients, request.user_profile)
    indications, purpose_targets = _compute_chronic_indications_and_targets(
        request.ingredients,
        request.user_profile,
    )

    score, score_label, score_message = _compute_diet_score(
        deficient=deficient,
        excessive=excessive,
        cautions=cautions,
        persona=request.persona,
    )

    return SupplementComprehensiveAnalysis(
        analysis_id=request.analysis_id,
        persona=request.persona,
        deficient_nutrients=deficient,
        excessive_nutrients=excessive,
        cautionary_components=cautions,
        diet_score=score,
        diet_score_label=score_label,
        diet_score_message=score_message,
        purpose_targets=purpose_targets,
        chronic_disease_indications=indications,
        algorithm_version=ALGORITHM_VERSION,
        warnings=warnings,
    )
