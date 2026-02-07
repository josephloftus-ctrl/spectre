"""
AI provider proxy endpoints.
Routes all frontend AI requests through the backend using server-side API key.
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.core.config import settings
from backend.core import llm

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
        "model": settings.CLAUDE_CHAT_MODEL,
        "analysis_model": settings.CLAUDE_ANALYSIS_MODEL,
    }


@router.post("/claude/chat")
def claude_chat(request: ClaudeChatRequest):
    """Proxy non-streaming Claude chat using server-side API key."""
    if not settings.CLAUDE_API_KEY:
        raise HTTPException(status_code=503, detail="Claude API key not configured")

    # Build messages list for the chat function
    prompt = "\n".join(
        m.content for m in request.messages if m.role == "user"
    )
    # Use last user message as the prompt
    last_user = next(
        (m.content for m in reversed(request.messages) if m.role == "user"), ""
    )

    result = llm.chat(
        prompt=last_user,
        system=request.system,
        model=request.model or settings.CLAUDE_CHAT_MODEL,
    )

    if result is None:
        raise HTTPException(status_code=500, detail="Claude request failed")

    # Return in Claude API response format for frontend compatibility
    return {
        "content": [{"type": "text", "text": result}],
        "model": request.model or settings.CLAUDE_CHAT_MODEL,
        "role": "assistant",
    }


@router.post("/claude/stream")
def claude_stream(request: ClaudeChatRequest):
    """Proxy streaming Claude chat using server-side API key."""
    if not settings.CLAUDE_API_KEY:
        raise HTTPException(status_code=503, detail="Claude API key not configured")

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    def stream_response():
        yield from llm.chat_stream(
            messages=messages,
            system=request.system,
            model=request.model or settings.CLAUDE_CHAT_MODEL,
        )

    return StreamingResponse(stream_response(), media_type="text/event-stream")
