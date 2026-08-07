"""Environment-driven settings for Text-to-Speech providers."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class TTSSettings(BaseSettings):
    """Typed Text-to-Speech configuration loaded from environment variables."""

    api_key: SecretStr = Field(default=SecretStr(""))
    base_url: str = Field(default="https://api.fish.audio/v1")
    model: str = Field(default="fish-speech-1")

    # Audio configuration
    audio_format: str = Field(default="mp3")
    sample_rate: int = Field(default=24000, gt=0)

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
        env_prefix="TTS_",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_tts_settings() -> TTSSettings:
    """Return cached TTSSettings instance."""
    return TTSSettings()


tts_settings = get_tts_settings()
