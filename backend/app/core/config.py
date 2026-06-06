"""Application configuration."""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """App settings, loaded from environment variables or .env file."""

    # App
    APP_NAME: str = "AI Novel-to-Script Tool"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    # File Storage
    UPLOAD_DIR: Path = Path("./data/uploads")
    OUTPUT_DIR: Path = Path("./data/outputs")
    SAMPLE_DIR: Path = Path("./data/samples")
    MAX_UPLOAD_SIZE_MB: int = 50

    # AI / LLM
    LLM_PROVIDER: str = "anthropic"  # "anthropic" | "openai" | "qwen" | "deepseek"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"  # default model
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    QWEN_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-v4-pro"

    # LLM params
    LLM_MAX_TOKENS: int = 8192
    LLM_TEMPERATURE: float = 0.7

    # Chapter Processing
    MAX_CHAPTER_LENGTH: int = 8000  # max chars per chapter chunk
    CHAPTER_OVERLAP: int = 200      # overlap between chunks

    # Auth (simple)
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24h

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
