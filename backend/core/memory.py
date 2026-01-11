"""
Living Memory service for personal schedules, notes, and work files.

This module handles the special processing needs of the living_memory collection,
including date extraction, people parsing, and tag management.
"""
import logging
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dateutil import parser as date_parser

from .embeddings import embed_document, search, embed_text, get_collection
from .database import create_file, update_file, list_files

logger = logging.getLogger(__name__)

COLLECTION_NAME = "living_memory"


# Common name patterns for chef/staff extraction
NAME_PATTERNS = [
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',  # First Last or First
]

# Date patterns
DATE_PATTERNS = [
    r'(\d{1,2}/\d{1,2}/\d{2,4})',  # MM/DD/YYYY or M/D/YY
    r'(\d{4}-\d{2}-\d{2})',         # YYYY-MM-DD
    r'(\d{1,2}-\d{1,2}-\d{2,4})',   # MM-DD-YYYY
]

# Day of week patterns
DAY_PATTERNS = [
    r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
    r'\b(mon|tue|wed|thu|fri|sat|sun)\b',
]


def extract_dates_from_text(text: str) -> List[str]:
    """Extract date strings from text."""
    dates = []
    text_lower = text.lower()

    # Try explicit date patterns
    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                parsed = date_parser.parse(match)
                dates.append(parsed.strftime('%Y-%m-%d'))
            except Exception:
                pass

    return list(set(dates))


def extract_people_from_text(text: str) -> List[str]:
    """Extract potential person names from text."""
    people = set()

    # Look for capitalized names
    words = text.split()
    for i, word in enumerate(words):
        # Skip common non-name words
        skip_words = {'the', 'and', 'for', 'from', 'with', 'chef', 'manager', 'am', 'pm'}
        if word.lower() in skip_words:
            continue

        # Check if it looks like a name (capitalized)
        if word and word[0].isupper() and len(word) > 1:
            # Check if followed by another capitalized word (full name)
            if i + 1 < len(words) and words[i + 1] and words[i + 1][0].isupper():
                full_name = f"{word} {words[i + 1]}"
                if len(full_name) < 30:  # Sanity check
                    people.add(full_name)
            elif not word.isupper():  # Single name, not acronym
                people.add(word)

    return list(people)


def extract_tags_from_text(text: str) -> List[str]:
    """Extract hashtag-style tags from text."""
    tags = re.findall(r'#(\w+)', text.lower())
    return list(set(tags))


def detect_content_type(text: str, filename: str = "") -> str:
    """Detect the type of living memory content."""
    text_lower = text.lower()
    filename_lower = filename.lower()

    # Schedule indicators
    schedule_words = ['schedule', 'shift', 'roster', 'am', 'pm', 'monday', 'tuesday',
                      'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    if any(word in text_lower for word in schedule_words) or 'schedule' in filename_lower:
        return 'schedule'

    # Note indicators
    note_words = ['note', 'todo', 'task', 'reminder', 'meeting']
    if any(word in text_lower for word in note_words) or 'note' in filename_lower:
        return 'note'

    return 'file'


def enrich_metadata(
    text: str,
    filename: str = "",
    base_metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Enrich metadata with extracted information.

    Returns metadata dict with:
    - type: schedule|note|file
    - dates_mentioned: list of ISO dates found
    - date_relevant: primary date this content is relevant for
    - people: list of people mentioned
    - tags: extracted tags
    """
    metadata = base_metadata.copy() if base_metadata else {}

    # Detect content type
    content_type = detect_content_type(text, filename)
    metadata['type'] = content_type

    # Extract dates
    dates = extract_dates_from_text(text)
    metadata['dates_mentioned'] = dates

    # Set primary relevant date
    if dates:
        # Use the earliest date as the relevant date
        metadata['date_relevant'] = min(dates)
    else:
        # Default to today
        metadata['date_relevant'] = datetime.now().strftime('%Y-%m-%d')

    # Extract people
    people = extract_people_from_text(text)
    metadata['people'] = people
    metadata['people_json'] = json.dumps(people)

    # Extract tags
    tags = extract_tags_from_text(text)
    metadata['tags'] = tags
    metadata['tags_json'] = json.dumps(tags)

    return metadata


def embed_schedule(
    file_id: str,
    parsed_data: Dict[str, Any],
    filename: str = "",
    file_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Embed a schedule file with enriched metadata.

    Schedules get special handling:
    - Each row is analyzed for dates and people
    - Metadata includes who's working when
    """
    rows = parsed_data.get("rows", [])
    headers = parsed_data.get("headers", [])

    # Combine all text for analysis
    all_text = " ".join(
        " ".join(str(v) for v in row.values() if v)
        for row in rows
    )

    # Enrich metadata
    enriched = enrich_metadata(all_text, filename)
    enriched['headers'] = headers

    # Embed with enriched metadata
    result = embed_document(
        file_id=file_id,
        parsed_data=parsed_data,
        filename=filename,
        file_date=file_date,
        collection_name=COLLECTION_NAME
    )

    result['metadata'] = enriched
    return result


def embed_note(
    file_id: str,
    content: str,
    title: str = "",
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Embed a text note into living memory.

    Args:
        file_id: Unique ID for this note
        content: Note text content
        title: Optional title
        tags: Optional list of tags
    """
    # Enrich metadata
    enriched = enrich_metadata(content, title)

    # Add explicit tags
    if tags:
        enriched['tags'] = list(set(enriched.get('tags', []) + tags))
        enriched['tags_json'] = json.dumps(enriched['tags'])

    # Create embedding
    embedding = embed_text(content)
    if not embedding:
        return {"error": "Failed to generate embedding", "chunks": 0}

    collection = get_collection(COLLECTION_NAME)
    if not collection:
        return {"error": "ChromaDB not available", "chunks": 0}

    chunk_id = f"{file_id}_note_0"
    now = datetime.now()

    try:
        collection.upsert(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "file_id": file_id,
                "type": "note",
                "title": title,
                "date": now.isoformat(),
                "date_epoch": int(now.timestamp()),
                "date_relevant": enriched.get('date_relevant', now.strftime('%Y-%m-%d')),
                "people_json": enriched.get('people_json', '[]'),
                "tags_json": enriched.get('tags_json', '[]'),
                "collection": COLLECTION_NAME
            }]
        )

        return {
            "success": True,
            "chunks_embedded": 1,
            "metadata": enriched
        }

    except Exception as e:
        logger.error(f"Failed to embed note: {e}")
        return {"error": str(e), "chunks": 0}


def get_today_items(date: Optional[str] = None) -> Dict[str, Any]:
    """
    Get all living memory items relevant to a specific date.

    Args:
        date: ISO date string (YYYY-MM-DD), defaults to today

    Returns:
        Dict with schedules, notes, and other items for the day
    """
    target_date = date or datetime.now().strftime('%Y-%m-%d')

    collection = get_collection(COLLECTION_NAME)
    if not collection:
        return {"error": "Collection not available", "items": []}

    try:
        # Query for items where date_relevant matches target date
        results = collection.get(
            where={"date_relevant": target_date},
            include=["documents", "metadatas"]
        )

        items = {
            "date": target_date,
            "schedules": [],
            "notes": [],
            "files": [],
            "people_working": set(),
            "tags": set()
        }

        for i, doc in enumerate(results.get("documents", [])):
            meta = results["metadatas"][i] if results.get("metadatas") else {}
            item_type = meta.get("type", "file")

            item = {
                "id": results["ids"][i],
                "content": doc,
                "metadata": meta
            }

            if item_type == "schedule":
                items["schedules"].append(item)
                # Extract people
                people = json.loads(meta.get("people_json", "[]"))
                items["people_working"].update(people)
            elif item_type == "note":
                items["notes"].append(item)
            else:
                items["files"].append(item)

            # Collect tags
            tags = json.loads(meta.get("tags_json", "[]"))
            items["tags"].update(tags)

        # Convert sets to lists for JSON serialization
        items["people_working"] = list(items["people_working"])
        items["tags"] = list(items["tags"])

        return items

    except Exception as e:
        logger.error(f"Failed to get today items: {e}")
        return {"error": str(e), "items": []}


def get_upcoming_items(days: int = 7) -> List[Dict[str, Any]]:
    """
    Get living memory items for the upcoming days.

    Args:
        days: Number of days to look ahead

    Returns:
        List of items grouped by date
    """
    results = []
    today = datetime.now()

    for i in range(days):
        target_date = (today + timedelta(days=i)).strftime('%Y-%m-%d')
        day_items = get_today_items(target_date)
        if not day_items.get("error"):
            results.append(day_items)

    return results


def search_memory(
    query: str,
    limit: int = 10,
    content_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search living memory with type and date filters.

    Args:
        query: Search text
        limit: Max results
        content_type: Filter by type (schedule, note, file)
        date_from: Start date filter
        date_to: End date filter
    """
    return search(
        query=query,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        collection_name=COLLECTION_NAME
    )
