"""AnswerCard normalization and retrieval tests."""

from __future__ import annotations

from lemon_ai_agent.answer_card import (
    AnswerCardNormalizer,
    MedicalKnowledgeRetriever,
)
from lemon_ai_agent.knowledge import (
    MEDICAL_KNOWLEDGE_ITEMS,
    analyze_chat_intent,
)


def test_answer_card_normalizer_converts_reviewed_seed_item() -> None:
    """Reviewed seed cards become source-traceable AnswerCards."""
    item = next(
        item
        for item in MEDICAL_KNOWLEDGE_ITEMS
        if item.topic == "magnesium_supplement_caution"
    )

    card = AnswerCardNormalizer().from_medical_knowledge_item(
        item,
        answerability="answerable_with_caution",
    )

    assert card is not None
    assert card.card_id == "seed:magnesium_supplement_caution"
    assert card.answerability == "answerable_with_caution"
    assert card.source_id == "kdris-2025"
    assert card.review_status == "reviewed"
    assert card.source_family == "nutrition_reference"
    assert card.allowed_guidance
    assert card.specific_examples
    assert card.checklist
    assert card.must_not_say
    assert card.reviewed_at
    assert card.expires_at
    assert card.grounding_snippet_ids == ("seed:magnesium_supplement_caution",)


def test_answer_card_normalizer_rejects_draft_seed_item() -> None:
    """Draft or paper-candidate seed items cannot become user-facing cards."""
    draft_item = next(
        item for item in MEDICAL_KNOWLEDGE_ITEMS if item.source_id == "semantic-scholar"
    )

    card = AnswerCardNormalizer().from_medical_knowledge_item(
        draft_item,
        answerability="answerable",
    )

    assert card is None


def test_retriever_returns_no_match_for_unreviewed_specific_couse_question() -> None:
    """Uncovered medication/supplement combinations fail closed instead of reusing a broad card."""
    analysis = analyze_chat_intent("리튬 약을 먹는데 셀레늄 영양제 같이 먹어도 돼?")

    result = MedicalKnowledgeRetriever().retrieve(analysis)

    assert result.retrieval_status == "no_match"
    assert result.cards == ()
    assert "no_reviewed_answer_card" in result.warnings


def test_retriever_returns_magnesium_caution_card_for_supported_couse_question() -> None:
    """Known caution topics can be explained through a reviewed AnswerCard."""
    analysis = analyze_chat_intent("혈압약 먹는데 마그네슘 영양제 같이 먹어도 돼?")

    result = MedicalKnowledgeRetriever().retrieve(analysis)

    assert result.retrieval_status == "found"
    assert any(card.topic == "magnesium_supplement_caution" for card in result.cards)
    assert all(card.review_status == "reviewed" for card in result.cards)
