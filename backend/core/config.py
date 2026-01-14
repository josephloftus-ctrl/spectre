"""
Centralized configuration for the Spectre backend.

All environment variables and settings should be defined here
to avoid duplication across modules.
"""
import os
from functools import lru_cache


class Settings:
    """Application settings loaded from environment variables."""

    # Ollama configuration
    OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://localhost:11434")

    # AI Models
    LLM_MODEL: str = "granite4:3b"
    EMBED_MODEL: str = "nomic-embed-text:v1.5"
    ANALYSIS_MODEL: str = "granite4:3b"

    # CORS - comma-separated list of allowed origins
    ALLOWED_ORIGINS: list = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:8090,http://localhost:5173,http://127.0.0.1:8090,https://steady.josephloftus.com"
    ).split(",")

    # Database
    DB_PATH: str = os.environ.get("SPECTRE_DB_PATH", "data/spectre.db")

    # File storage
    DATA_DIR: str = os.environ.get("SPECTRE_DATA_DIR", "data")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Singleton instance for easy import
settings = get_settings()
