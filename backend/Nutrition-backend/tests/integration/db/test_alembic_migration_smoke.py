"""Opt-in Alembic live migration smoke tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

BACKEND_ROOT = Path(__file__).resolve().parents[4]
RUN_POSTGRES_MIGRATION_SMOKE = os.getenv("RUN_POSTGRES_MIGRATION_SMOKE") == "1"
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not RUN_POSTGRES_MIGRATION_SMOKE or not TEST_DATABASE_URL,
    reason=(
        "Set RUN_POSTGRES_MIGRATION_SMOKE=1 and TEST_DATABASE_URL to run live "
        "Alembic upgrade/downgrade tests."
    ),
)


def test_alembic_upgrade_and_downgrade_against_live_postgresql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify all migrations apply and roll back against an explicit test DB."""
    assert TEST_DATABASE_URL is not None
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    command.downgrade(config, "base")
