"""
Application configuration using Pydantic Settings.

Loads environment variables from .env file and provides
typed access to all configuration values throughout the app.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All values can be overridden via .env file or environment variables.
    Default values are provided for development convenience.
    """

    # --- Application ---
    APP_NAME: str = "AI StudyMate"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # --- Database ---
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/studymate"

    # --- Security ---
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production-minimum-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # --- LLM Provider ---
    LLM_PROVIDER: str = "groq"  # groq, openai, gemini
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL_NAME: str = "llama-3.1-8b-instant"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash-lite"
    OPENAI_API_KEY: Optional[str] = None

    # --- Vector Database ---
    VECTOR_DB_PATH: str = "./data/chromadb"
    HF_API_TOKEN: Optional[str] = None

    # --- File Storage ---
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB in bytes

    # --- Voice Services ---
    SPEECHMATICS_API_KEY: Optional[str] = None
    STT_PROVIDER: str = "speechmatics"  # speechmatics, whisper

    class Config:
        """Pydantic settings configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton settings instance
# Import this wherever configuration is needed
settings = Settings()
