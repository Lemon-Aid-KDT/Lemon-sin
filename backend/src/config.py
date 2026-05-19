from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    postgres_user: str = "lemon"
    postgres_password: str = "lemon1234"
    postgres_db: str = "lemon_aid"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # JWT
    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Social Login
    google_client_id: str | None = None  # Google Cloud Console에서 발급받은 클라이언트 ID

    # ─── Email (Resend) ───
    resend_api_key: str | None = None
    # 발신자 — 도메인 인증 전엔 onboarding@resend.dev 만 가능
    email_from: str = "Lemon Aid <onboarding@resend.dev>"

    # ─── Email Verification 정책 ───
    email_code_ttl_minutes: int = 10            # 코드 유효 시간
    email_code_max_attempts: int = 5             # 같은 코드 틀린 횟수 제한
    email_send_min_interval_seconds: int = 60    # 같은 이메일 재발송 최소 간격
    email_send_daily_limit: int = 5              # 같은 이메일 하루 발송 한도

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
