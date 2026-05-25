"""Learning/vector DB security preflight script tests."""

from __future__ import annotations

import importlib
import json
import sys
from io import StringIO
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[4]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

check_learning_vector_db_security = importlib.import_module(
    "scripts.check_learning_vector_db_security"
)


def test_preflight_constants_cover_supabase_learning_tables_and_raw_keys() -> None:
    """Verify the DB preflight checks the sensitive Supabase exposure surface."""
    assert check_learning_vector_db_security.LEARNING_VECTOR_TABLES == (
        "learning_image_objects",
        "image_embedding_jobs",
        "image_embedding_records",
    )
    assert check_learning_vector_db_security.SUPABASE_API_ROLES == (
        "PUBLIC",
        "anon",
        "authenticated",
        "service_role",
    )
    assert {
        "image_bytes",
        "raw_ocr_text",
        "provider_payload",
        "request_headers",
        "secret",
    }.issubset(check_learning_vector_db_security.FORBIDDEN_COLUMNS)


@pytest.mark.asyncio
async def test_run_preflight_outputs_sanitized_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify successful reports do not need database URLs or secrets."""

    async def fake_collect_security_report() -> dict[str, object]:
        """Return a sanitized success report."""
        return {
            "schema_version": check_learning_vector_db_security.SCHEMA_VERSION,
            "passed": True,
            "vector_extension_schema": "extensions",
            "raw_image_bytes_stored_in_db": False,
            "raw_ocr_text_stored_in_db": False,
        }

    monkeypatch.setattr(
        check_learning_vector_db_security,
        "collect_security_report",
        fake_collect_security_report,
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = await check_learning_vector_db_security.run_preflight(
        strict=True,
        stdout=stdout,
        stderr=stderr,
    )

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert payload["passed"] is True
    assert "database_url" not in payload


@pytest.mark.asyncio
async def test_run_preflight_outputs_sanitized_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify connection failures do not print URLs, passwords, or raw data."""

    async def fake_collect_security_report() -> dict[str, object]:
        """Raise a representative connection failure."""
        raise RuntimeError("postgresql://user:password@example.com/lemon")

    monkeypatch.setattr(
        check_learning_vector_db_security,
        "collect_security_report",
        fake_collect_security_report,
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = await check_learning_vector_db_security.run_preflight(
        strict=True,
        stdout=stdout,
        stderr=stderr,
    )

    payload = json.loads(stderr.getvalue())
    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert payload == {
        "error_type": "RuntimeError",
        "schema_version": check_learning_vector_db_security.SCHEMA_VERSION,
        "status": "failed",
    }
    assert "password" not in stderr.getvalue()
