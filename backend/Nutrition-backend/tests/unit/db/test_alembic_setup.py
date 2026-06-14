"""Alembic configuration tests."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[4]


def test_alembic_script_directory_loads_initial_revision() -> None:
    """Verify Alembic can load the local migration directory."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["0018_seed_dyslipidemia_weight_evidence"]


def test_alembic_script_directory_loads_outside_backend_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Alembic script location does not depend on backend as cwd."""
    monkeypatch.chdir(BACKEND_ROOT.parent)
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["0018_seed_dyslipidemia_weight_evidence"]


def test_initial_migration_file_exists() -> None:
    """Verify the initial users migration file exists."""
    migration_path = BACKEND_ROOT / "alembic" / "versions" / "0001_create_users_table.py"

    assert migration_path.is_file()


def test_analysis_results_migration_file_exists() -> None:
    """Verify the analysis result migration file exists."""
    migration_path = BACKEND_ROOT / "alembic" / "versions" / "0002_create_analysis_results_table.py"

    assert migration_path.is_file()


def test_privacy_migration_file_exists() -> None:
    """Verify the privacy consent and audit migration file exists."""
    migration_path = (
        BACKEND_ROOT / "alembic" / "versions" / "0003_create_privacy_consent_audit_tables.py"
    )

    assert migration_path.is_file()


def test_p1_supplement_health_migration_file_exists() -> None:
    """Verify the P1 supplement and health migration file exists."""
    migration_path = (
        BACKEND_ROOT / "alembic" / "versions" / "0004_create_p1_supplement_health_tables.py"
    )

    assert migration_path.is_file()


def test_learning_vector_migration_file_exists() -> None:
    """Verify the learning vector migration file exists."""
    migration_path = BACKEND_ROOT / "alembic" / "versions" / "0005_create_learning_vector_tables.py"

    assert migration_path.is_file()


def test_regulated_ocr_intake_migration_file_exists() -> None:
    """Verify the regulated OCR intake migration file exists."""
    migration_path = (
        BACKEND_ROOT / "alembic" / "versions" / "0006_create_regulated_ocr_intake_tables.py"
    )

    assert migration_path.is_file()


def test_agent_memory_migration_file_exists() -> None:
    """Verify the Agent memory migration file exists."""
    migration_path = BACKEND_ROOT / "alembic" / "versions" / "0007_create_agent_memory_tables.py"

    assert migration_path.is_file()


def test_alembic_version_table_supports_long_revision_ids() -> None:
    """Verify offline DDL uses a version column wide enough for local revision IDs."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    output = StringIO()
    config.output_buffer = output

    command.upgrade(config, "head", sql=True)

    assert "version_num VARCHAR(80)" in output.getvalue()


def test_medical_source_governance_migration_file_exists() -> None:
    """Verify the medical source governance migration file exists."""
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "0009_create_medical_source_governance_tables.py"
    )

    assert migration_path.is_file()


def test_chatbot_unknown_backlog_migration_file_exists() -> None:
    """Verify the chatbot unknown backlog migration file exists."""
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "0010_add_chatbot_unknown_backlog.py"
    )

    assert migration_path.is_file()


def test_chatbot_reviewed_evidence_seed_migration_file_exists() -> None:
    """Verify the chatbot reviewed evidence seed migration exists."""
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "0011_seed_chatbot_reviewed_evidence.py"
    )

    assert migration_path.is_file()


def test_chatbot_policy_boundary_seed_migration_file_exists() -> None:
    """Verify the chatbot policy boundary seed migration exists."""
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "0012_seed_chatbot_policy_boundaries.py"
    )

    assert migration_path.is_file()


def test_chatbot_unknown_backlog_summary_view_migration_file_exists() -> None:
    """Verify the chatbot unknown backlog summary view migration exists."""
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "0013_create_chatbot_unknown_backlog_summary_view.py"
    )

    assert migration_path.is_file()


def test_user_medications_migration_file_exists() -> None:
    """Verify the user medications migration exists."""
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "0014_create_user_medications.py"
    )

    assert migration_path.is_file()


def test_food_records_migration_file_exists() -> None:
    """Verify the food records migration exists."""
    migration_path = BACKEND_ROOT / "alembic" / "versions" / "0015_create_food_records.py"

    assert migration_path.is_file()


def test_food_records_migration_is_privacy_safe() -> None:
    """Verify food record storage avoids raw prompt/OCR/transcript fields."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    output = StringIO()
    config.output_buffer = output

    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    migration_sql = sql.split("0015_create_food_records", maxsplit=1)[-1]

    assert "0015_create_food_records" in sql
    assert "CREATE TABLE food_records" in migration_sql
    assert "display_items" in migration_sql
    assert "food_db_match_id" in migration_sql
    assert "match_confidence" in migration_sql
    assert "nutrient_estimates" in migration_sql
    assert "raw_question" not in migration_sql
    assert "raw_prompt" not in migration_sql
    assert "raw_ocr" not in migration_sql
    assert "raw_chat_transcript" not in migration_sql


def test_user_medications_migration_is_privacy_safe() -> None:
    """Verify saved medication storage avoids raw health free text."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    output = StringIO()
    config.output_buffer = output

    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()

    migration_sql = sql.split("0014_create_user_medications", maxsplit=1)[-1]

    assert "0014_create_user_medications" in sql
    assert "CREATE TABLE user_medications" in migration_sql
    assert "owner_subject_hash" in migration_sql
    assert "display_name" in migration_sql
    assert "condition_tags" in migration_sql
    assert "raw_question" not in migration_sql
    assert "raw_prompt" not in migration_sql
    assert "raw_ocr" not in migration_sql
    assert "conversation" not in migration_sql
    assert "dose_text" not in migration_sql
    assert "free_text_note" not in migration_sql


def test_chatbot_unknown_backlog_summary_view_migration_is_privacy_safe() -> None:
    """Verify local Alembic SQL creates only aggregate backlog fields."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    output = StringIO()
    config.output_buffer = output

    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()

    assert "0013_create_chatbot_unknown_backlog_summary_view" in sql
    assert "CREATE OR REPLACE VIEW chatbot_unknown_knowledge_backlog_summary" in sql
    assert "security_invoker = true" in sql
    assert "event_count" in sql
    assert "latest_event_at" in sql
    assert "raw_question" not in sql
    assert "raw_prompt" not in sql
    assert "raw_ocr" not in sql
    assert "conversation" not in sql


def test_chatbot_policy_boundary_seed_migration_contains_p0_codes() -> None:
    """Verify local Alembic SQL includes reviewed P0 policy boundary seeds."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    output = StringIO()
    config.output_buffer = output

    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()

    assert "0012_seed_chatbot_policy_boundaries" in sql
    assert "p0_st_johns_wort_antidepressant" in sql
    assert "p0_grapefruit_statin" in sql
    assert "p0_potassium_salt_substitute" in sql
    assert "p0_nitrate_pde5_inhibitor" in sql
    assert "p0_serotonergic_supplement_antidepressant" in sql
    assert "p0_statin_red_yeast_rice" in sql
