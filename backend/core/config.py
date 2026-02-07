"""
Centralized configuration for the Spectre backend.

All environment variables and settings should be defined here
to avoid duplication across modules.
"""
import os
from functools import lru_cache


class Settings:
    """Application settings loaded from environment variables."""

    # CORS - comma-separated list of allowed origins
    ALLOWED_ORIGINS: list = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:8090,http://localhost:5173,http://127.0.0.1:8090,https://steady.josephloftus.com"
    ).split(",")

    # Database
    DB_PATH: str = os.environ.get("SPECTRE_DB_PATH", "data/spectre.db")

    # Claude API
    CLAUDE_API_KEY: str = os.environ.get("CLAUDE_API_KEY", "")
    CLAUDE_API_URL: str = "https://api.anthropic.com/v1/messages"
    CLAUDE_CHAT_MODEL: str = os.environ.get("CLAUDE_CHAT_MODEL", "claude-haiku-4-5-20251001")
    CLAUDE_ANALYSIS_MODEL: str = os.environ.get("CLAUDE_ANALYSIS_MODEL", "claude-sonnet-4-5-20250929")

    # API key for protecting destructive endpoints (optional)
    API_KEY: str = os.environ.get("SPECTRE_API_KEY", "")

    # File storage
    DATA_DIR: str = os.environ.get("SPECTRE_DATA_DIR", "data")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Singleton instance for easy import
settings = get_settings()
