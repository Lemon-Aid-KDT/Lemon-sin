import logging
import secrets
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.session import get_db
from src.models.email_verification import EmailVerification
from src.models.user import RefreshToken, User
from src.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    SignupRequest,
    SocialLoginRequest,
    TokenResponse,
)
from src.services.email import render_verification_email, send_email
from src.utils.rate_limit import RateLimitWindow, enforce_rate_limit
from src.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    """
    이메일/비번 자체 회원가입.

    정책 (CLAUDE.md §10):
      - 같은 이메일이 이미 있으면 409 Conflict 반환.
      - "다른 방식 (구글/카카오) 으로 가입됐어도" 동일 이메일이면 차단.
      - 다른 이메일이면 별개 계정 OK.
      - 가입 직후 이메일 인증 코드 자동 발송 (rate-limit 적용).
    """
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_duplicate_email_message(existing),
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(user)
    await db.flush()

    # 인증 코드 자동 발송. 발송 실패해도 가입은 유지 — 사용자가 verify 화면에서 재발송 가능.
    try:
        await _create_and_send_verification_code(
            email=body.email,
            purpose="signup",
            user_id=user.id,
            db=db,
        )
    except HTTPException:
        # rate-limit 등 사용자에게 알려야 하는 에러는 그대로 전파
        raise
    except Exception as e:
        logger.warning("[signup] verification email send failed: %s", e)
        # 발송 실패해도 가입은 성공 — 클라이언트에서 verify 화면 진입 후 재발송 시도 가능

    return MessageResponse(message="회원가입이 완료되었어요. 이메일로 인증 코드를 보냈어요.")


async def _create_and_send_verification_code(
    *,
    email: str,
    purpose: str,
    user_id: int | None,
    db: AsyncSession,
) -> None:
    """공통 — 인증 코드 생성 + 발송 + DB 기록. rate-limit 적용."""
    await enforce_rate_limit(
        action=f"email_send:{purpose}",
        identifier=email,
        windows=[
            RateLimitWindow("minute", settings.email_send_min_interval_seconds, 1),
            RateLimitWindow("day", 86400, settings.email_send_daily_limit),
        ],
        user_friendly_action="이메일 인증 코드 발송",
    )

    code = f"{secrets.randbelow(1_000_000):06d}"
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.email_code_ttl_minutes)

    # 같은 (email, purpose) 의 이전 미사용 코드는 무효화
    await db.execute(
        update(EmailVerification)
        .where(
            EmailVerification.email == email,
            EmailVerification.purpose == purpose,
            EmailVerification.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )

    db.add(EmailVerification(
        user_id=user_id,
        email=email,
        code=code,
        purpose=purpose,
        created_at=now,
        expires_at=expires,
        attempt_count=0,
    ))
    await db.flush()

    subject, html = render_verification_email(code=code, purpose=purpose)
    await send_email(to=email, subject=subject, html=html)


def _duplicate_email_message(existing: User) -> str:
    """이메일 충돌 안내 메시지 — 어떤 방식으로 가입돼 있는지 알려주면 사용자 친화적."""
    if existing.google_id:
        return "이미 구글로 가입된 이메일이에요. 구글로 로그인해주세요."
    if existing.kakao_id:
        return "이미 카카오로 가입된 이메일이에요. 카카오로 로그인해주세요."
    if existing.password_hash:
        return "이미 이메일로 가입된 계정이에요. 로그인해주세요."
    return "이미 사용 중인 이메일이에요."


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    # 로그인 시도 횟수 제한 (10분에 5회) — 무차별 대입 방지
    await enforce_rate_limit(
        action="login_attempt",
        identifier=body.email,
        windows=[RateLimitWindow("ten_min", 600, 5)],
        user_friendly_action="로그인",
    )

    user = await db.scalar(
        select(User).where(User.email == body.email, User.deleted_at.is_(None))
    )
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    access_token = create_access_token(user.id)
    refresh_token_str, expires_at = create_refresh_token(user.id)

    db.add(RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=expires_at,
        created_at=datetime.now(UTC),
    ))

    user.last_login_at = datetime.now(UTC)
    await db.flush()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token_str)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

    stored = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token == body.refresh_token,
            RefreshToken.revoked.is_(False),
        )
    )
    if not stored or stored.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="만료되었거나 무효화된 토큰입니다.")

    return AccessTokenResponse(access_token=create_access_token(stored.user_id))


@router.post("/logout", response_model=MessageResponse)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.token == body.refresh_token)
    )
    if stored:
        stored.revoked = True
        await db.flush()
    return MessageResponse(message="로그아웃되었습니다.")


async def _issue_tokens(user: User, db: AsyncSession) -> TokenResponse:
    """소셜 로그인 공통: JWT 토큰 발급 및 last_login_at 갱신"""
    access_token = create_access_token(user.id)
    refresh_token_str, expires_at = create_refresh_token(user.id)
    db.add(RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=expires_at,
        created_at=datetime.now(UTC),
    ))
    user.last_login_at = datetime.now(UTC)
    await db.flush()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token_str)


@router.post("/google", response_model=TokenResponse)
async def google_login(body: SocialLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Flutter google_sign_in 패키지가 발급한 id_token을 받아 구글 서버에서 검증합니다.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": body.token},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="유효하지 않은 Google 토큰입니다.")

    data = resp.json()

    # 우리 앱 클라이언트 ID와 일치하는지 확인
    if settings.google_client_id and data.get("aud") != settings.google_client_id:
        raise HTTPException(status_code=401, detail="토큰 발급처가 일치하지 않습니다.")

    google_id = data["sub"]  # 구글 고유 사용자 ID
    email = data.get("email")
    display_name = data.get("name")

    # 1. 같은 google_id 면 기존 사용자 → 로그인 (자동 매칭)
    user = await db.scalar(select(User).where(User.google_id == google_id))
    if user:
        return await _issue_tokens(user, db)

    # 2. 신규 가입 — 같은 이메일이 다른 방식으로 이미 있으면 차단 (정책 2026-05-13)
    if email:
        existing = await db.scalar(select(User).where(User.email == email))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_duplicate_email_message(existing),
            )

    # 3. 진짜 신규 — 생성
    user = User(google_id=google_id, email=email, display_name=display_name)
    db.add(user)
    await db.flush()

    return await _issue_tokens(user, db)


@router.post("/kakao", response_model=TokenResponse)
async def kakao_login(body: SocialLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Flutter kakao_flutter_sdk가 발급한 access_token을 받아 카카오 서버에서 사용자 정보를 조회합니다.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {body.token}"},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="유효하지 않은 Kakao 토큰입니다.")

    data = resp.json()
    kakao_id = str(data["id"])  # 카카오 고유 사용자 ID

    kakao_account = data.get("kakao_account", {})
    email = kakao_account.get("email")
    nickname = kakao_account.get("profile", {}).get("nickname")

    # 1. 같은 kakao_id 면 기존 사용자 → 로그인 (자동 매칭)
    user = await db.scalar(select(User).where(User.kakao_id == kakao_id))
    if user:
        return await _issue_tokens(user, db)

    # 2. 신규 가입 — 같은 이메일이 다른 방식으로 이미 있으면 차단 (정책 2026-05-13)
    #    카카오 이메일 동의 미수락 시 email=None — 그땐 차단 안 함 (kakao_id 만으로 신규 생성)
    if email:
        existing = await db.scalar(select(User).where(User.email == email))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_duplicate_email_message(existing),
            )

    # 3. 진짜 신규 — 생성
    user = User(kakao_id=kakao_id, email=email, display_name=nickname)
    db.add(user)
    await db.flush()

    return await _issue_tokens(user, db)
