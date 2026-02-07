"""
Living Memory service — stub.

The embedding-based living memory system has been removed.
Date/people/tag extraction utilities are kept for potential future use.
"""
import logging
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


def extract_dates_from_text(text: str) -> List[str]:
    """Extract date strings from text."""
    DATE_PATTERNS = [
        r'(\d{1,2}/\d{1,2}/\d{2,4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{1,2}-\d{1,2}-\d{2,4})',
    ]
    dates = []
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
    words = text.split()
    skip_words = {'the', 'and', 'for', 'from', 'with', 'chef', 'manager', 'am', 'pm'}
    for i, word in enumerate(words):
        if word.lower() in skip_words:
            continue
        if word and word[0].isupper() and len(word) > 1:
            if i + 1 < len(words) and words[i + 1] and words[i + 1][0].isupper():
                full_name = f"{word} {words[i + 1]}"
                if len(full_name) < 30:
                    people.add(full_name)
            elif not word.isupper():
                people.add(word)
    return list(people)


def extract_tags_from_text(text: str) -> List[str]:
    """Extract hashtag-style tags from text."""
    return list(set(re.findall(r'#(\w+)', text.lower())))


def enrich_metadata(text: str, filename: str = "", base_metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """Enrich metadata with extracted information."""
    metadata = base_metadata.copy() if base_metadata else {}
    metadata['dates_mentioned'] = extract_dates_from_text(text)
    metadata['people'] = extract_people_from_text(text)
    metadata['tags'] = extract_tags_from_text(text)
    return metadata


# Stub functions for API compatibility
def embed_schedule(file_id, parsed_data, filename="", file_date=None):
    return {"success": False, "error": "Embeddings pipeline removed", "chunks": 0}


def embed_note(file_id, content, title="", tags=None):
    return {"success": False, "error": "Embeddings pipeline removed", "chunks": 0}


def get_today_items(date=None):
    return {"date": date or datetime.now().strftime('%Y-%m-%d'), "schedules": [], "notes": [], "files": [], "people_working": [], "tags": []}


def get_upcoming_items(days=7):
    return []


def search_memory(query, limit=10, content_type=None, date_from=None, date_to=None):
    return []
