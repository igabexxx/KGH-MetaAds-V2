"""
KGH Meta Ads — Application Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ─── Database ─────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://kgh:password@localhost:5432/kgh_metads"

    # ─── Meta API ─────────────────────────────────────────
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_ACCESS_TOKEN: str = ""
    META_AD_ACCOUNT_ID: str = ""
    META_PAGE_ID: str = ""
    META_API_VERSION: str = "v19.0"

    @property
    def META_API_BASE_URL(self) -> str:
        return f"https://graph.facebook.com/{self.META_API_VERSION}"

    # ─── Security ─────────────────────────────────────────
    API_SECRET_KEY: str = "change-me-in-production"
    WEBHOOK_VERIFY_TOKEN: str = "kgh_webhook_verify"
    CORS_ORIGINS: str = "http://localhost:8000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    # ─── N8N ──────────────────────────────────────────────
    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_USER: str = "admin"
    N8N_PASSWORD: str = ""

    # ─── LLM ──────────────────────────────────────────────
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""

    # ─── Notifications ─────────────────────────────────────
    MESSAGING_PLATFORM: str = "telegram"
    MESSAGING_BOT_TOKEN: str = ""
    MESSAGING_CHAT_ID: str = ""

    # ─── Auth ──────────────────────────────────────────────
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "kgh2024!"      # overridden by env var in production
    JWT_SECRET: str = "kgh-jwt-secret-change-in-prod"
    JWT_EXPIRE_HOURS: int = 12

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
