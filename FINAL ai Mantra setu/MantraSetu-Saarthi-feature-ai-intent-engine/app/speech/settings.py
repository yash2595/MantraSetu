"""Environment-driven settings for Speech-to-Text providers."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SpeechSettings(BaseSettings):
    """Typed Speech-to-Text configuration loaded from environment variables."""


    base_url: str = Field(default="https://api.openai.com/v1")
    model: str = Field(default="whisper-1")
    # OpenAI API key for Whisper (use OPENAI_API_KEY env var)
    api_key: SecretStr = Field(default=SecretStr(""), env="OPENAI_API_KEY")

    # Timeout settings in seconds
    timeout_connect: float = Field(default=10.0, gt=0)
    timeout_read: float = Field(default=60.0, gt=0)
    timeout_write: float = Field(default=10.0, gt=0)
    timeout_pool: float = Field(default=10.0, gt=0)

    # Retry configuration
    max_retries: int = Field(default=2, ge=0)
    retry_backoff_seconds: float = Field(default=2.0, ge=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",

        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_speech_settings() -> SpeechSettings:
    """Return cached SpeechSettings instance."""
    return SpeechSettings()


speech_settings = get_speech_settings()
