from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./data/fashion.db"
    cors_allowed_origins: str = "http://localhost:3000"

    crawler_delay_seconds: float = 2.0
    crawler_max_retries: int = 3
    crawler_timeout_seconds: int = 30
    crawler_headless: bool = True

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True
    admin_bearer_token: str | None = None
    gpt_actions_api_key: str | None = None

    discord_webhook_url: str | None = None
    intel_discord_webhook_url: str | None = None
    alert_price_drop_threshold: float = 0.10  # 10% 이상 하락 시 알림
    intel_ingest_enabled: bool = False
    intel_default_time_range_days: int = 7
    push_vapid_public_key: str | None = None
    push_vapid_private_key: str | None = None
    push_vapid_subject: str = "mailto:admin@example.com"
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    gemini_api_key: str | None = None

    @model_validator(mode="after")
    def validate_admin_token(self) -> "Settings":
        token = (self.admin_bearer_token or "").strip()
        is_production_like = not self.api_debug and not self.database_url.startswith("sqlite")
        if is_production_like and (not token or token == "change-me"):
            import warnings
            warnings.warn(
                "ADMIN_BEARER_TOKEN is not set — admin endpoints will be inaccessible",
                RuntimeWarning,
                stacklevel=2,
            )
        return self

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
