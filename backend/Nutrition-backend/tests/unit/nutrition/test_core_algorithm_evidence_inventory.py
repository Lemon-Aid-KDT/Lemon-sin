"""Core-algorithm evidence intake registry tests."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
INVENTORY_PATH = PROJECT_ROOT / "data" / "nutrition_reference" / "core_algorithm_evidence.json"
REQUIRED_FIELDS = {
    "topic",
    "algorithm_area",
    "claim_summary",
    "recommended_action",
    "source_type",
    "review_status",
    "source_doc",
    "priority",
    "implementation_target",
}
ALLOWED_STATUSES = {"draft", "reviewed", "rejected", "needs_official_source"}


def test_core_algorithm_evidence_inventory_has_required_review_metadata() -> None:
    """Every imported claim must remain traceable and non-user-facing by default."""
    records = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

    assert isinstance(records, list)
    assert len(records) >= 12
    for record in records:
        assert REQUIRED_FIELDS.issubset(record)
        assert record["review_status"] in ALLOWED_STATUSES
        assert record["review_status"] == "draft"
        assert record["source_doc"]
        assert record["implementation_target"]


def test_core_algorithm_evidence_inventory_keeps_p0_safety_backlog_visible() -> None:
    """P0 safety candidates must be present before code rules graduate to reviewed."""
    records = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    p0_topics = {record["topic"] for record in records if record["priority"] == "P0"}

    assert "drug_supplement_interaction_boundary" in p0_topics
    assert "smoker_beta_carotene_vitamin_a_boundary" in p0_topics
    assert "alcohol_vitamin_a_acetaminophen_boundary" in p0_topics
    assert "weight_prediction_medical_limiter_boundary" in p0_topics
