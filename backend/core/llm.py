"""
Unified Claude LLM client.

Provides consistent interface for:
- Chat completions (for conversational/standup use)
- Text generation (for analysis/structured output)
- Streaming chat (for SSE endpoints)
- Model availability checking
"""
import logging
import json
import requests
from typing import Optional, List, Dict, Any, Generator

from .config import settings

logger = logging.getLogger(__name__)

ANTHROPIC_VERSION = "2023-06-01"


def _headers() -> dict:
    """Build headers for Claude API requests."""
    return {
        "Content-Type": "application/json",
        "x-api-key": settings.CLAUDE_API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
    }


def check_available(model: Optional[str] = None) -> bool:
    """
    Check if Claude API is configured and reachable.

    Args:
        model: Ignored (kept for signature compatibility). Availability
               depends on having a valid API key.
    """
    if not settings.CLAUDE_API_KEY:
        return False
    try:
        # Minimal request to verify the key works
        resp = requests.post(
            settings.CLAUDE_API_URL,
            headers=_headers(),
            json={
                "model": settings.CLAUDE_CHAT_MODEL,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "hi"}],
            },
            timeout=10,
        )
        return resp.status_code in (200, 400)  # 400 = valid key, bad request shape is fine
    except Exception:
        return False


def chat(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    timeout: int = 120,
) -> Optional[str]:
    """
    Send a chat request to Claude.

    Best for: conversational responses, multi-turn context, standup content.

    Args:
        prompt: User message content
        system: Optional system prompt
        model: Model to use (defaults to CLAUDE_CHAT_MODEL)
        temperature: Sampling temperature (0.0-1.0)
        timeout: Request timeout in seconds

    Returns:
        Response content string, or None if request failed
    """
    target_model = model or settings.CLAUDE_CHAT_MODEL

    try:
        payload: Dict[str, Any] = {
            "model": target_model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if system:
            payload["system"] = system

        resp = requests.post(
            settings.CLAUDE_API_URL,
            headers=_headers(),
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        # Claude response: {"content": [{"type": "text", "text": "..."}]}
        content_blocks = data.get("content", [])
        return content_blocks[0]["text"] if content_blocks else ""
    except Exception as e:
        logger.error(f"LLM chat request failed: {e}")
        return None


def generate(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 1000,
    temperature: float = 0.3,
    timeout: int = 120,
) -> Optional[str]:
    """
    Send a generation request to Claude.

    Best for: structured output, analysis, JSON generation.
    Uses lower default temperature for more consistent/factual output.

    Args:
        prompt: The prompt text
        system: Optional system prompt
        model: Model to use (defaults to CLAUDE_ANALYSIS_MODEL)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0-1.0)
        timeout: Request timeout in seconds

    Returns:
        Response content string, or None if request failed
    """
    target_model = model or settings.CLAUDE_ANALYSIS_MODEL

    try:
        payload: Dict[str, Any] = {
            "model": target_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if system:
            payload["system"] = system

        resp = requests.post(
            settings.CLAUDE_API_URL,
            headers=_headers(),
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        content_blocks = data.get("content", [])
        return content_blocks[0]["text"] if content_blocks else ""
    except Exception as e:
        logger.error(f"LLM generate request failed: {e}")
        return None


def chat_stream(
    messages: List[Dict[str, str]],
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: int = 120,
) -> Generator[str, None, None]:
    """
    Stream a chat response from Claude. Yields SSE-formatted lines.

    Args:
        messages: List of {"role": ..., "content": ...} dicts
        system: Optional system prompt
        model: Model to use (defaults to CLAUDE_CHAT_MODEL)
        temperature: Sampling temperature
        max_tokens: Maximum tokens
        timeout: Request timeout in seconds

    Yields:
        Raw SSE lines from the Claude streaming API
    """
    target_model = model or settings.CLAUDE_CHAT_MODEL

    # Filter out system messages (Claude uses a separate system field)
    api_messages = [m for m in messages if m.get("role") != "system"]

    payload: Dict[str, Any] = {
        "model": target_model,
        "max_tokens": max_tokens,
        "messages": api_messages,
        "temperature": temperature,
        "stream": True,
    }
    if system:
        payload["system"] = system

    try:
        with requests.post(
            settings.CLAUDE_API_URL,
            headers=_headers(),
            json=payload,
            stream=True,
            timeout=timeout,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                yield line + "\n"
    except Exception as e:
        logger.error(f"LLM stream request failed: {e}")
        yield f'data: {{"type":"error","message":"{str(e)}"}}\n'
