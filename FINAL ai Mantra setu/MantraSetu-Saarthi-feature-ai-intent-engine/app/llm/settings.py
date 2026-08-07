from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    provider: str = Field(default="gemini")

    # Required
    api_key: SecretStr | None = Field(
        default=None,
        validation_alias="GEMINI_API_KEY",
        description="Gemini API Key",
    )

    base_url: str = Field(default="https://generativelanguage.googleapis.com/v1beta")
    model: str = Field(default="gemini-3.5-flash-lite")

    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=1024)

    app_name: str = Field(default="MantraSetu AI Backend")
    app_url: str = Field(default="http://localhost:8000")

    timeout_connect: float = Field(default=10.0, gt=0)
    timeout_read: float = Field(default=60.0, gt=0)
    timeout_write: float = Field(default=10.0, gt=0)
    timeout_pool: float = Field(default=10.0, gt=0)

    max_retries: int = Field(default=2, ge=0)
    retry_backoff_seconds: float = Field(default=2.0, ge=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_llm_settings() -> LLMSettings:
    return LLMSettings()


llm_settings = get_llm_settings()