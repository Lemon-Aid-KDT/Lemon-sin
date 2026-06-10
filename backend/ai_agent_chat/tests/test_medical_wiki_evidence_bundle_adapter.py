from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from lemon_ai_agent.agents.chatbot import ChatbotAgent
from lemon_ai_agent.chat_session import ChatbotRequest
from lemon_ai_agent.medical_wiki_evidence_bundles import (
    MedicalWikiEvidenceBundleRetriever,
)

MEDICAL_WIKI_FIXTURES = (
    Path(__file__).resolve().parents[4]
    / "MEDICAL-WIKI"
    / "manifest"
    / "evidence_bundle_adapter_fixtures.jsonl"
)

pytestmark = pytest.mark.skipif(
    not MEDICAL_WIKI_FIXTURES.exists(),
    reason="MEDICAL-WIKI manifest is managed outside this git worktree",
)


def test_evidence_bundle_retriever_loads_all_current_fixtures() -> None:
    retriever = MedicalWikiEvidenceBundleRetriever(
        MEDICAL_WIKI_FIXTURES,
        as_of=date(2026, 6, 9),
    )

    assert len(retriever.fixtures) == 60
    assert retriever.route_counts() == {
        "answer_renderer_with_boundary_anchor": 10,
        "boundary_renderer": 50,
    }
    assert all(bundle.expires_at > "2026-06-09" for bundle in retriever.fixtures)


def test_evidence_bundle_boundary_fixture_discards_sections_and_preserves_sources() -> None:
    retriever = MedicalWikiEvidenceBundleRetriever(
        MEDICAL_WIKI_FIXTURES,
        as_of=date(2026, 6, 9),
    )

    bundle = next(
        fixture
        for fixture in retriever.fixtures
        if fixture.expected_renderer_route == "boundary_renderer"
    )
    result = retriever.retrieve_for_question(bundle.query)

    assert result.retrieval_status == "found"
    assert result.cards
    assert {card.answerability for card in result.cards}.issubset(
        {"urgent_escalation", "medical_decision_boundary", "safety_boundary"}
    )
    assert all("reviewed_section:" not in card.grounding_snippet_ids for card in result.cards)
    assert {card.source_id for card in result.cards} == set(bundle.expected_source_ids)
    assert set(bundle.blocked_actions).issubset(set(result.cards[0].must_not_say))


def test_evidence_bundle_answerable_fixture_preserves_section_and_boundary_anchor() -> None:
    retriever = MedicalWikiEvidenceBundleRetriever(
        MEDICAL_WIKI_FIXTURES,
        as_of=date(2026, 6, 9),
    )

    bundle = next(
        fixture
        for fixture in retriever.fixtures
        if fixture.expected_renderer_route == "answer_renderer_with_boundary_anchor"
    )
    result = retriever.retrieve_for_question(bundle.query)

    assert result.retrieval_status == "found"
    assert result.cards
    assert {card.answerability for card in result.cards} == {"answerable_with_caution"}
    assert any(
        any(snippet.startswith("reviewed_section:") for snippet in card.grounding_snippet_ids)
        for card in result.cards
    )
    assert {card.source_id for card in result.cards} == set(bundle.expected_source_ids)
    assert bundle.safety_anchor_claim_id in {card.linked_claim_id for card in result.cards}
    assert set(bundle.blocked_actions).issubset(set(result.cards[0].must_not_say))


def test_chatbot_routes_evidence_bundle_answerable_fixture_to_card_renderer() -> None:
    retriever = MedicalWikiEvidenceBundleRetriever(
        MEDICAL_WIKI_FIXTURES,
        as_of=date(2026, 6, 9),
    )
    bundle = next(
        fixture
        for fixture in retriever.fixtures
        if fixture.expected_renderer_route == "answer_renderer_with_boundary_anchor"
    )

    response = ChatbotAgent(retriever=retriever).answer(
        ChatbotRequest(
            request_id="medical-wiki-evidence-bundle-answerable",
            user_id="medical-wiki-eval-user",
            message=bundle.query,
        )
    )

    assert response.provider == "deterministic"
    assert response.answerability == "answerable_with_caution"
    assert "출처 기준" in response.message
    assert "진단합니다" not in response.message
    assert {source["source_id"] for source in response.sources} == set(bundle.expected_source_ids)
