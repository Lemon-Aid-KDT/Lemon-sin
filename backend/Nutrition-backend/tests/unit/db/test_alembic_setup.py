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

    assert script.get_heads() == ["0009_create_medical_source_governance_tables"]


def test_alembic_script_directory_loads_outside_backend_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Alembic script location does not depend on backend as cwd."""
    monkeypatch.chdir(BACKEND_ROOT.parent)
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["0009_create_medical_source_governance_tables"]


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
