from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.session import get_db
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
from src.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다.")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(user)
    await db.flush()
    return MessageResponse(message="회원가입이 완료되었습니다.")


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
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

    user = await db.scalar(select(User).where(User.google_id == google_id))
    if not user:
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

    user = await db.scalar(select(User).where(User.kakao_id == kakao_id))
    if not user:
        user = User(kakao_id=kakao_id, email=email, display_name=nickname)
        db.add(user)
        await db.flush()

    return await _issue_tokens(user, db)
