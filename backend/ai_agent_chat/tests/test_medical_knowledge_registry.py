"""Medical knowledge registry and Q&A policy coverage tests."""

from __future__ import annotations

from collections import Counter

from lemon_ai_agent.knowledge import (
    LLM_QA_EVAL_SET,
    MEDICAL_KNOWLEDGE_ITEMS,
    REVIEWED_MEDICAL_SOURCE_REGISTRY,
    analyze_chat_intent,
    policy_for_question,
    select_medical_knowledge,
)


def test_reviewed_medical_source_registry_tracks_keyed_sources() -> None:
    """Verify MVP medical sources have review metadata and env-key ownership."""
    by_id = {source.source_id: source for source in REVIEWED_MEDICAL_SOURCE_REGISTRY}

    kdca = by_id["kdca-healthinfo"]
    assert kdca.status == "reviewed"
    assert kdca.publisher == "Korea Disease Control and Prevention Agency"
    assert kdca.env_key is None
    assert "chronic_condition" in kdca.source_families
    assert {"hypertension", "diabetes", "kidney_disease"}.issubset(set(kdca.topics))
    assert len(kdca.topic_id_requirements) == 54
    assert ("hypertension", "고혈압") in kdca.topic_id_requirements
    assert kdca.last_reviewed_at

    semantic_scholar = by_id["semantic-scholar"]
    assert semantic_scholar.status == "draft"
    assert semantic_scholar.env_key == "SEMANTIC_SCHOLAR_API_KEY"
    assert semantic_scholar.user_facing_allowed is False


def test_backend_qna_eval_set_matches_classifier_targets() -> None:
    """Keep backend-integrated chatbot policy aligned with the MVP eval set."""
    groups = Counter(item.group for item in LLM_QA_EVAL_SET)

    assert len(LLM_QA_EVAL_SET) >= 230
    assert groups["general_medical"] >= 30
    assert groups["chronic_condition"] >= 50
    assert groups["nutrition_kdris"] >= 50
    assert groups["supplement_functional_food"] >= 40
    assert groups["drug_interaction_boundary"] >= 30
    assert groups["emergency_mental_health_escalation"] >= 30

    mismatches = [
        (item.case_id, policy_for_question(item.question).category, item.expected_category)
        for item in LLM_QA_EVAL_SET
        if policy_for_question(item.question).category != item.expected_category
    ]
    assert mismatches == []


def test_intent_analysis_keeps_profile_context_relevant_to_question() -> None:
    """Use profile disease context only when it matters to the user question."""
    unrelated = analyze_chat_intent(
        "오늘 수면을 어떻게 관리하면 좋아?",
        {"profile": {"chronic_conditions": ["diabetes", "hypertension"]}},
    )
    dizziness = analyze_chat_intent(
        "운동 후 어지러움이 있어",
        {"profile": {"chronic_conditions": ["diabetes", "hypertension"]}},
    )

    assert unrelated.primary_intent == "sleep"
    assert unrelated.related_conditions == ()
    assert dizziness.primary_intent == "symptom"
    assert dizziness.related_conditions == ("diabetes",)
    assert dizziness.red_flags == ()


def test_reviewed_medical_knowledge_selection_suppresses_draft_paper_sources() -> None:
    """Draft research sources stay internal and are not selected for user answers."""
    analysis = analyze_chat_intent("당뇨를 개선하려면 식사와 운동을 어떻게 관리해?")

    items = select_medical_knowledge(analysis)

    assert any(item.source == "CDC Diabetes Meal Planning" for item in items)
    assert any(item.source == "CDC Adult Physical Activity Guidelines" for item in items)
    assert all(item.reviewed_status == "reviewed" for item in items)
    assert all(item.evidence_type != "paper_candidate" for item in items)
    assert "Semantic Scholar Graph API" in {item.source for item in MEDICAL_KNOWLEDGE_ITEMS}
    assert "Semantic Scholar Graph API" not in {item.source for item in items}


def test_p0_interaction_and_context_questions_route_to_boundary_policy() -> None:
    """P0 interaction candidates stay deterministic until source review is complete."""
    questions = [
        "와파린 복용 중인데 비타민 K 영양제를 같이 먹어도 돼?",
        "갑상선약이랑 칼슘, 철분을 같이 먹어도 되는지 알려줘",
        "메트포민 먹는데 비타민 B12를 추가해도 괜찮아?",
        "항응고제 복용 중 오메가3, 은행잎, 비타민 E 같이 먹어도 돼?",
        "MAOI 약을 먹는데 티라민 많은 음식을 피해야 하는지 판단해줘",
        "흡연자인데 베타카로틴이나 비타민 A 영양제를 먹어도 돼?",
        "음주가 잦은데 비타민 A 단일제나 아세트아미노펜을 같이 써도 돼?",
    ]

    for question in questions:
        assert policy_for_question(question).category == "drug_or_interaction"
