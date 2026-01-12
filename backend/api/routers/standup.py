"""
Standup API router.
"""
from fastapi import APIRouter, HTTPException, Form, Query
from typing import Optional

from backend.core.standup import (
    get_or_generate_standup, prebake_standup, reroll_section,
    list_cached_standups, get_cached_standup
)

router = APIRouter(prefix="/api/standup", tags=["Standup"])


@router.get("")
def get_standup(date: Optional[str] = Query(None)):
    """
    Get daily standup content (Safety Moment, DEI Moment, Manager Prompt).
    Returns cached content if available, generates fresh if not.
    """
    content = get_or_generate_standup(date)
    return content


@router.get("/cached")
def get_standup_cached_only(date: Optional[str] = Query(None)):
    """Get cached standup content only (returns null if not pre-baked)."""
    content = get_cached_standup(date)
    if not content:
        return {"available": False, "date": date}
    content["available"] = True
    return content


@router.post("/prebake")
def prebake_standup_content(date: Optional[str] = Form(None)):
    """
    Pre-generate and cache standup content for a date.
    Use this for overnight pre-baking of next day's content.
    """
    result = prebake_standup(date)
    return result


@router.post("/reroll/{section}")
def reroll_standup_section(
    section: str,
    topic: Optional[str] = Form(None)
):
    """
    Regenerate a specific standup section.

    Args:
        section: 'safety', 'dei', or 'manager'
        topic: Optional topic hint to focus the content
    """
    if section not in ['safety', 'dei', 'manager']:
        raise HTTPException(status_code=400, detail="Invalid section. Use: safety, dei, manager")

    result = reroll_section(section, topic)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    return {"success": True, "section": section, "content": result}


@router.get("/history")
def get_standup_history():
    """List all cached standup dates."""
    cached = list_cached_standups()
    return {"cached": cached, "count": len(cached)}
