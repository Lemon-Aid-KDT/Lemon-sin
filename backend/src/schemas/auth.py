from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    # OAuth (카카오/구글) 로그인 시 — 이번에 처음 가입한 사용자면 True.
    # 이메일 로그인 등 해당 없는 경우 None (응답에서 생략).
    # 프론트: True → 회원가입 10-step 진입, False → 바로 홈.
    is_new_user: bool | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class SocialLoginRequest(BaseModel):
    token: str
