"""
Memory and Day At A Glance API router.
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Form, Query
from typing import Optional
import uuid

from backend.core import llm
from backend.core.memory import (
    get_today_items, get_upcoming_items, search_memory, embed_note
)
from backend.core.analysis import get_recent_anomalies

router = APIRouter(tags=["Memory"])


# ============== Day At A Glance API ==============

@router.get("/api/glance")
def day_at_a_glance(date: Optional[str] = Query(None)):
    """
    Get Day At A Glance data for a specific date.
    Returns schedules, notes, people working, and tags for the day.

    Args:
        date: ISO date string (YYYY-MM-DD), defaults to today
    """
    items = get_today_items(date)
    if items.get("error"):
        raise HTTPException(status_code=500, detail=items["error"])
    return items


@router.get("/api/glance/upcoming")
def upcoming_glance(days: int = Query(7, le=30)):
    """Get Day At A Glance data for the upcoming days."""
    items = get_upcoming_items(days)
    return {"days": items, "count": len(items)}


@router.get("/api/glance/briefing")
def ai_briefing(date: Optional[str] = Query(None)):
    """
    Generate an AI-powered morning briefing.
    Combines schedule, notes, and insights into a summary.
    """
    target_date = date or datetime.now().strftime('%Y-%m-%d')

    today_items = get_today_items(target_date)
    anomalies = get_recent_anomalies(limit=5)

    briefing = {
        "date": target_date,
        "schedule_count": len(today_items.get("schedules", [])),
        "note_count": len(today_items.get("notes", [])),
        "people_working": today_items.get("people_working", []),
        "tags": today_items.get("tags", []),
        "recent_anomalies": anomalies[:3] if anomalies else [],
        "summary": None
    }

    try:
        prompt_parts = [f"Today is {target_date}. Give a brief morning briefing."]

        if briefing["people_working"]:
            prompt_parts.append(f"Staff working: {', '.join(briefing['people_working'])}")

        if briefing["schedule_count"]:
            prompt_parts.append(f"There are {briefing['schedule_count']} schedule entries.")

        if briefing["note_count"]:
            prompt_parts.append(f"There are {briefing['note_count']} notes to review.")

        if briefing["recent_anomalies"]:
            anomaly_texts = [a.get("summary", "Issue detected") for a in briefing["recent_anomalies"]]
            prompt_parts.append(f"Recent issues: {'; '.join(anomaly_texts)}")

        prompt = " ".join(prompt_parts) + " Keep it under 100 words."

        summary = llm.generate(prompt, max_tokens=200, temperature=0.5)
        if summary:
            briefing["summary"] = summary.strip()

    except Exception as e:
        briefing["summary"] = f"Unable to generate AI summary: {str(e)}"

    return briefing


# ============== Memory Note API ==============

@router.post("/api/memory/note")
def create_memory_note(
    content: str = Form(...),
    title: str = Form(""),
    tags: Optional[str] = Form(None)
):
    """
    Create a quick note in living memory.
    """
    note_id = str(uuid.uuid4())
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    result = embed_note(
        file_id=note_id,
        content=content,
        title=title,
        tags=tag_list
    )

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    return {
        "success": True,
        "note_id": note_id,
        "title": title,
        "metadata": result.get("metadata", {})
    }
