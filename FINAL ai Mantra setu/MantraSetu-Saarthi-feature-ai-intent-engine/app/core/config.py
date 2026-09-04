"""Application settings and environment configuration."""

from enum import Enum
from functools import lru_cache

from pydantic import AliasChoices, BaseModel, Field
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
    api_base_url: str = Field(default="http://localhost:8000")
    log_level: str = Field(default="INFO")
    cors_origins: str = Field(default="")
    voice_ticket_secret: str = Field(
        validation_alias=AliasChoices("VOICE_TICKET_SECRET", "voice_ticket_secret"),
    )
    jwt_algorithm: str = Field(default="HS256")
    chroma_db_path: str = Field(default="./data/chroma_db")
    embedding_model_name: str = Field(default="paraphrase-multilingual-MiniLM-L12-v2")

    @property
    def cors_origins_list(self) -> list[str]:
        default_dev = [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:3000",
        ]
        if self.cors_origins:
            prod_origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
            return list(dict.fromkeys(default_dev + prod_origins))
        return default_dev

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
