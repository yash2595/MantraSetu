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
    JWT_SECRET_KEY: str = "supersecret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60 * 24
    GOOGLE_CLIENT_ID: str
    class Config:
        env_file = ".env"


settings = Settings()