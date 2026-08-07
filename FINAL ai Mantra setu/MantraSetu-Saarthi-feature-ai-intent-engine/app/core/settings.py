"""Centralized Application Configuration Module for MantraSetu AgentOS.

This module is the single source of truth for all backend configuration settings across AI, RAG, Browser,
Navigation, Conversation, Orchestrator, API, and Health subsystems.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Enumeration of supported deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class BaseSettingsModel(BaseModel):
    """Immutable base Pydantic v2 sub-configuration model."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class ApplicationConfig(BaseSettingsModel):
    """Application metadata and environment settings.

    Attributes:
        application_name: Global application name string.
        version: Application semantic version string.
        environment: Environment enum value.
        debug: Boolean flag enabling debug mode.
    """

    application_name: str = Field(
        default="MantraSetu AgentOS",
        description="Global application name string.",
    )
    version: str = Field(
        default="1.0.0",
        description="Application semantic version string.",
    )
    environment: Environment = Field(
        default=Environment.PRODUCTION,
        description="Environment enum value.",
    )
    debug: bool = Field(
        default=False,
        description="Boolean flag enabling debug mode.",
    )


class ServerSettings(BaseSettingsModel):
    """HTTP server and network listener configuration settings.

    Attributes:
        host: Host network interface address string.
        port: Listening network port number (1-65535).
        workers: Worker process count (>=1).
        timeout: Server socket timeout in seconds (>0).
    """

    host: str = Field(
        default="0.0.0.0",
        description="Host network interface address string.",
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Listening network port number (1-65535).",
    )
    workers: int = Field(
        default=4,
        ge=1,
        description="Worker process count.",
    )
    timeout: float = Field(
        default=30.0,
        gt=0.0,
        description="Server socket timeout in seconds.",
    )


class AISettings(BaseSettingsModel):
    """AI inference provider backend settings.

    Attributes:
        provider: Provider key identifier string.
        base_url: Provider REST base URL string.
        default_model: Default AI model identifier string.
        temperature: Generation temperature sampling parameter (0.0 to 2.0).
        max_tokens: Maximum token generation limit (>=1).
        timeout: Provider API timeout in seconds (>0).
        retry_count: Retry attempt count (>=0).
        streaming_enabled: Boolean flag enabling token streaming.
        api_key: Optional provider API key string.
    """

    provider: str = Field(
        default="mock",
        description="Provider key identifier string.",
    )
    base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="Provider REST base URL string.",
    )
    default_model: str = Field(
        default="qwen-max",
        description="Default AI model string.",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Generation temperature parameter.",
    )
    max_tokens: int = Field(
        default=2048,
        ge=1,
        description="Maximum token generation limit.",
    )
    timeout: float = Field(
        default=30.0,
        gt=0.0,
        description="Provider API timeout in seconds.",
    )
    retry_count: int = Field(
        default=3,
        ge=0,
        description="Retry attempt count.",
    )
    streaming_enabled: bool = Field(
        default=True,
        description="Boolean flag enabling token streaming.",
    )
    api_key: str | None = Field(
        default=None,
        description="Optional provider API key string.",
    )


class RAGSettings(BaseSettingsModel):
    """RAG subsystem vector store and embedding configuration settings.

    Attributes:
        embedding_model: Embedding model identifier string.
        vector_database_uri: Vector database connection URI string.
        top_k: Top K nearest neighbor vector results limit (>=1).
        similarity_threshold: Minimum vector similarity score threshold (0.0 to 1.0).
        chunk_size: Maximum token/character size per chunk (>0).
        chunk_overlap: Overlapping characters count between adjacent chunks (>=0).
        reranker_enabled: Boolean flag enabling post-retrieval reranking.
        vector_namespace: Vector collection namespace string.
        data_directory: Storage directory Path.
    """

    embedding_model: str = Field(
        default="text-embedding-v3",
        description="Embedding model identifier string.",
    )
    vector_database_uri: str = Field(
        default="memory://",
        description="Vector database connection URI string.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Top K vector search results limit.",
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum vector similarity score threshold.",
    )
    chunk_size: int = Field(
        default=512,
        gt=0,
        description="Maximum character size per chunk.",
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        description="Overlapping characters count between adjacent chunks.",
    )
    reranker_enabled: bool = Field(
        default=False,
        description="Boolean flag enabling post-retrieval reranking.",
    )
    vector_namespace: str = Field(
        default="default",
        description="Vector collection namespace string.",
    )
    data_directory: Path = Field(
        default_factory=lambda: Path("./data"),
        validate_default=True,
        description="Storage directory Path.",
    )

    @field_validator("data_directory", mode="after")
    @classmethod
    def _validate_data_dir(cls, v: Path) -> Path:
        """Ensure data directory exists or create it automatically.

        Args:
            v: Input Path.

        Returns:
            Path: Validated directory Path.
        """
        v.mkdir(parents=True, exist_ok=True)
        return v


class BrowserSettings(BaseSettingsModel):
    """Browser automation subsystem configuration settings.

    Attributes:
        headless: Boolean flag enabling headless execution mode.
        navigation_timeout: Page navigation timeout in seconds (>0).
        action_timeout: Action execution timeout in seconds (>0).
        viewport_width: Viewport width in pixels (>0).
        viewport_height: Viewport height in pixels (>0).
        download_directory: Download directory Path.
        user_agent: Optional custom User-Agent string.
        slow_mo: Action delay in seconds for debugging (>=0).
    """

    headless: bool = Field(
        default=True,
        description="Boolean flag enabling headless mode.",
    )
    navigation_timeout: float = Field(
        default=30.0,
        gt=0.0,
        description="Page navigation timeout in seconds.",
    )
    action_timeout: float = Field(
        default=15.0,
        gt=0.0,
        description="Action execution timeout in seconds.",
    )
    viewport_width: int = Field(
        default=1280,
        gt=0,
        description="Viewport width in pixels.",
    )
    viewport_height: int = Field(
        default=720,
        gt=0,
        description="Viewport height in pixels.",
    )
    download_directory: Path = Field(
        default_factory=lambda: Path("./downloads"),
        validate_default=True,
        description="Download directory Path.",
    )
    user_agent: str | None = Field(
        default=None,
        description="Optional custom User-Agent string.",
    )
    slow_mo: float = Field(
        default=0.0,
        ge=0.0,
        description="Action delay in seconds for debugging.",
    )

    @field_validator("download_directory", mode="after")
    @classmethod
    def _validate_download_dir(cls, v: Path) -> Path:
        """Ensure download directory exists or create it automatically.

        Args:
            v: Input Path.

        Returns:
            Path: Validated directory Path.
        """
        v.mkdir(parents=True, exist_ok=True)
        return v


class APISettings(BaseSettingsModel):
    """REST API route and security configuration settings.

    Attributes:
        prefix: REST API route path prefix string.
        rate_limit_per_minute: Maximum requests allowed per minute (>0).
        request_timeout: HTTP request processing timeout in seconds (>0).
        max_request_size: Maximum request payload size in bytes (>0).
        cors_origins: Tuple of allowed CORS origin strings.
        trusted_hosts: Tuple of allowed HTTP host strings.
        allowed_methods: Tuple of allowed HTTP methods strings.
        allowed_headers: Tuple of allowed HTTP headers strings.
    """

    prefix: str = Field(
        default="/api/v1",
        description="REST API route path prefix string.",
    )
    rate_limit_per_minute: int = Field(
        default=60,
        gt=0,
        description="Maximum requests allowed per minute.",
    )
    request_timeout: float = Field(
        default=30.0,
        gt=0.0,
        description="HTTP request processing timeout in seconds.",
    )
    max_request_size: int = Field(
        default=10_485_760,
        gt=0,
        description="Maximum request payload size in bytes.",
    )
    cors_origins: tuple[str, ...] = Field(
        default=("*",),
        description="Tuple of allowed CORS origin strings.",
    )
    trusted_hosts: tuple[str, ...] = Field(
        default=("*",),
        description="Tuple of allowed HTTP host strings.",
    )
    allowed_methods: tuple[str, ...] = Field(
        default=("GET", "POST", "PUT", "DELETE", "OPTIONS"),
        description="Tuple of allowed HTTP methods strings.",
    )
    allowed_headers: tuple[str, ...] = Field(
        default=("*",),
        description="Tuple of allowed HTTP headers strings.",
    )


class HealthSettings(BaseSettingsModel):
    """Health monitoring subsystem configuration settings.

    Attributes:
        health_check_timeout: Component health probe timeout in seconds (>0).
        cache_ttl: Health check result cache time-to-live in seconds (>0).
    """

    health_check_timeout: float = Field(
        default=5.0,
        gt=0.0,
        description="Component health check probe timeout in seconds.",
    )
    cache_ttl: float = Field(
        default=10.0,
        gt=0.0,
        description="Health check result cache time-to-live in seconds.",
    )


class ApplicationSettings(BaseSettings):
    """Root Application Configuration Settings loaded from environment variables and config files.

    Attributes:
        app: ApplicationConfig submodel.
        server: ServerSettings submodel.
        ai: AISettings submodel.
        rag: RAGSettings submodel.
        browser: BrowserSettings submodel.
        api: APISettings submodel.
        health: HealthSettings submodel.
    """

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    app: ApplicationConfig = Field(default_factory=ApplicationConfig)
    server: ServerSettings = Field(default_factory=ServerSettings)
    ai: AISettings = Field(default_factory=AISettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    api: APISettings = Field(default_factory=APISettings)
    health: HealthSettings = Field(default_factory=HealthSettings)


def load_settings(
    env_file: str | Path | None = None,
) -> ApplicationSettings:
    """Instantiate and validate an immutable ApplicationSettings object.

    Args:
        env_file: Optional explicit path to an environment configuration file.

    Returns:
        ApplicationSettings: Fully validated application configuration settings object.
    """
    if env_file is not None:
        path = Path(env_file)
        if path.is_file():
            return ApplicationSettings(_env_file=path)

    return ApplicationSettings()
