from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "MantraSetu"
    APP_VERSION: str = "0.1.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    WHISPER_MODEL: str = "whisper-1"
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "mantrasetu"
    AI_SERVICE_URL: str = "http://localhost:8002/api/v1"
    AI_SERVICE_TIMEOUT_SECONDS: float = 15.0
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60 * 24
    VOICE_TICKET_SECRET: str = "mantrasetu_voice_ticket_secret_shared_2026"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    ADMIN_SECRET_KEY: str = "mantrasetu-admin-secret"
    CORS_ORIGINS: str = ""
    
    # Email Settings
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None

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
        if self.CORS_ORIGINS:
            prod_origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
            return list(dict.fromkeys(default_dev + prod_origins))
        return default_dev

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()