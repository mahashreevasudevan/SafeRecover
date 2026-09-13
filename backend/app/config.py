from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SafeRecover API"
    database_url: str = "sqlite:///./saferecover.db"
    cors_origins: str = "http://localhost:5173"
    n8n_retry_webhook_url: str | None = None
    n8n_timeout_seconds: float = 5.0
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash-lite"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
