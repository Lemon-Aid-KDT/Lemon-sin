from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from lemon_ai_agent.medical_wiki_evidence_bundles import (
    MedicalWikiEvidenceBundleRetriever,
)

from scripts import eval_medical_wiki_evidence_bundles as eval_evidence_bundles

WORKSPACE_ROOT = Path(__file__).resolve().parents[6]
MEDICAL_WIKI_FIXTURES = (
    WORKSPACE_ROOT / "MEDICAL-WIKI" / "manifest" / "evidence_bundle_adapter_fixtures.jsonl"
)

pytestmark = pytest.mark.skipif(
    not MEDICAL_WIKI_FIXTURES.exists(),
    reason="MEDICAL-WIKI manifest is managed outside this git worktree",
)


def test_evidence_bundle_eval_runner_passes_representative_cases() -> None:
    retriever = MedicalWikiEvidenceBundleRetriever(
        MEDICAL_WIKI_FIXTURES,
        as_of=date(2026, 6, 9),
    )
    cases = [retriever.fixtures[0], retriever.fixtures[10]]

    rows, summary = eval_evidence_bundles.run_eval(cases, retriever)

    assert summary["status"] == "pass"
    assert summary["case_count"] == 2
    assert summary["passed"] == 2
    assert rows[0]["passed"] is True
    assert rows[1]["passed"] is True

