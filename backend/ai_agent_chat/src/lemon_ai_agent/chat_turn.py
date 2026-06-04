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
from lemon_ai_agent.answer_plan import AnalysisPlan, AnswerPlan, AnswerPlanBuilder
from lemon_ai_agent.chat_session import ChatbotRequest
from lemon_ai_agent.knowledge import (
    AnswerPolicy,
    ChatIntentAnalysis,
    MedicalKnowledgeItem,
    analyze_chat_intent,
    policy_for_question,
)

_FOLLOW_UP_TERMS = (
    "그럼",
    "그러면",
    "그건",
    "그거",
    "이건",
    "이거",
    "저건",
    "저거",
    "왜",
    "자세히",
    "더",
    "저녁",
    "아침",
    "점심",
    "간식",
    "식단",
    "영양제도",
    "같이",
    "먹어도",
    "어떻게",
    "추천",
    "then",
    "why",
    "more",
    "that",
    "this",
)
_BRIEF_FOLLOW_UP_MAX_CHARS = 40


@dataclass(frozen=True)
class ChatTurnPlan:
    request: ChatbotRequest
    policy: AnswerPolicy
    analysis: ChatIntentAnalysis
    knowledge_items: tuple[MedicalKnowledgeItem, ...]
    answer_cards: tuple[AnswerCard, ...]
    answerability: Answerability
    retrieval_status: RetrievalStatus
    answer_plan: AnswerPlan
    analysis_plan: AnalysisPlan
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
        self._plan_builder = AnswerPlanBuilder()

    def plan(self, request: ChatbotRequest) -> ChatTurnPlan:
        planning_question = _continuity_planning_question(request)
        policy = policy_for_question(planning_question, request.context)
        analysis = analyze_chat_intent(planning_question, request.context)
        retrieval = self._retriever.retrieve(analysis)
        answerability = answerability_for_analysis(
            analysis,
            has_cards=bool(retrieval.cards),
        )
        answer_plan = self._plan_builder.build_answer_plan(
            request,
            analysis,
            retrieval.cards,
        )
        analysis_plan = self._plan_builder.build_analysis_plan(request, answer_plan)
        return ChatTurnPlan(
            request=request,
            policy=policy,
            analysis=analysis,
            knowledge_items=retrieval.knowledge_items,
            answer_cards=retrieval.cards,
            answerability=answerability,
            retrieval_status=retrieval.retrieval_status,
            answer_plan=answer_plan,
            analysis_plan=analysis_plan,
            retrieval_warnings=retrieval.warnings,
        )


def _continuity_planning_question(request: ChatbotRequest) -> str:
    """Add recent user turns for short follow-ups before policy/retrieval planning.

    The full conversation is not persisted here and assistant text is ignored.
    This only prevents brief references like "그럼 저녁은?" from losing the
    user-supplied health/food/medication topic from the previous turn.
    """
    message = request.message.strip()
    if not request.conversation or not _is_follow_up_message(message):
        return message

    recent_user_turns = [
        turn.content.strip()
        for turn in request.conversation[-6:]
        if turn.role == "user" and turn.content.strip()
    ]
    if not recent_user_turns:
        return message
    return "\n".join((*recent_user_turns[-3:], message))


def _is_follow_up_message(message: str) -> bool:
    normalized = " ".join(message.casefold().split())
    if not normalized:
        return False
    return len(normalized) <= _BRIEF_FOLLOW_UP_MAX_CHARS or any(
        term in normalized for term in _FOLLOW_UP_TERMS
    )
