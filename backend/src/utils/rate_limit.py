"""Redis 기반 rate-limit 헬퍼.

정책 (CLAUDE.md §10.3):
  - 이메일 인증 발송: 1분에 1회 / 하루 5회
  - 로그인 실패: 10분에 5회

구현:
  - 키 패턴: rl:{action}:{identifier}:{window}
    예: rl:email_send:user@a.com:minute, rl:email_send:user@a.com:day
  - INCR + EXPIRE 로 카운트.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from src.cache.redis_client import get_redis


@dataclass
class RateLimitWindow:
    """rate-limit 윈도우 정의."""
    label: str          # 키 suffix (예: "minute", "day")
    window_seconds: int  # 윈도우 길이
    max_count: int       # 최대 허용 횟수


async def enforce_rate_limit(
    *,
    action: str,
    identifier: str,
    windows: list[RateLimitWindow],
    user_friendly_action: str = "요청",
) -> None:
    """주어진 윈도우들 모두 검사. 하나라도 초과면 429.

    호출 예:
      await enforce_rate_limit(
          action="email_send",
          identifier=email,
          windows=[
              RateLimitWindow("minute", 60, 1),
              RateLimitWindow("day", 86400, 5),
          ],
          user_friendly_action="이메일 인증 코드 발송",
      )
    """
    redis = get_redis()
    # 1. 모든 윈도우 카운트 조회 (limit 검사만)
    for w in windows:
        key = f"rl:{action}:{identifier}:{w.label}"
        current = await redis.get(key)
        current_count = int(current) if current else 0
        if current_count >= w.max_count:
            ttl = await redis.ttl(key)
            retry_after = max(ttl, 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=_rate_limit_message(user_friendly_action, w, retry_after),
                headers={"Retry-After": str(retry_after)},
            )
    # 2. 검사 통과 — 모든 윈도우 INCR (실제 카운트)
    for w in windows:
        key = f"rl:{action}:{identifier}:{w.label}"
        # pipeline 으로 race condition 최소화
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, w.window_seconds, nx=True)  # 키 없을 때만 TTL 세팅
        await pipe.execute()


def _rate_limit_message(action: str, w: RateLimitWindow, retry_after: int) -> str:
    """사용자 친화 메시지."""
    if w.label == "minute":
        return f"{action} 은 {w.window_seconds}초에 {w.max_count}회까지만 가능해요. {retry_after}초 후 다시 시도해주세요."
    if w.label == "day":
        return f"오늘 {action} 한도를 초과했어요 (하루 {w.max_count}회). 내일 다시 시도해주세요."
    return f"{action} 한도 초과. {retry_after}초 후 다시 시도해주세요."


async def reset_counter(action: str, identifier: str, window_label: str) -> None:
    """테스트 / 어드민용 카운터 리셋."""
    redis = get_redis()
    await redis.delete(f"rl:{action}:{identifier}:{window_label}")
