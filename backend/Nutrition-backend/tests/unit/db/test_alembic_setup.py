"""Alembic configuration tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[4]


def test_alembic_script_directory_loads_initial_revision() -> None:
    """Verify Alembic can load the local migration directory."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["0010_revoke_learning_api_grants"]


def test_alembic_script_directory_loads_outside_backend_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Alembic script location does not depend on backend as cwd."""
    monkeypatch.chdir(BACKEND_ROOT.parent)
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["0010_revoke_learning_api_grants"]


def test_alembic_env_widens_revision_id_capacity() -> None:
    """Verify live migration smoke can store descriptive revision ids."""
    env_path = BACKEND_ROOT / "alembic" / "env.py"
    env_source = env_path.read_text(encoding="utf-8")

    assert "_ensure_revision_id_capacity(connection)" in env_source
    assert "connection.commit()" in env_source
    assert "version_num VARCHAR(255)" in env_source
    assert "ALTER COLUMN version_num TYPE VARCHAR(255)" in env_source


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


def test_learning_vector_migration_uses_supabase_extension_schema() -> None:
    """Verify pgvector is not installed in the public schema."""
    migration_path = BACKEND_ROOT / "alembic" / "versions" / "0005_create_learning_vector_tables.py"
    migration = migration_path.read_text(encoding="utf-8")

    assert "CREATE SCHEMA IF NOT EXISTS extensions" in migration
    assert "CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions" in migration
    assert "extensions.vector" in migration


def test_regulated_ocr_intake_migration_file_exists() -> None:
    """Verify the regulated OCR intake migration file exists."""
    migration_path = (
        BACKEND_ROOT / "alembic" / "versions" / "0006_create_regulated_ocr_intake_tables.py"
    )

    assert migration_path.is_file()


def test_health_daily_summaries_composite_pk_migration_file_exists() -> None:
    """Verify the PR-O composite-PK migration file exists."""
    migration_path = (
        BACKEND_ROOT / "alembic" / "versions" / "0007_health_daily_summaries_composite_pk.py"
    )

    assert migration_path.is_file()


def test_health_daily_summaries_hypertable_migration_file_exists() -> None:
    """Verify the PR-P opt-in hypertable migration file exists."""
    migration_path = (
        BACKEND_ROOT / "alembic" / "versions" / "0008_health_daily_summaries_hypertable.py"
    )

    assert migration_path.is_file()


def test_learning_vector_supabase_access_migration_file_exists() -> None:
    """Verify the Supabase access hardening migration file exists."""
    migration_path = (
        BACKEND_ROOT / "alembic" / "versions" / "0009_harden_learning_vector_supabase_access.py"
    )

    assert migration_path.is_file()


def test_learning_vector_supabase_access_migration_is_fail_closed() -> None:
    """Verify learning/vector tables are not exposed to Supabase API roles."""
    migration_path = (
        BACKEND_ROOT / "alembic" / "versions" / "0009_harden_learning_vector_supabase_access.py"
    )
    migration = migration_path.read_text(encoding="utf-8")

    for table_name in (
        "learning_image_objects",
        "image_embedding_jobs",
        "image_embedding_records",
    ):
        assert "public.{table_name}" in migration
        assert table_name in migration

    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FROM PUBLIC" in migration
    assert "'anon', 'authenticated', 'service_role'" in migration
    assert "'pending_auto_filter'" in migration
    assert "'pending_manual_review'" in migration
    assert "'rejected_by_auto_filter'" in migration
    assert "GRANT " not in migration


def test_learning_vector_remote_grant_revoke_migration_file_exists() -> None:
    """Verify the remote Supabase drift hardening migration file exists."""
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "0010_revoke_learning_api_grants_and_public_definers.py"
    )

    assert migration_path.is_file()


def test_learning_vector_remote_grant_revoke_migration_is_fail_closed() -> None:
    """Verify remote drift migration revokes Data API and public definer access."""
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "0010_revoke_learning_api_grants_and_public_definers.py"
    )
    migration = migration_path.read_text(encoding="utf-8")

    assert "REVOKE ALL PRIVILEGES ON TABLE" in migration
    assert "public.learning_image_objects" in migration
    assert "public.image_embedding_jobs" in migration
    assert "public.image_embedding_records" in migration
    assert "REVOKE EXECUTE ON FUNCTION" in migration
    assert "rls_auto_enable" in migration
    assert "'anon', 'authenticated', 'service_role'" in migration
    assert "GRANT " not in migration
