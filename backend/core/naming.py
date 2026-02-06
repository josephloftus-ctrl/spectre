"""
Unified site and location naming utilities.

Provides consistent site ID normalization and extraction across:
- File uploads (files.py)
- Filename parsing (worker.py)
- Excel sheet content (engine.py)
"""
import re
from pathlib import Path
from typing import Optional


def slugify(text: str, max_length: int = 40) -> str:
    """
    Convert text to a URL/ID-safe slug.

    Transforms: "PSEG - NHQ (673)" -> "pseg_nhq"

    Args:
        text: Input text to slugify
        max_length: Maximum length of output

    Returns:
        Lowercase slug with only alphanumeric chars and underscores
    """
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9\s_-]+", "", t)
    t = t.replace("-", "_")
    t = re.sub(r"\s+", "_", t)
    t = re.sub(r"_+", "_", t)
    t = t.strip("_")
    return t[:max_length]


def normalize_site_id(site_id: Optional[str], filename: str = "") -> str:
    """
    Normalize site ID for standardized naming.
    If site_id is not provided, try to infer from filename.

    Args:
        site_id: Explicit site ID (may be None)
        filename: Filename to infer from if site_id not provided

    Returns:
        Normalized site ID string, or 'unknown' if cannot determine
    """
    if site_id:
        # Standardize: lowercase, underscores instead of spaces/hyphens
        return site_id.lower().replace(' ', '_').replace('-', '_')

    # Try to infer from common patterns in filename
    if filename:
        site = extract_site_from_filename(filename)
        if site:
            return site

    return 'unknown'


def extract_site_from_filename(filename: str) -> Optional[str]:
    """
    Extract site_id from filename.

    Handles various naming patterns:
    - "PSEG NHQ 1_8.xlsx" -> "pseg_nhq"
    - "PSEG NHQ.xlsx" -> "pseg_nhq"
    - "Site Name 12-25.xlsx" -> "site_name"
    - "Lockheed Martin 100.xlsx" -> "lockheed_100"
    - "01.15.25 - PSEG NHQ.xlsx" -> "pseg_nhq"
    - "NHQ_1_2026-01-18.xlsx" -> "pseg_nhq"

    Args:
        filename: Original filename

    Returns:
        Extracted site ID or None if cannot determine
    """
    if not filename:
        return None

    # Remove extension
    name = Path(filename).stem

    # Skip if it's just underscores or numbers
    if re.match(r'^[_\s\d\(\).-]+$', name):
        return None

    # First, try fuzzy matching against known site patterns (handles abbreviations)
    known_match = match_known_site(name)
    if known_match:
        return known_match

    # Remove date PREFIX patterns: "01.15.25 - ", "1.8.26 ", "12-26 - ", etc.
    # MM.DD.YY or M.D.YY with optional separator after
    name = re.sub(r'^\d{1,2}[._-]\d{1,2}[._-]?\d{0,4}\s*[-–]\s*', '', name)
    name = re.sub(r'^\d{1,2}[._-]\d{1,2}[._-]\d{2,4}\s+', '', name)

    # Remove standardized filename SUFFIX patterns: "_1_2026-01-18", "_1"
    # This handles files like "NHQ_1_2026-01-18.xlsx" or "LOCKHEED_100_1_2026-01-18.xlsx"
    name = re.sub(r'_\d+_\d{4}-\d{2}-\d{2}$', '', name)

    # Remove date SUFFIX patterns (1_8, 12-25, 2024-01-08, etc.)
    name = re.sub(r'[\s_-]*\d{1,2}[_/-]\d{1,2}([_/-]\d{2,4})?$', '', name)
    name = re.sub(r'[\s_-]*\d{4}[_/-]\d{1,2}[_/-]\d{1,2}$', '', name)

    # Remove trailing version/sequence numbers like "_1" but preserve site numbers like "_100"
    # Only remove if it's a small number (1-9) preceded by underscore
    name = re.sub(r'_[1-9]$', '', name)

    # Remove trailing numbers and special chars (but not if they're part of site name like "100")
    name = re.sub(r'[\s_-]+$', '', name)

    # Clean up and normalize
    name = name.strip()
    if not name or len(name) < 2:
        return None

    # Try fuzzy matching again after cleanup
    known_match = match_known_site(name)
    if known_match:
        return known_match

    # Convert to site_id format: lowercase, spaces to underscores
    site_id = re.sub(r'\s+', '_', name.lower())
    site_id = re.sub(r'[^a-z0-9_]', '', site_id)
    site_id = re.sub(r'_+', '_', site_id).strip('_')

    return site_id if site_id else None


# Common site patterns for fuzzy matching
# Order matters - more specific patterns should come first
# Canonical site_id -> list of patterns that map to it
KNOWN_SITE_PATTERNS = {
    # Lockheed Martin Bldg 100 - canonical name with all variations
    'lockheed_martin_bldg_100': [
        'lockheed martin, bldg 100', 'lockheed_martin_bldg_100', 'lockheed martin bldg 100',
        'lockhead martin, bldg 100', 'lockhead_martin_bldg_100',  # typo variants
        'lockheed_100', 'lockheed 100', 'lockheed100', 'lm100', 'lm 100',
        'bldg 100', 'bldg_100', 'building 100',
    ],
    # Lockheed Martin Bldg D - canonical name with all variations
    'lockheed_martin_bldg_d': [
        'lockheed martin, bldg d', 'lockheed_martin_bldg_d', 'lockheed martin bldg d',
        'lockheed_bldg_d', 'lockheed_d', 'lockheed d', 'lmd',
        'bldg d', 'bldg_d', 'building d',
    ],
    # PSEG sites
    'pseg_nhq': ['pseg nhq', 'pseg_nhq', 'pseg - nhq', 'nhq', 'pseg-nhq'],
    'pseg_hq': ['pseg hq', 'pseg_hq', 'headquarters'],
    'pseg_salem': ['pseg salem', 'pseg_salem', 'pseg - salem', 'salem'],
    'pseg_hope_creek': ['pseg hope creek', 'pseg_hope_creek', 'pseg - hope creek', 'hope creek', 'hope_creek', 'hopecreek'],
}


def match_known_site(text: str) -> Optional[str]:
    """
    Try to match text against known site patterns.

    Args:
        text: Text to match (filename, cell value, etc.)

    Returns:
        Matched site_id or None
    """
    text_lower = text.lower()

    for site_id, patterns in KNOWN_SITE_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                return site_id

    return None


def format_display_name(site_id: str) -> str:
    """
    Convert site_id to human-readable display name.

    Transforms: "pseg_nhq" -> "PSEG NHQ"
                "lockheed_bldg_d" -> "Lockheed Bldg D"

    Args:
        site_id: Normalized site ID

    Returns:
        Formatted display name
    """
    if not site_id:
        return "Unknown"

    # Split on underscores
    parts = site_id.split('_')

    # Apply title case, but keep known acronyms uppercase
    acronyms = {'pseg', 'nhq', 'hq', 'lm'}
    formatted = []
    for part in parts:
        if part.lower() in acronyms:
            formatted.append(part.upper())
        else:
            formatted.append(part.title())

    return ' '.join(formatted)


def generate_standard_filename(site_id: str, original_filename: str, date_str: Optional[str] = None) -> str:
    """
    Generate a standardized filename: {SITE_ID}_{YYYY-MM-DD}.{ext}

    Args:
        site_id: Normalized site ID
        original_filename: Original filename (for extension)
        date_str: ISO date string, defaults to today

    Returns:
        Standardized filename like "PSEG_NHQ_2026-01-11.xlsx"
    """
    from datetime import datetime

    ext = Path(original_filename).suffix.lower()
    if not date_str:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
    normalized_site = site_id.upper().replace(' ', '_').replace('-', '_')
    return f"{normalized_site}_{date_str}{ext}"
