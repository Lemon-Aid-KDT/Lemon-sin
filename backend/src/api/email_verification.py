"""이메일 인증 — 코드 발송 / 검증.

엔드포인트:
  POST /api/v1/auth/email/send-code    — 코드 생성 + Resend 발송
  POST /api/v1/auth/email/verify-code  — 코드 검증 + users.email_verified_at 갱신
"""
from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.session import get_db
from src.models.email_verification import EmailVerification
from src.models.user import RefreshToken, User
from src.schemas.auth import MessageResponse, TokenResponse
from src.services.email import render_verification_email, send_email
from src.utils.rate_limit import RateLimitWindow, enforce_rate_limit
from src.utils.security import create_access_token, create_refresh_token

router = APIRouter(prefix="/auth/email", tags=["email-verification"])

VALID_PURPOSES = {"signup", "password_reset"}


class SendCodeRequest(BaseModel):
    email: EmailStr
    purpose: str = Field(default="signup", pattern="^(signup|password_reset)$")


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern="^[0-9]{6}$")
    purpose: str = Field(default="signup", pattern="^(signup|password_reset)$")


@router.post("/send-code", response_model=MessageResponse)
async def send_code(body: SendCodeRequest, db: AsyncSession = Depends(get_db)):
    """이메일 인증 코드 생성 + 발송.

    Rate limit (CLAUDE.md §10.3):
      - 1분에 1회 / 하루 5회 (이메일 + purpose 기준)
    """
    if body.purpose not in VALID_PURPOSES:
        raise HTTPException(status_code=400, detail="유효하지 않은 인증 목적입니다.")

    # Rate limit — purpose 별로 카운터 분리해서 signup 코드가 password_reset 한도 잡아먹지 않게
    await enforce_rate_limit(
        action=f"email_send:{body.purpose}",
        identifier=body.email,
        windows=[
            RateLimitWindow("minute", settings.email_send_min_interval_seconds, 1),
            RateLimitWindow("day", 86400, settings.email_send_daily_limit),
        ],
        user_friendly_action="이메일 인증 코드 발송",
    )

    # password_reset 은 등록된 이메일에만 — 단 보안상 "없는 계정" 명시는 피함 (계정 존재 탐색 방지)
    user = None
    if body.purpose == "password_reset":
        user = await db.scalar(
            select(User).where(User.email == body.email, User.deleted_at.is_(None))
        )
        if not user:
            # 200 OK + 일반 메시지 — 공격자에게 계정 유무 노출 안 함
            return MessageResponse(message="입력하신 이메일로 인증 코드를 보냈어요.")

    # 6자리 숫자 코드
    code = f"{secrets.randbelow(1_000_000):06d}"
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.email_code_ttl_minutes)

    # 같은 (email, purpose) 의 이전 미사용 코드는 무효화 (consumed_at 으로 표시)
    await db.execute(
        update(EmailVerification)
        .where(
            EmailVerification.email == body.email,
            EmailVerification.purpose == body.purpose,
            EmailVerification.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )

    db.add(EmailVerification(
        user_id=user.id if user else None,
        email=body.email,
        code=code,
        purpose=body.purpose,
        created_at=now,
        expires_at=expires,
        attempt_count=0,
    ))
    await db.flush()

    # 발송
    subject, html = render_verification_email(code=code, purpose=body.purpose)
    await send_email(to=body.email, subject=subject, html=html)

    return MessageResponse(message="입력하신 이메일로 인증 코드를 보냈어요.")


@router.post("/verify-code", response_model=TokenResponse | MessageResponse)
async def verify_code(body: VerifyCodeRequest, db: AsyncSession = Depends(get_db)):
    """인증 코드 검증.

    signup 성공 시: users.email_verified_at 갱신 + JWT (access/refresh) 발급.
      → 사용자가 비번 다시 입력할 필요 없이 그대로 로그인 상태로 진입.
    password_reset: 검증만 성공 메시지 반환 (비번 변경은 별도 엔드포인트).
    """
    if body.purpose not in VALID_PURPOSES:
        raise HTTPException(status_code=400, detail="유효하지 않은 인증 목적입니다.")

    now = datetime.now(UTC)

    record = await db.scalar(
        select(EmailVerification)
        .where(
            EmailVerification.email == body.email,
            EmailVerification.purpose == body.purpose,
            EmailVerification.consumed_at.is_(None),
        )
        .order_by(EmailVerification.created_at.desc())
    )

    if not record:
        raise HTTPException(status_code=400, detail="유효한 인증 코드가 없어요. 다시 발송해주세요.")

    # 만료
    if record.expires_at.replace(tzinfo=UTC) < now:
        raise HTTPException(status_code=400, detail="인증 코드가 만료됐어요. 다시 발송해주세요.")

    # 시도 횟수 초과
    if record.attempt_count >= settings.email_code_max_attempts:
        record.consumed_at = now  # 무효화
        await db.flush()
        raise HTTPException(status_code=400, detail="시도 횟수를 초과했어요. 다시 발송해주세요.")

    # 코드 불일치
    if record.code != body.code:
        record.attempt_count += 1
        await db.flush()
        remaining = settings.email_code_max_attempts - record.attempt_count
        raise HTTPException(
            status_code=400,
            detail=f"인증 코드가 일치하지 않아요. {remaining}회 남았어요.",
        )

    # 성공 — 코드 소비
    record.consumed_at = now

    if body.purpose == "signup":
        # users.email_verified_at 갱신
        user = await db.scalar(select(User).where(User.email == body.email))
        if user is None:
            await db.flush()
            raise HTTPException(status_code=400, detail="해당 이메일의 계정을 찾을 수 없어요.")
        if user.email_verified_at is None:
            user.email_verified_at = now

        # 토큰 발급 — verify 직후 바로 로그인 상태로
        access_token = create_access_token(user.id)
        refresh_token_str, expires_at = create_refresh_token(user.id)
        db.add(RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=expires_at,
            created_at=now,
        ))
        user.last_login_at = now
        await db.flush()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
        )

    await db.flush()
    return MessageResponse(message="이메일 인증이 완료됐어요.")
