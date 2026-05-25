"""Medical knowledge registry and Q&A policy coverage tests."""

from __future__ import annotations

from collections import Counter

from lemon_ai_agent.knowledge import (
    LLM_QA_EVAL_SET,
    REVIEWED_MEDICAL_SOURCE_REGISTRY,
    policy_for_question,
)


def test_reviewed_medical_source_registry_tracks_keyed_sources() -> None:
    """Verify MVP medical sources have review metadata and env-key ownership."""
    by_id = {source.source_id: source for source in REVIEWED_MEDICAL_SOURCE_REGISTRY}

    kdca = by_id["kdca-healthinfo"]
    assert kdca.status == "reviewed"
    assert kdca.publisher == "Korea Disease Control and Prevention Agency"
    assert kdca.env_key == "KDCA_HEALTHINFO_API_KEY"
    assert "chronic_condition" in kdca.source_families
    assert {"hypertension", "diabetes", "kidney_disease"}.issubset(set(kdca.topics))
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
