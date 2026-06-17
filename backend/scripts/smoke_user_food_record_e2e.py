"""Smoke-test the DB-backed user food-record context end to end (seed -> load).

Seeds a confirmed ``FoodRecord`` for a synthetic owner under FORCE RLS, then
loads it back through the real loader (a real SQL ``SELECT`` against the
non-superuser ``lemon_app`` role) and confirms the answer-facing snapshot
reflects the saved record. This is the K6 (real DB) counterpart to the L6 auto
check, which proves the same pipeline minus the SQL round-trip.

Run::

    DATABASE_URL='postgresql+asyncpg://lemon_app:lemon_app@localhost:55432/lemon' \
        python scripts/smoke_user_food_record_e2e.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
AI_AGENT_SRC = BACKEND_ROOT / "ai_agent_chat" / "src"

sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))
sys.path.insert(0, str(AI_AGENT_SRC))
sys.path.insert(0, str(BACKEND_ROOT))

from src.config import Settings  # noqa: E402
from src.db.dependencies import rls_request_transaction_allow_inner_commit  # noqa: E402
from src.models.db.food_record import FoodRecord  # noqa: E402
from src.security.auth import AuthenticatedUser  # noqa: E402
from src.security.privacy import hash_actor_subject  # noqa: E402
from src.services.food_records import load_recent_user_food_record_context  # noqa: E402

EXPECTED_ITEM = "라면"


def _user() -> AuthenticatedUser:
    return AuthenticatedUser(
        subject="k6-smoke-user",
        issuer="https://auth.example.com/",
        claims={"sub": "k6-smoke-user"},
    )


async def _run(database_url: str) -> dict[str, Any]:
    settings = Settings(privacy_hash_secret=SecretStr("k6-smoke-secret"))
    user = _user()
    owner_hash = hash_actor_subject(user, settings)
    engine = create_async_engine(database_url)
    try:
        async with (
            AsyncSession(engine) as session,
            rls_request_transaction_allow_inner_commit(session, user, settings),
        ):
            session.add(
                FoodRecord(
                    owner_subject_hash=owner_hash,
                    recorded_date=date(2026, 5, 21),
                    meal_type="lunch",
                    display_items=[EXPECTED_ITEM],
                    estimated_tags=["high_sodium"],
                    rough_nutrient_axes=["sodium_high"],
                    user_confirmed=True,
                    source="manual",
                )
            )
            await session.flush()
            snapshots = await load_recent_user_food_record_context(session, user, settings)
    finally:
        await engine.dispose()

    loaded_items = [item for snap in snapshots for item in snap.get("display_items", [])]
    reflected = EXPECTED_ITEM in loaded_items
    return {
        "status": "ok" if reflected else "fail",
        "loaded_record_count": len(snapshots),
        "loaded_display_items": loaded_items,
        "answer_reflects_record": reflected,
    }


def main() -> int:
    """Run the user food-record end-to-end smoke and print a JSON result."""
    parser = argparse.ArgumentParser(description="Seed -> RLS load -> reflect smoke.")
    parser.add_argument(
        "--database-url",
        default=os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL"),
    )
    args = parser.parse_args()
    if not args.database_url:
        print(
            "ERROR: set DATABASE_URL or TEST_DATABASE_URL, or pass --database-url.",
            file=sys.stderr,
        )
        return 2
    result = asyncio.run(_run(args.database_url))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
