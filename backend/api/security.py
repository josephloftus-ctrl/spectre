"""
Simple API key dependency for protecting destructive endpoints.
"""
from typing import Optional

from fastapi import Header, HTTPException

from backend.core.config import settings


def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """Require a matching API key when SPECTRE_API_KEY is configured."""
    if not settings.API_KEY:
        return
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
