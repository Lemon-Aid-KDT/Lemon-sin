"""이메일 인증 코드 (회원가입·비번 찾기 공용)"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 어떤 유저 — null 가능 (signup 단계엔 user 없을 수도, 비번찾기는 user 있음)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False)  # 6자리 숫자
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)  # 'signup' | 'password_reset'

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 시도 횟수 — 같은 코드 5회 틀리면 무효
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
