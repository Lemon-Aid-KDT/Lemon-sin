from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lemon_ai_agent.knowledge import (
    REVIEWED_MEDICAL_SOURCE_REGISTRY,
    ChatIntentAnalysis,
    Condition,
    MedicalKnowledgeItem,
    SourceFamily,
    SourceStatus,
    analyze_chat_intent,
    select_medical_knowledge,
)

Answerability = Literal[
    "answerable",
    "answerable_with_caution",
    "needs_more_info",
    "unknown_no_reviewed_source",
    "medical_decision_boundary",
    "urgent_escalation",
]

RetrievalStatus = Literal["found", "no_match", "stale_only", "not_reviewed_only"]


@dataclass(frozen=True)
class AnswerCard:
    card_id: str
    answerability: Answerability
    topic: str
    intent: str
    condition: Condition | None
    allowed_guidance: tuple[str, ...]
    specific_examples: tuple[str, ...]
    checklist: tuple[str, ...]
    caution_conditions: tuple[str, ...]
    must_not_say: tuple[str, ...]
    source_id: str
    source_url: str
    source_family: SourceFamily
    source_version_id: str | None
    version_label: str
    review_status: SourceStatus
    reviewed_at: str
    expires_at: str
    grounding_snippet_ids: tuple[str, ...]
    source_name: str
    concrete_guidance: str

    def source_metadata(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "source_family": self.source_family,
            "review_status": self.review_status,
            "version_label": self.version_label,
            "reviewed_at": self.reviewed_at,
            "expires_at": self.expires_at,
            "source_url": self.source_url,
        }


@dataclass(frozen=True)
class KnowledgeRetrievalResult:
    cards: tuple[AnswerCard, ...]
    knowledge_items: tuple[MedicalKnowledgeItem, ...]
    missing_topics: tuple[str, ...]
    warnings: tuple[str, ...]
    retrieval_status: RetrievalStatus


class AnswerCardNormalizer:
    """Converts reviewed seed knowledge into the runtime answer-card contract."""

    def from_medical_knowledge_item(
        self,
        item: MedicalKnowledgeItem,
        *,
        answerability: Answerability,
    ) -> AnswerCard | None:
        if item.reviewed_status != "reviewed" or item.evidence_type == "paper_candidate":
            return None

        source = _reviewed_source_by_id(item.source_id)
        if source is None or source.status != "reviewed" or not source.user_facing_allowed:
            return None

        if (
            not item.allowed_guidance
            or not item.specific_examples
            or not item.checklist
            or not item.must_not_say
            or not item.source_url
        ):
            return None

        source_family = _source_family_for_item(item, source.source_families)
        return AnswerCard(
            card_id=f"seed:{item.topic}",
            answerability=answerability,
            topic=item.topic,
            intent=item.intent,
            condition=item.condition,
            allowed_guidance=item.allowed_guidance,
            specific_examples=item.specific_examples,
            checklist=item.checklist,
            caution_conditions=item.caution_conditions,
            must_not_say=item.must_not_say,
            source_id=item.source_id,
            source_url=item.source_url,
            source_family=source_family,
            source_version_id=None,
            version_label=source.version_label,
            review_status=item.reviewed_status,
            reviewed_at=source.last_reviewed_at,
            expires_at=source.review_expires_at,
            grounding_snippet_ids=(f"seed:{item.topic}",),
            source_name=item.source,
            concrete_guidance=item.concrete_guidance,
        )


class MedicalKnowledgeRetriever:
    """Registry-backed v1 retriever for reviewed user-facing answer cards."""

    def __init__(self, normalizer: AnswerCardNormalizer | None = None) -> None:
        self._normalizer = normalizer or AnswerCardNormalizer()

    def retrieve(self, analysis: ChatIntentAnalysis) -> KnowledgeRetrievalResult:
        answerability = answerability_for_analysis(analysis, has_cards=True)
        selected_items = tuple(
            item
            for item in select_medical_knowledge(analysis)
            if _item_is_relevant_to_question(item, analysis.normalized_question, analysis)
        )
        cards = tuple(
            card
            for item in selected_items
            if (
                card := self._normalizer.from_medical_knowledge_item(
                    item,
                    answerability=answerability,
                )
            )
            is not None
        )

        if cards:
            return KnowledgeRetrievalResult(
                cards=cards,
                knowledge_items=selected_items,
                missing_topics=(),
                warnings=(),
                retrieval_status="found",
            )

        return KnowledgeRetrievalResult(
            cards=(),
            knowledge_items=(),
            missing_topics=(analysis.primary_intent,),
            warnings=("no_reviewed_answer_card",),
            retrieval_status="no_match",
        )

    def retrieve_for_question(
        self,
        question: str,
        context: dict[str, object] | None = None,
    ) -> KnowledgeRetrievalResult:
        return self.retrieve(analyze_chat_intent(question, context))


def answerability_for_analysis(
    analysis: ChatIntentAnalysis,
    *,
    has_cards: bool,
) -> Answerability:
    if analysis.category in {"symptom_or_emergency", "mental_health_risk"}:
        return "urgent_escalation"
    if analysis.category in {"drug_or_interaction", "out_of_scope"}:
        return "medical_decision_boundary"
    if not has_cards:
        return "unknown_no_reviewed_source"
    if analysis.category == "medication_supplement_caution":
        return "answerable_with_caution"
    return "answerable"


def unique_source_metadata(cards: tuple[AnswerCard, ...]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for card in cards:
        key = (card.source_id, card.source_family)
        if key in seen:
            continue
        seen.add(key)
        sources.append(card.source_metadata())
    return sources


def _reviewed_source_by_id(source_id: str):
    return next(
        (source for source in REVIEWED_MEDICAL_SOURCE_REGISTRY if source.source_id == source_id),
        None,
    )


def _source_family_for_item(
    item: MedicalKnowledgeItem,
    source_families: tuple[SourceFamily, ...],
) -> SourceFamily:
    if item.source_id == "kdris-2025" and "nutrition_reference" in source_families:
        return "nutrition_reference"
    if item.intent == "supplement" and "supplement_reference" in source_families:
        return "supplement_reference"
    if item.condition is not None and "chronic_condition" in source_families:
        return "chronic_condition"
    if "general_medical" in source_families:
        return "general_medical"
    return source_families[0]


def _item_is_relevant_to_question(
    item: MedicalKnowledgeItem,
    normalized_question: str,
    analysis: ChatIntentAnalysis,
) -> bool:
    if analysis.category == "medication_supplement_caution":
        return _caution_item_matches_question(item, normalized_question)
    if analysis.category == "supplement_question":
        return _supplement_item_matches_question(item, normalized_question)
    return True


def _caution_item_matches_question(
    item: MedicalKnowledgeItem,
    normalized_question: str,
) -> bool:
    if item.topic == "magnesium_supplement_caution":
        return "마그네슘" in normalized_question or "magnesium" in normalized_question
    return False


def _supplement_item_matches_question(
    item: MedicalKnowledgeItem,
    normalized_question: str,
) -> bool:
    if item.intent != "supplement":
        return True
    if item.topic == "magnesium_supplement_caution":
        return "마그네슘" in normalized_question or "magnesium" in normalized_question
    return True
