"""Check learning/vector DB security posture without printing secrets."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.config import get_settings  # noqa: E402

SCHEMA_VERSION = "learning-vector-db-security-v1"
LEARNING_VECTOR_TABLES = (
    "learning_image_objects",
    "image_embedding_jobs",
    "image_embedding_records",
)
SUPABASE_API_ROLES = ("PUBLIC", "anon", "authenticated", "service_role")
FORBIDDEN_COLUMNS = (
    "image_bytes",
    "raw_image",
    "raw_image_bytes",
    "image_base64",
    "ocr_text",
    "raw_ocr_text",
    "provider_payload",
    "raw_provider_payload",
    "request_headers",
    "secret",
)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any security check fails.",
    )
    return parser.parse_args()


async def collect_security_report() -> dict[str, Any]:
    """Collect a sanitized learning/vector DB security report.

    Returns:
        JSON-serializable report without database URLs, secrets, or raw data.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            vector_extension_installed = bool(
                await connection.scalar(
                    text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                )
            )
            vector_extension_schema = await connection.scalar(text("""
                    SELECT n.nspname
                    FROM pg_extension e
                    JOIN pg_namespace n ON n.oid = e.extnamespace
                    WHERE e.extname = 'vector'
                    """))
            table_reports = []
            unsafe_privileges = []
            forbidden_columns = []
            for table_name in LEARNING_VECTOR_TABLES:
                table_reports.append(
                    await _table_security_report(connection, table_name=table_name)
                )
                unsafe_privileges.extend(
                    await _unsafe_privileges(connection, table_name=table_name)
                )
                forbidden_columns.extend(
                    await _forbidden_columns(connection, table_name=table_name)
                )
    finally:
        await engine.dispose()

    passed = (
        vector_extension_installed
        and vector_extension_schema == "extensions"
        and all(table["exists"] and table["rls_enabled"] for table in table_reports)
        and not unsafe_privileges
        and not forbidden_columns
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "passed": passed,
        "vector_extension_installed": vector_extension_installed,
        "vector_extension_schema": vector_extension_schema,
        "tables": table_reports,
        "unsafe_privilege_count": len(unsafe_privileges),
        "unsafe_privileges": unsafe_privileges,
        "forbidden_column_count": len(forbidden_columns),
        "forbidden_columns": forbidden_columns,
        "raw_image_bytes_stored_in_db": False,
        "raw_ocr_text_stored_in_db": False,
    }


async def _table_security_report(connection: Any, *, table_name: str) -> dict[str, Any]:
    """Return table existence and RLS status.

    Args:
        connection: Async SQLAlchemy connection.
        table_name: Public schema table name.

    Returns:
        Sanitized table security report.
    """
    row = (
        (
            await connection.execute(
                text("""
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relname = :table_name
                """),
                {"table_name": table_name},
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        return {
            "table": table_name,
            "exists": False,
            "rls_enabled": False,
            "rls_forced": False,
        }
    return {
        "table": table_name,
        "exists": True,
        "rls_enabled": bool(row["relrowsecurity"]),
        "rls_forced": bool(row["relforcerowsecurity"]),
    }


async def _unsafe_privileges(connection: Any, *, table_name: str) -> list[dict[str, str]]:
    """Return Supabase API-role privileges that should be absent.

    Args:
        connection: Async SQLAlchemy connection.
        table_name: Public schema table name.

    Returns:
        Unsafe privilege rows.
    """
    rows = (
        (
            await connection.execute(
                text("""
                SELECT grantee, privilege_type
                FROM information_schema.table_privileges
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                  AND grantee IN :roles
                ORDER BY grantee, privilege_type
                """).bindparams(bindparam("roles", expanding=True)),
                {"table_name": table_name, "roles": list(SUPABASE_API_ROLES)},
            )
        )
        .mappings()
        .all()
    )
    return [
        {
            "table": table_name,
            "grantee": str(row["grantee"]),
            "privilege_type": str(row["privilege_type"]),
        }
        for row in rows
    ]


async def _forbidden_columns(connection: Any, *, table_name: str) -> list[dict[str, str]]:
    """Return forbidden raw payload columns if they exist.

    Args:
        connection: Async SQLAlchemy connection.
        table_name: Public schema table name.

    Returns:
        Forbidden column rows.
    """
    rows = (
        (
            await connection.execute(
                text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                  AND lower(column_name) IN :forbidden_columns
                ORDER BY column_name
                """).bindparams(bindparam("forbidden_columns", expanding=True)),
                {"table_name": table_name, "forbidden_columns": list(FORBIDDEN_COLUMNS)},
            )
        )
        .mappings()
        .all()
    )
    return [
        {
            "table": table_name,
            "column": str(row["column_name"]),
        }
        for row in rows
    ]


async def run_preflight(
    *,
    strict: bool = False,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Run the security preflight and write sanitized JSON.

    Args:
        strict: Return a failing exit code when checks do not pass.
        stdout: Destination for successful report JSON.
        stderr: Destination for connection or execution failure JSON.

    Returns:
        Process-style exit code.
    """
    try:
        report = await collect_security_report()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "failed",
                    "error_type": exc.__class__.__name__,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=stderr,
        )
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), file=stdout)
    if strict and not report["passed"]:
        return 1
    return 0


def main() -> None:
    """Run the DB security check."""
    args = parse_args()
    raise SystemExit(asyncio.run(run_preflight(strict=args.strict)))


if __name__ == "__main__":
    main()
