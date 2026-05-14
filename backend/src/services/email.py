"""이메일 발송 — Resend API.

Resend HTTP API:
  POST https://api.resend.com/emails
  Authorization: Bearer {RESEND_API_KEY}
  {
    "from": "Lemon Aid <onboarding@resend.dev>",
    "to": ["user@example.com"],
    "subject": "...",
    "html": "..."
  }

RESEND_API_KEY 가 없으면 (개발 초기) 콘솔에만 출력하고 200 OK 처리 — 흐름 막지 않음.
"""
from __future__ import annotations

import logging

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send_email(*, to: str, subject: str, html: str) -> None:
    """Resend 로 이메일 발송. 실패 시 RuntimeError."""
    if not settings.resend_api_key:
        # 개발 초기 / API 키 미설정 — 콘솔에 코드만 출력.
        # 운영 빌드에선 RESEND_API_KEY 가 반드시 설정돼야 함.
        logger.warning(
            "[email] RESEND_API_KEY not set — printing instead of sending. "
            "to=%s subject=%s body=%s",
            to, subject, _strip_html(html),
        )
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.email_from,
                "to": [to],
                "subject": subject,
                "html": html,
            },
        )
    if resp.status_code >= 400:
        # 에러 본문은 dev 로그에만 (외부 노출 금지)
        logger.error("[email] Resend send failed: %s %s", resp.status_code, resp.text)
        raise RuntimeError("이메일 발송에 실패했어요. 잠시 후 다시 시도해주세요.")


def _strip_html(html: str) -> str:
    """로그에서 HTML 태그 대충 제거 — dev 콘솔 가독성용."""
    import re
    return re.sub(r"<[^>]+>", " ", html).strip()


# ─── 템플릿 ───

def render_verification_email(*, code: str, purpose: str) -> tuple[str, str]:
    """이메일 인증 코드 메일 — (제목, html) 반환."""
    if purpose == "password_reset":
        title = "비밀번호 찾기"
        intro = "비밀번호 찾기 요청을 받았어요. 아래 인증 코드를 입력해주세요."
    else:
        title = "이메일 인증"
        intro = "Lemon Aid 가입을 환영해요. 아래 인증 코드를 앱에 입력해주세요."

    subject = f"[Lemon Aid] {title} 인증 코드: {code}"

    html = f"""\
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#F5F6F8;font-family:'Pretendard',-apple-system,sans-serif;color:#191F28;">
  <div style="max-width:480px;margin:0 auto;padding:40px 24px;">
    <div style="background:#FFFFFF;border-radius:16px;padding:32px 24px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
      <h1 style="margin:0 0 12px;font-size:22px;font-weight:700;letter-spacing:-0.5px;">{title}</h1>
      <p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#4E5968;">{intro}</p>

      <div style="background:#F5F6F8;border-radius:12px;padding:20px;text-align:center;margin:0 0 24px;">
        <div style="font-size:32px;font-weight:800;letter-spacing:8px;color:#4C7EF7;font-family:'SF Mono',Monaco,monospace;">
          {code}
        </div>
      </div>

      <p style="margin:0 0 8px;font-size:13px;color:#8B95A1;">
        · 코드는 10분 동안 유효해요.<br>
        · 본인이 요청하지 않았다면 이 메일은 무시해주세요.
      </p>
    </div>
    <p style="margin:24px 0 0;font-size:12px;color:#8B95A1;text-align:center;">
      © Lemon Aid · 만성질환자용 AI 영양·복약 관리
    </p>
  </div>
</body>
</html>"""
    return subject, html
