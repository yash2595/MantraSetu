"""Application settings and environment configuration."""

from enum import Enum
from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevelEnum(str, Enum):
    """Log level choices enum."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggingSettings(BaseModel):
    """Nested logging settings."""

    level: LogLevelEnum = Field(default=LogLevelEnum.INFO)


class ApplicationSettings(BaseModel):
    """Nested application settings."""

    app_name: str = Field(default="MantraSetu AI Assistant")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    api_v1_prefix: str = Field(default="/api/v1")


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables."""

    app_name: str = Field(default="MantraSetu AI Assistant")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    api_v1_prefix: str = Field(default="/api/v1")
    log_level: str = Field(default="INFO")

    application: ApplicationSettings = Field(default_factory=ApplicationSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


settings = get_settings()
