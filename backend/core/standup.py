"""
Standup content generator for daily briefings.

Generates:
- Safety Moment: Food safety tips from training corpus + current events
- DEI Moment: Awareness days, historical events, inclusion topics
- Manager Prompt: Daily talking points and focus areas

Supports pre-baking (scheduled generation) and rerolls.
"""
import logging
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from dataclasses import dataclass, asdict

from .corpus import get_corpus_text
from . import llm

logger = logging.getLogger(__name__)

# Cache directory for pre-baked content
CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "standup_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class StandupContent:
    """Container for daily standup content."""
    date: str
    safety_moment: Dict[str, Any]
    dei_moment: Dict[str, Any]
    manager_prompt: Dict[str, Any]
    generated_at: str
    version: int = 1


def get_llm_response(prompt: str, system: str = "", temperature: float = 0.7) -> Optional[str]:
    """Get response from Claude LLM."""
    return llm.chat(prompt, system=system if system else None, temperature=temperature)


def web_search(query: str, num_results: int = 5, timeout: int = 5) -> List[Dict[str, str]]:
    """
    Search the web for relevant content.
    Uses DuckDuckGo Instant Answer API (no API key required).

    Args:
        query: Search query
        num_results: Max results to return
        timeout: Request timeout in seconds (default 5, fail fast)
    """
    try:
        # DuckDuckGo Instant Answer API
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            },
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()

        results = []

        # Abstract (main answer)
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", ""),
                "snippet": data.get("Abstract", ""),
                "source": data.get("AbstractSource", ""),
                "url": data.get("AbstractURL", "")
            })

        # Related topics
        for topic in data.get("RelatedTopics", [])[:num_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:100],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", "")
                })

        return results[:num_results]

    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return []


def get_today_observances() -> List[str]:
    """Get national/international observances for today."""
    today = datetime.now()
    month_day = today.strftime("%B %d")

    # Search for observances
    results = web_search(f"national day {month_day} observances awareness")

    observances = []
    for r in results:
        if r.get("snippet"):
            observances.append(r["snippet"])

    return observances


def generate_safety_moment(topic_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a safety moment from training corpus and web research.
    """
    # Load training corpus text (truncated to keep context manageable)
    rag_context = get_corpus_text(max_chars=8000)
    sources = ["Training Materials"]
    if not rag_context:
        logger.warning("No training materials found for safety moment")
        rag_context = "(No training materials available - using general food safety knowledge)"

    # Get current food safety news (use current year)
    current_year = datetime.now().year
    web_results = web_search(f"food safety news tips {current_year}", timeout=5)
    web_context = ""
    for r in web_results[:2]:
        if r.get("snippet"):
            web_context += f"\n- {r['snippet'][:300]}"

    if not web_context:
        web_context = "\n(Web search unavailable)"

    # Generate with LLM
    topic_instruction = ""
    if topic_hint:
        topic_instruction = f"\n\nIMPORTANT: Focus specifically on {topic_hint}. The safety moment MUST be about {topic_hint}."

    prompt = f"""Generate a brief, engaging Safety Moment for a food service team standup meeting.
{topic_instruction}

CONTEXT FROM TRAINING MATERIALS:
{rag_context}

CURRENT NEWS/TRENDS:
{web_context}

Requirements:
- 2-3 short paragraphs
- Actionable tip the team can use today
- Conversational but professional tone
- Focus on practical food safety

Generate ONLY the safety moment content, no headers or labels."""

    system = "You are a food safety expert creating daily briefing content for kitchen staff."

    content = get_llm_response(prompt, system, temperature=0.7)

    return {
        "content": content or "Unable to generate safety moment.",
        "sources": list(set(sources)),
        "topic": topic_hint or "general food safety",
        "type": "safety_moment"
    }


def generate_dei_moment(topic_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a DEI moment based on observances, history, and inclusion topics.
    """
    today = datetime.now()
    date_str = today.strftime("%B %d")

    # Get observances and historical context
    observances = get_today_observances()

    # Search for historical events
    history_results = web_search(f"on this day {date_str} history")

    # Build context
    context = f"Today is {date_str}.\n"

    if observances:
        context += "\nObservances today:\n"
        for obs in observances[:3]:
            context += f"- {obs[:200]}\n"

    if history_results:
        context += "\nHistorical context:\n"
        for h in history_results[:2]:
            if h.get("snippet"):
                context += f"- {h['snippet'][:200]}\n"

    # Generate with LLM
    prompt = f"""Generate a brief DEI (Diversity, Equity, Inclusion) moment for a team standup meeting.

{context}

{f"Focus area hint: {topic_hint}" if topic_hint else ""}

Requirements:
- 2-3 short paragraphs
- Connect to a relevant observance, historical event, or inclusion topic
- Thoughtful and respectful tone
- Include a reflection question or action item for the team
- Educational but not preachy

Generate ONLY the DEI moment content, no headers or labels."""

    system = "You are creating thoughtful, inclusive content for diverse workplace teams."

    content = get_llm_response(prompt, system, temperature=0.7)

    return {
        "content": content or "Unable to generate DEI moment.",
        "observances": observances[:3] if observances else [],
        "date": date_str,
        "topic": topic_hint,
        "type": "dei_moment"
    }


def generate_manager_prompt(focus_areas: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Generate manager talking points and daily focus areas.
    """
    today = datetime.now()
    day_of_week = today.strftime("%A")

    # Load training corpus text (truncated)
    rag_context = get_corpus_text(max_chars=6000)
    sources = ["Training Materials"] if rag_context else []

    focus_str = ""
    if focus_areas:
        focus_str = f"\nFocus areas to address: {', '.join(focus_areas)}"

    prompt = f"""Generate manager talking points for a {day_of_week} team standup.

MANAGEMENT GUIDANCE FROM TRAINING:
{rag_context}
{focus_str}

Requirements:
- 3-5 bullet points for the manager to cover
- Mix of operational reminders and team engagement
- Consider it's {day_of_week} (adjust tone/focus accordingly)
- Practical and actionable
- End with a motivational note

Generate ONLY the manager prompt content as bullet points."""

    system = "You are a management coach helping food service managers run effective team standups."

    content = get_llm_response(prompt, system, temperature=0.6)

    return {
        "content": content or "Unable to generate manager prompt.",
        "sources": list(set(sources)),
        "day": day_of_week,
        "focus_areas": focus_areas or [],
        "type": "manager_prompt"
    }


def generate_daily_standup(
    safety_topic: Optional[str] = None,
    dei_topic: Optional[str] = None,
    focus_areas: Optional[List[str]] = None
) -> StandupContent:
    """
    Generate complete daily standup content.
    """
    today = date.today().isoformat()

    logger.info(f"Generating standup content for {today}")

    safety = generate_safety_moment(safety_topic)
    dei = generate_dei_moment(dei_topic)
    manager = generate_manager_prompt(focus_areas)

    return StandupContent(
        date=today,
        safety_moment=safety,
        dei_moment=dei,
        manager_prompt=manager,
        generated_at=datetime.now().isoformat(),
        version=1
    )


def prebake_standup(target_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Pre-generate and cache standup content for a date.

    Args:
        target_date: ISO date string (YYYY-MM-DD), defaults to today
    """
    target = target_date or date.today().isoformat()
    cache_file = CACHE_DIR / f"standup_{target}.json"

    # Generate content
    content = generate_daily_standup()
    content_dict = asdict(content)

    # Save to cache
    with open(cache_file, 'w') as f:
        json.dump(content_dict, f, indent=2)

    logger.info(f"Pre-baked standup content saved to {cache_file}")

    return {
        "success": True,
        "date": target,
        "cache_file": str(cache_file),
        "content": content_dict
    }


def get_cached_standup(target_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get cached standup content for a date.
    """
    target = target_date or date.today().isoformat()
    cache_file = CACHE_DIR / f"standup_{target}.json"

    if cache_file.exists():
        with open(cache_file, 'r') as f:
            return json.load(f)

    return None


def get_or_generate_standup(target_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Get cached standup or generate fresh if not available.
    """
    # Try cache first
    cached = get_cached_standup(target_date)
    if cached:
        cached["from_cache"] = True
        return cached

    # Generate fresh
    content = generate_daily_standup()
    result = asdict(content)
    result["from_cache"] = False

    # Save to cache for future requests
    target = target_date or date.today().isoformat()
    cache_file = CACHE_DIR / f"standup_{target}.json"
    try:
        with open(cache_file, 'w') as f:
            json.dump(result, f, indent=2)
        logger.info(f"Cached standup for {target}")
    except Exception as e:
        logger.error(f"Failed to cache standup: {e}")

    return result


def reroll_section(section: str, topic_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Regenerate a specific section of the standup.

    Args:
        section: 'safety', 'dei', or 'manager'
        topic_hint: Optional topic to focus on
    """
    if section == "safety":
        return generate_safety_moment(topic_hint)
    elif section == "dei":
        return generate_dei_moment(topic_hint)
    elif section == "manager":
        return generate_manager_prompt([topic_hint] if topic_hint else None)
    else:
        return {"error": f"Unknown section: {section}"}


def list_cached_standups() -> List[Dict[str, Any]]:
    """List all cached standup dates."""
    cached = []
    for f in CACHE_DIR.glob("standup_*.json"):
        date_str = f.stem.replace("standup_", "")
        cached.append({
            "date": date_str,
            "file": str(f),
            "size": f.stat().st_size
        })
    return sorted(cached, key=lambda x: x["date"], reverse=True)
