"""Redis 클라이언트 — rate-limit, 캐시 등에 사용."""
from __future__ import annotations

from redis.asyncio import Redis

from src.config import settings

_redis: Redis | None = None


def get_redis() -> Redis:
    """싱글톤 Redis 인스턴스. 처음 호출 시 lazy 생성."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
