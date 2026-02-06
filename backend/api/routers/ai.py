"""
AI provider proxy endpoints.
"""
from typing import List, Optional

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.core.config import settings

router = APIRouter(prefix="/api/ai", tags=["AI"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ClaudeChatRequest(BaseModel):
    messages: List[ChatMessage]
    system: Optional[str] = None
    model: Optional[str] = None


@router.get("/claude/status")
def claude_status():
    """Report whether Claude is configured server-side."""
    return {
        "available": bool(settings.CLAUDE_API_KEY),
        "model": settings.CLAUDE_MODEL
    }


def _claude_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "x-api-key": settings.CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01"
    }


def _claude_payload(request: ClaudeChatRequest, stream: bool) -> dict:
    system_prompt = request.system or ""
    model = request.model or settings.CLAUDE_MODEL
    messages = [
        {"role": m.role, "content": m.content}
        for m in request.messages
        if m.role != "system"
    ]
    return {
        "model": model,
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": messages,
        "stream": stream
    }


@router.post("/claude/chat")
def claude_chat(request: ClaudeChatRequest):
    """Proxy non-streaming Claude chat using server-side API key."""
    if not settings.CLAUDE_API_KEY:
        raise HTTPException(status_code=503, detail="Claude API key not configured")

    payload = _claude_payload(request, stream=False)
    try:
        resp = requests.post(
            settings.CLAUDE_API_URL,
            headers=_claude_headers(),
            json=payload,
            timeout=120
        )
        if not resp.ok:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/claude/stream")
def claude_stream(request: ClaudeChatRequest):
    """Proxy streaming Claude chat using server-side API key."""
    if not settings.CLAUDE_API_KEY:
        raise HTTPException(status_code=503, detail="Claude API key not configured")

    payload = _claude_payload(request, stream=True)

    def stream_response():
        try:
            with requests.post(
                settings.CLAUDE_API_URL,
                headers=_claude_headers(),
                json=payload,
                stream=True,
                timeout=120
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    yield line + "\n"
        except Exception as e:
            yield f"data: {{\"type\":\"error\",\"message\":\"{str(e)}\"}}\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")
