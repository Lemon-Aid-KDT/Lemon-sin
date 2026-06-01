"""Safe wording refinement for deterministic supplement impact previews."""

from __future__ import annotations

import json
from collections.abc import Mapping
from decimal import Decimal
from math import isfinite
from typing import Any

from pydantic import ValidationError

from src.config import Settings
from src.llm.ollama import (
    OllamaChatClient,
    OllamaClientError,
    OllamaConfigurationError,
    extract_ollama_message_content,
)
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.supplement_recommendation import (
    SupplementAnalysisExplainRequest,
    SupplementRecommendationExplainRequest,
    SupplementRecommendationExplainResponse,
)
from src.nutrition.deficiency_analysis import FORBIDDEN_TERMS, contains_forbidden_terms
from src.services.supplement_recommendation import SUPPLEMENT_IMPACT_DISCLAIMER

SUPPLEMENT_EXPLAIN_SYSTEM_PROMPT = """
You rewrite deterministic supplement impact results for a healthcare app.
Do not create new nutrition facts, risk labels, amounts, supplement names, or
medical claims. Do not tell the user to change a dose, treat a disease, diagnose
a condition, or change medication. Use only the provided deterministic preview.
Return only JSON matching the supplied schema.
""".strip()

SUPPLEMENT_ANALYSIS_EXPLAIN_SYSTEM_PROMPT = """
You explain a supplement OCR analysis preview for a healthcare app.
Use only the provided sanitized fields. Do not infer unseen ingredients, amounts,
risks, diagnoses, treatments, or dosage changes. Do not ask the user to change
medication. Return only JSON matching the supplied schema.
""".strip()
HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.6
MAX_SAFE_PROMPT_NUMBER = 1_000_000


class SupplementExplanationError(RuntimeError):
    """Raised when a supplement explanation cannot be safely generated."""


async def explain_supplement_recommendation(
    request: SupplementRecommendationExplainRequest,
    settings: Settings,
) -> SupplementRecommendationExplainResponse:
    """Return a safe explanation for a deterministic supplement impact preview.

    Args:
        request: Explanation request.
        settings: Runtime settings.

    Returns:
        Safe explanation response. If local LLM refinement is disabled or rejected,
        a deterministic fallback is returned.
    """
    fallback = build_deterministic_explanation(request, warnings=())
    if not request.use_local_llm:
        return fallback

    try:
        response = await _explain_with_local_ollama(request, settings)
    except (OllamaClientError, OllamaConfigurationError, SupplementExplanationError):
        return build_deterministic_explanation(request, warnings=("llm_explanation_unavailable",))
    return response


async def explain_supplement_analysis_preview(
    record: SupplementAnalysisRun,
    request: SupplementAnalysisExplainRequest,
    settings: Settings,
) -> SupplementRecommendationExplainResponse:
    """Return a safe explanation for an OCR analysis preview before registration.

    Args:
        record: Stored supplement analysis preview. Raw OCR text must not be present.
        request: Explanation options.
        settings: Runtime settings.

    Returns:
        Safe explanation response. If local LLM refinement is disabled or rejected,
        a deterministic fallback is returned.
    """
    fallback = build_deterministic_analysis_explanation(record, warnings=())
    if not request.use_local_llm:
        return fallback

    try:
        response = await _explain_analysis_with_local_ollama(record, settings)
    except (OllamaClientError, OllamaConfigurationError, SupplementExplanationError):
        return build_deterministic_analysis_explanation(
            record,
            warnings=("llm_explanation_unavailable",),
        )
    return response


def build_deterministic_explanation(
    request: SupplementRecommendationExplainRequest,
    *,
    warnings: tuple[str, ...],
) -> SupplementRecommendationExplainResponse:
    """Build an explanation without calling an LLM.

    Args:
        request: Explanation request.
        warnings: Safe warning strings.

    Returns:
        Deterministic explanation response.
    """
    preview = request.preview
    bullets: list[str] = []
    if preview.current_supplement_contributions:
        bullets.append(
            f"계산된 보충제 영양소는 {len(preview.current_supplement_contributions)}종입니다."
        )
    if preview.deficiency_support_candidates:
        bullets.append(
            f"낮은 섭취로 표시된 영양소와 겹치는 항목이 "
            f"{len(preview.deficiency_support_candidates)}종 있습니다."
        )
    if preview.excess_or_duplicate_risks:
        bullets.append(
            f"중복 또는 상한 확인이 필요한 항목이 "
            f"{len(preview.excess_or_duplicate_risks)}종 있습니다."
        )
    if preview.missing_profile_fields:
        bullets.append("나이, 성별, 생애주기 같은 개인화 입력 확인이 필요합니다.")
    if not bullets:
        bullets.append("현재 입력 기준으로 표시할 추가 보충제 영향 항목이 없습니다.")

    response = SupplementRecommendationExplainResponse(
        safe_user_message=preview.safe_user_message,
        explanation_bullets=bullets[:6],
        clinical_disclaimer=SUPPLEMENT_IMPACT_DISCLAIMER,
        blocked_terms_detected=[],
        llm_used=False,
        warnings=list(warnings),
    )
    _reject_forbidden_response(response)
    return response


def build_deterministic_analysis_explanation(
    record: SupplementAnalysisRun,
    *,
    warnings: tuple[str, ...],
) -> SupplementRecommendationExplainResponse:
    """Build a pre-registration analysis explanation without calling an LLM.

    Args:
        record: Stored supplement analysis preview.
        warnings: Safe warning strings.

    Returns:
        Deterministic explanation response.
    """
    context = _build_analysis_explanation_context(record)
    ingredient_count = int(context["ingredient_count"])
    missing_sections = list(context["missing_required_sections"])
    bullets: list[str] = []

    product_name = context["product_name"]
    if isinstance(product_name, str) and product_name:
        bullets.append(f"제품명 후보는 {product_name}입니다.")
    else:
        bullets.append("제품명은 라벨을 보며 직접 확인해야 합니다.")

    ingredient_summary = _format_context_ingredients(context["ingredients"])
    if ingredient_count and ingredient_summary:
        bullets.append(
            f"성분 후보 {ingredient_count}개: {ingredient_summary}를 등록 전 검토하세요."
        )
    elif ingredient_count:
        bullets.append(f"성분 후보 {ingredient_count}개를 등록 전 검토하세요.")
    else:
        bullets.append("성분 후보가 비어 있어 수동 입력이나 추가 사진이 필요합니다.")

    intake_method = _mapping(context["intake_method"])
    intake_text = intake_method.get("text")
    if isinstance(intake_text, str) and intake_text:
        bullets.append(f"섭취 방법 후보: {intake_text}")
    elif context["intake_method_present"]:
        bullets.append("섭취 방법 후보가 있어 저장 전 빈도와 1회량을 확인할 수 있습니다.")
    else:
        bullets.append("섭취 방법은 아직 충분하지 않아 직접 확인이 필요합니다.")

    if context["precaution_count"]:
        bullets.append(f"주의 문구 후보 {context['precaution_count']}개가 있습니다.")
    if context["functional_claim_count"]:
        bullets.append(f"기능성 문구 후보 {context['functional_claim_count']}개가 있습니다.")
    if missing_sections:
        bullets.append(f"추가 확인 섹션: {', '.join(missing_sections[:4])}")

    message = (
        "등록 전 라벨 분석 결과를 확인하세요."
        if ingredient_count
        else "성분 후보가 부족해 제품명과 성분을 직접 확인해야 합니다."
    )
    response = SupplementRecommendationExplainResponse(
        safe_user_message=message,
        explanation_bullets=bullets[:6],
        clinical_disclaimer=SUPPLEMENT_IMPACT_DISCLAIMER,
        blocked_terms_detected=[],
        llm_used=False,
        warnings=list(warnings),
    )
    _reject_forbidden_response(response)
    return response


async def _explain_with_local_ollama(
    request: SupplementRecommendationExplainRequest,
    settings: Settings,
) -> SupplementRecommendationExplainResponse:
    """Call local Ollama for schema-constrained wording refinement.

    Args:
        request: Explanation request.
        settings: Runtime settings.

    Returns:
        Validated safe explanation response.

    Raises:
        OllamaClientError: If the local API call fails.
        SupplementExplanationError: If the output is unsafe or schema-invalid.
    """
    payload = _build_explanation_payload(request, settings)
    data = await OllamaChatClient(settings).post_chat(payload)
    content = extract_ollama_message_content(data)
    try:
        response = SupplementRecommendationExplainResponse.model_validate_json(content)
    except ValidationError as exc:
        raise SupplementExplanationError("Local explanation output failed validation.") from exc
    response.clinical_disclaimer = SUPPLEMENT_IMPACT_DISCLAIMER
    response.llm_used = True
    _reject_forbidden_response(response)
    return response


async def _explain_analysis_with_local_ollama(
    record: SupplementAnalysisRun,
    settings: Settings,
) -> SupplementRecommendationExplainResponse:
    """Call local Ollama for a pre-registration analysis explanation.

    Args:
        record: Stored supplement analysis preview.
        settings: Runtime settings.

    Returns:
        Validated safe explanation response.

    Raises:
        OllamaClientError: If the local API call fails.
        SupplementExplanationError: If the output is unsafe or schema-invalid.
    """
    payload = _build_analysis_explanation_payload(record, settings)
    data = await OllamaChatClient(settings).post_chat(payload)
    content = extract_ollama_message_content(data)
    try:
        response = SupplementRecommendationExplainResponse.model_validate_json(content)
    except ValidationError as exc:
        raise SupplementExplanationError(
            "Local analysis explanation output failed validation."
        ) from exc
    response.clinical_disclaimer = SUPPLEMENT_IMPACT_DISCLAIMER
    response.llm_used = True
    _reject_forbidden_response(response)
    return response


def _build_explanation_payload(
    request: SupplementRecommendationExplainRequest,
    settings: Settings,
) -> dict[str, Any]:
    """Build an Ollama Chat payload for safe explanation.

    Args:
        request: Explanation request.
        settings: Runtime settings.

    Returns:
        Ollama chat payload.
    """
    schema = SupplementRecommendationExplainResponse.model_json_schema()
    preview_json = request.preview.model_dump_json()
    user_prompt = (
        "Rewrite the deterministic supplement impact preview in concise Korean. "
        "Do not change any action labels, reason codes, nutrient amounts, or counts. "
        "Do not add new supplement or disease facts. Return JSON that conforms to "
        "the schema.\n\n"
        "<deterministic_preview>\n"
        f"{preview_json}\n"
        "</deterministic_preview>\n\n"
        "JSON Schema:\n"
        f"{json.dumps(schema, ensure_ascii=False)}"
    )
    return {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": SUPPLEMENT_EXPLAIN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "think": False,
        "format": schema,
        "options": {"temperature": 0},
    }


def _build_analysis_explanation_payload(
    record: SupplementAnalysisRun,
    settings: Settings,
) -> dict[str, Any]:
    """Build an Ollama Chat payload from sanitized analysis fields only.

    Args:
        record: Stored supplement analysis preview.
        settings: Runtime settings.

    Returns:
        Ollama chat payload.
    """
    schema = SupplementRecommendationExplainResponse.model_json_schema()
    context = _build_analysis_explanation_context(record)
    context_json = json.dumps(context, ensure_ascii=False)
    user_prompt = (
        "Rewrite this supplement label analysis preview in concise Korean. "
        "Use only the sanitized OCR-derived fields in the JSON context. "
        "Restate ingredient names and amounts only from the provided "
        "ingredients[].amount_text values. Do not add new ingredients, amounts, "
        "product claims, medical risks, or advice. "
        "Return JSON that conforms to the schema.\n\n"
        "<analysis_preview_context>\n"
        f"{context_json}\n"
        "</analysis_preview_context>\n\n"
        "JSON Schema:\n"
        f"{json.dumps(schema, ensure_ascii=False)}"
    )
    return {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": SUPPLEMENT_ANALYSIS_EXPLAIN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "think": False,
        "format": schema,
        "options": {"temperature": 0},
    }


def _build_analysis_explanation_context(record: SupplementAnalysisRun) -> dict[str, Any]:
    """Build bounded fields safe to send to the local explanation model.

    Args:
        record: Stored supplement analysis preview.

    Returns:
        Sanitized analysis context without raw OCR text, image bytes, object URIs,
        or provider payloads.
    """
    snapshot = _mapping(record.parsed_snapshot)
    parsed_product = _mapping(snapshot.get("parsed_product"))
    ingredient_candidates = _list_of_mappings(snapshot.get("ingredient_candidates"))
    intake_method = _mapping(snapshot.get("intake_method"))
    label_sections = _list_of_mappings(snapshot.get("label_sections"))
    precautions = _list_of_mappings(snapshot.get("precautions"))
    return {
        "status": _safe_text(record.status, limit=60),
        "ocr_provider": _safe_text(record.ocr_provider, limit=80),
        "ocr_confidence_bucket": _confidence_bucket(record.ocr_confidence),
        "product_name": _safe_text(parsed_product.get("product_name"), limit=120),
        "manufacturer": _safe_text(parsed_product.get("manufacturer"), limit=120),
        "ingredient_count": len(ingredient_candidates),
        "ingredients": [_ingredient_summary(candidate) for candidate in ingredient_candidates[:6]],
        "label_section_excerpts": [
            section
            for section in (_label_section_summary(section) for section in label_sections[:6])
            if section["text_excerpt"]
        ],
        "label_section_types": [
            _safe_text(section.get("section_type"), limit=80) for section in label_sections[:8]
        ],
        "intake_method": _intake_method_summary(intake_method),
        "intake_method_present": bool(intake_method),
        "precautions": [
            precaution
            for precaution in (_precaution_summary(item) for item in precautions[:4])
            if precaution["text"]
        ],
        "precaution_count": len(precautions),
        "functional_claim_count": len(_list_of_mappings(snapshot.get("functional_claims"))),
        "missing_required_sections": _safe_string_list(
            snapshot.get("missing_required_sections"),
            max_items=8,
            limit=80,
        ),
        "low_confidence_fields": _safe_string_list(
            snapshot.get("low_confidence_fields"),
            max_items=12,
            limit=80,
        ),
        "warnings": [
            _safe_text(warning, limit=140)
            for warning in list(record.warnings or [])[:6]
            if _safe_text(warning, limit=140)
        ],
    }


def _ingredient_summary(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Return bounded ingredient fields for explanation context.

    Args:
        candidate: Parsed ingredient candidate.

    Returns:
        Safe ingredient summary.
    """
    return {
        "display_name": _safe_text(candidate.get("display_name"), limit=120),
        "amount": _safe_number(candidate.get("amount")),
        "amount_text": _format_amount_text(candidate.get("amount"), candidate.get("unit")),
        "amount_present": candidate.get("amount") is not None,
        "unit": _safe_text(candidate.get("unit"), limit=40),
        "confidence_bucket": _confidence_bucket(candidate.get("confidence")),
    }


def _label_section_summary(section: Mapping[str, Any]) -> dict[str, str | None]:
    """Return a bounded OCR-derived label section excerpt.

    Args:
        section: Parsed label section mapping.

    Returns:
        Safe section type, heading, and bounded text excerpt.
    """
    return {
        "section_type": _safe_text(section.get("section_type"), limit=80),
        "heading_text": _safe_text(section.get("heading_text"), limit=120),
        "text_excerpt": _safe_text(section.get("text_bundle"), limit=220),
    }


def _intake_method_summary(intake_method: Mapping[str, Any]) -> dict[str, Any]:
    """Return bounded intake-method fields for explanation context.

    Args:
        intake_method: Parsed intake-method mapping.

    Returns:
        Safe intake-method summary.
    """
    structured = _mapping(intake_method.get("structured"))
    return {
        "text": _safe_text(intake_method.get("text"), limit=180),
        "frequency": _safe_text(structured.get("frequency"), limit=40),
        "times_per_day": _safe_number(structured.get("times_per_day")),
        "amount_per_time": _safe_number(structured.get("amount_per_time")),
        "amount_unit": _safe_text(structured.get("amount_unit"), limit=40),
    }


def _precaution_summary(precaution: Mapping[str, Any]) -> dict[str, str | None]:
    """Return a bounded precaution sentence for explanation context.

    Args:
        precaution: Parsed precaution mapping.

    Returns:
        Safe precaution summary.
    """
    return {
        "text": _safe_text(precaution.get("text"), limit=220),
        "category": _safe_text(precaution.get("category"), limit=80),
        "severity": _safe_text(precaution.get("severity"), limit=80),
    }


def _format_context_ingredients(value: Any) -> str:
    """Format sanitized ingredient summaries for deterministic user wording.

    Args:
        value: Ingredient summary list from the explanation context.

    Returns:
        Comma-separated safe ingredient and amount summary.
    """
    if not isinstance(value, list):
        return ""
    formatted: list[str] = []
    for item in value[:3]:
        if not isinstance(item, Mapping):
            continue
        display_name = item.get("display_name")
        if not isinstance(display_name, str) or not display_name:
            continue
        amount_text = item.get("amount_text")
        if isinstance(amount_text, str) and amount_text:
            formatted.append(f"{display_name} {amount_text}")
        else:
            formatted.append(f"{display_name} 함량 확인 필요")
    return ", ".join(formatted)


def _format_amount_text(amount: Any, unit: Any) -> str | None:
    """Return a display-safe ingredient amount string.

    Args:
        amount: Parsed numeric amount.
        unit: Parsed unit string.

    Returns:
        Bounded amount text, or None when amount is absent.
    """
    numeric = _safe_number(amount)
    if numeric is None:
        return None
    amount_text = str(numeric)
    normalized_unit = _safe_text(unit, limit=40)
    if normalized_unit:
        return f"{amount_text} {normalized_unit}"
    return amount_text


def _safe_number(value: Any) -> int | float | None:
    """Return a JSON-serializable number for safe prompt context.

    Args:
        value: Candidate numeric value.

    Returns:
        int or float when finite and reasonably bounded; otherwise None.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal | int | float):
        numeric = float(value)
    else:
        return None
    if not isfinite(numeric) or not -MAX_SAFE_PROMPT_NUMBER <= numeric <= MAX_SAFE_PROMPT_NUMBER:
        return None
    if numeric.is_integer():
        return int(numeric)
    return numeric


def _mapping(value: Any) -> Mapping[str, Any]:
    """Return value when it is a mapping, otherwise an empty mapping."""
    if isinstance(value, Mapping):
        return value
    return {}


def _list_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    """Return bounded mappings from a possibly invalid list value."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _safe_string_list(value: Any, *, max_items: int, limit: int) -> list[str]:
    """Return bounded non-empty strings from a possibly invalid list value."""
    if not isinstance(value, list):
        return []
    strings: list[str] = []
    for item in value:
        text = _safe_text(item, limit=limit)
        if text:
            strings.append(text)
        if len(strings) >= max_items:
            break
    return strings


def _safe_text(value: Any, *, limit: int) -> str | None:
    """Return a bounded string or None for non-string/empty values."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return text[:limit]


def _confidence_bucket(value: Any) -> str:
    """Return a coarse confidence bucket without exposing provider payloads."""
    if isinstance(value, Decimal | int | float):
        numeric = float(value)
    else:
        return "none"
    if numeric >= HIGH_CONFIDENCE_THRESHOLD:
        return "high"
    if numeric >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


def _reject_forbidden_response(response: SupplementRecommendationExplainResponse) -> None:
    """Reject forbidden wording from an explanation response.

    Args:
        response: Candidate explanation response.

    Raises:
        SupplementExplanationError: If a forbidden term is present.
    """
    messages = [
        response.safe_user_message,
        response.clinical_disclaimer,
        *response.explanation_bullets,
    ]
    blocked_terms = [term for term in FORBIDDEN_TERMS if any(term in text for text in messages)]
    if blocked_terms or contains_forbidden_terms(messages):
        response.blocked_terms_detected = blocked_terms
        raise SupplementExplanationError("Supplement explanation contains unsafe wording.")
