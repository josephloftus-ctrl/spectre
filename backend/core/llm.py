"""
Unified Ollama LLM client.

Provides consistent interface for:
- Chat completions (for conversational/standup use)
- Text generation (for analysis/structured output)
- Model availability checking
"""
import logging
import requests
from typing import Optional, List, Dict, Any

from .config import settings

logger = logging.getLogger(__name__)


def check_available(model: Optional[str] = None) -> bool:
    """
    Check if Ollama is running and a model is available.

    Args:
        model: Specific model to check, defaults to settings.LLM_MODEL
    """
    target_model = model or settings.LLM_MODEL
    try:
        resp = requests.get(f"{settings.OLLAMA_URL}/api/tags", timeout=5)
        if resp.ok:
            models = [m['name'] for m in resp.json().get('models', [])]
            return any(target_model in m for m in models)
        return False
    except Exception:
        return False


def chat(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    timeout: int = 120
) -> Optional[str]:
    """
    Send a chat request to Ollama using the /api/chat endpoint.

    Best for: conversational responses, multi-turn context, standup content.

    Args:
        prompt: User message content
        system: Optional system prompt
        model: Model to use (defaults to settings.LLM_MODEL)
        temperature: Sampling temperature (0.0-1.0)
        timeout: Request timeout in seconds

    Returns:
        Response content string, or None if request failed
    """
    target_model = model or settings.LLM_MODEL

    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = requests.post(
            f"{settings.OLLAMA_URL}/api/chat",
            json={
                "model": target_model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature}
            },
            timeout=timeout
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")
    except Exception as e:
        logger.error(f"LLM chat request failed: {e}")
        return None


def generate(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 1000,
    temperature: float = 0.3,
    timeout: int = 120
) -> Optional[str]:
    """
    Send a generate request to Ollama using the /api/generate endpoint.

    Best for: structured output, analysis, JSON generation.
    Uses lower default temperature for more consistent/factual output.

    Args:
        prompt: The prompt text
        system: Optional system prompt
        model: Model to use (defaults to settings.ANALYSIS_MODEL)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0-1.0)
        timeout: Request timeout in seconds

    Returns:
        Response content string, or None if request failed
    """
    target_model = model or settings.ANALYSIS_MODEL

    try:
        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }
        if system:
            payload["system"] = system

        resp = requests.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json=payload,
            timeout=timeout
        )
        resp.raise_for_status()
        return resp.json().get('response', '')
    except Exception as e:
        logger.error(f"LLM generate request failed: {e}")
        return None


def embed(text: str, model: Optional[str] = None, timeout: int = 30) -> Optional[List[float]]:
    """
    Generate embedding for text using Ollama.

    Note: This is a convenience wrapper. For batch operations,
    use the embeddings module directly.

    Args:
        text: Text to embed
        model: Model to use (defaults to settings.EMBED_MODEL)
        timeout: Request timeout in seconds

    Returns:
        List of embedding floats, or None if request failed
    """
    target_model = model or settings.EMBED_MODEL

    try:
        resp = requests.post(
            f"{settings.OLLAMA_URL}/api/embeddings",
            json={
                "model": target_model,
                "prompt": text
            },
            timeout=timeout
        )
        resp.raise_for_status()
        return resp.json().get("embedding")
    except Exception as e:
        logger.error(f"LLM embedding request failed: {e}")
        return None
