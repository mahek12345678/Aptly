import logging
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Resolve .env relative to the backend/ directory (parent of app/core/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = str(_BACKEND_DIR / ".env")


class Settings(BaseSettings):
    PROJECT_NAME: str = "Aptly"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Database (PostgreSQL with asyncpg)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aptly_db"

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""

    # JWT
    JWT_SECRET_KEY: str = "aptly-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    FRONTEND_URL: str = "http://localhost:5173"

    # Resume Storage
    RESUME_UPLOAD_DIR: Path = _BACKEND_DIR / "uploads" / "resumes"

    # ChromaDB & Vector Store
    CHROMA_PERSIST_DIR: Path = _BACKEND_DIR / "chroma_data"
    CHROMA_COLLECTION_NAME: str = "aptly_resumes"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    # LLM Service Configuration (Groq)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_PROVIDER: str = "groq"
    # Voice Assistant configuration
    ASSISTANT_SPEECH_LIMIT: int = Field(default=5, validation_alias="ASSISTANT_SPEECH_LIMIT")
    ASSISTANT_SPEECH_WINDOW_SECONDS: int = Field(default=60, validation_alias="ASSISTANT_SPEECH_WINDOW_SECONDS")
    ELEVENLABS_API_KEY: str = Field(default="", validation_alias="ELEVENLABS_API_KEY")
    ELEVENLABS_VOICE_ID: str = Field(default="", validation_alias="ELEVENLABS_VOICE_ID")
    ELEVENLABS_MODEL_ID: str = Field(default="eleven_multilingual_v2", validation_alias="ELEVENLABS_MODEL_ID")

    # Job Provider configuration
    JOB_PROVIDER: str = Field(default="adzuna", validation_alias="JOB_PROVIDER")
    JOB_PROVIDER_API_KEY: str = Field(default="", validation_alias="JOB_PROVIDER_API_KEY")
    JOB_PROVIDER_BASE_URL: str = Field(
        default="https://api.adzuna.com/v1/api/jobs",
        validation_alias="JOB_PROVIDER_BASE_URL",
    )
    JOB_PROVIDER_LIMIT: int = Field(default=50, validation_alias="JOB_PROVIDER_LIMIT")

    # Adzuna Provider Credentials & Parameters
    ADZUNA_APP_ID: str = Field(default="", validation_alias="ADZUNA_APP_ID")
    ADZUNA_APP_KEY: str = Field(default="", validation_alias="ADZUNA_APP_KEY")
    ADZUNA_COUNTRY: str = Field(default="in", validation_alias="ADZUNA_COUNTRY")
    ADZUNA_RESULTS_PER_PAGE: int = Field(default=15, validation_alias="ADZUNA_RESULTS_PER_PAGE")
    ADZUNA_MAX_PAGES_PER_QUERY: int = Field(default=1, validation_alias="ADZUNA_MAX_PAGES_PER_QUERY")
    ADZUNA_QUERIES: List[str] = Field(
        default=[
            "software engineer",
            "backend engineer",
            "frontend engineer",
            "data analyst",
            "data scientist",
            "machine learning engineer",
            "AI engineer",
            "product engineer",
            "intern software engineer",
        ],
        validation_alias="ADZUNA_QUERIES",
    )

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_BEAT_REFRESH_HOUR: int = 3
    CELERY_BEAT_REFRESH_MINUTE: int = 0
    CELERY_BEAT_RANK_HOUR: int = 3
    CELERY_BEAT_RANK_MINUTE: int = 30

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

