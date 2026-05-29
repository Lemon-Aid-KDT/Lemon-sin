from __future__ import annotations

from dataclasses import dataclass

from lemon_ai_agent.answer_card import (
    Answerability,
    AnswerCard,
    MedicalKnowledgeRetriever,
    RetrievalStatus,
    answerability_for_analysis,
    unique_source_metadata,
)
from lemon_ai_agent.chat_session import ChatbotRequest
from lemon_ai_agent.knowledge import (
    AnswerPolicy,
    ChatIntentAnalysis,
    MedicalKnowledgeItem,
    analyze_chat_intent,
    policy_for_question,
)


@dataclass(frozen=True)
class ChatTurnPlan:
    request: ChatbotRequest
    policy: AnswerPolicy
    analysis: ChatIntentAnalysis
    knowledge_items: tuple[MedicalKnowledgeItem, ...]
    answer_cards: tuple[AnswerCard, ...]
    answerability: Answerability
    retrieval_status: RetrievalStatus
    retrieval_warnings: tuple[str, ...] = ()

    @property
    def source_families(self) -> list[str]:
        return list(self.policy.source_families)

    @property
    def sources(self) -> list[dict[str, str]]:
        return unique_source_metadata(self.answer_cards)

    @property
    def requires_boundary_response(self) -> bool:
        return self.answerability in {"urgent_escalation", "medical_decision_boundary"}


class ChatTurnModule:
    """Builds the policy, intent, and reviewed knowledge plan for one chat turn."""

    def __init__(self, retriever: MedicalKnowledgeRetriever | None = None) -> None:
        self._retriever = retriever or MedicalKnowledgeRetriever()

    def plan(self, request: ChatbotRequest) -> ChatTurnPlan:
        policy = policy_for_question(request.message)
        analysis = analyze_chat_intent(request.message, request.context)
        retrieval = self._retriever.retrieve(analysis)
        answerability = answerability_for_analysis(
            analysis,
            has_cards=bool(retrieval.cards),
        )
        return ChatTurnPlan(
            request=request,
            policy=policy,
            analysis=analysis,
            knowledge_items=retrieval.knowledge_items,
            answer_cards=retrieval.cards,
            answerability=answerability,
            retrieval_status=retrieval.retrieval_status,
            retrieval_warnings=retrieval.warnings,
        )
