from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./data/fashion.db"

    crawler_delay_seconds: float = 2.0
    crawler_max_retries: int = 3
    crawler_timeout_seconds: int = 30
    crawler_headless: bool = True

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True


settings = Settings()
