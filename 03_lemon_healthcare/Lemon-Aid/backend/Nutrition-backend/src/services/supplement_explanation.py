"""Safe wording refinement for deterministic supplement impact previews."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from src.config import Settings
from src.llm.ollama import (
    OllamaChatClient,
    OllamaClientError,
    OllamaConfigurationError,
    extract_ollama_message_content,
)
from src.models.schemas.supplement_recommendation import (
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
