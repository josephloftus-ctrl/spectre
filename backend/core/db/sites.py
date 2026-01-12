"""
Site database operations.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from .base import get_db


def auto_format_site_name(site_id: str) -> str:
    """
    Auto-format a site_id into a readable display name.

    Examples:
        'pseg_nhq' -> 'PSEG NHQ'
        'lockheed_bldg_100' -> 'Lockheed Bldg 100'
        'p_and_g_greensboro' -> 'P And G Greensboro'
    """
    if not site_id:
        return ""

    # Replace underscores with spaces
    name = site_id.replace("_", " ")

    # Title case, but preserve all-caps for short words (likely acronyms)
    words = name.split()
    formatted = []
    for word in words:
        # If word is short (<=4 chars) and looks like it could be an acronym, uppercase it
        if len(word) <= 4 and word.isalpha():
            formatted.append(word.upper())
        else:
            formatted.append(word.capitalize())

    return " ".join(formatted)


def get_site(site_id: str) -> Optional[Dict[str, Any]]:
    """Get a site by ID, with auto-formatted name as fallback."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM sites WHERE site_id = ?",
            (site_id,)
        ).fetchone()

        if row:
            result = dict(row)
            # Check if display_name is custom or auto-formatted
            has_custom_name = bool(result.get("display_name"))
            if not has_custom_name:
                result["display_name"] = auto_format_site_name(site_id)
            result["is_custom"] = has_custom_name
            return result

        # Site not in table yet - return auto-formatted name
        return {
            "site_id": site_id,
            "display_name": auto_format_site_name(site_id),
            "is_custom": False,
            "created_at": None,
            "updated_at": None
        }


def get_site_display_name(site_id: str) -> str:
    """Get just the display name for a site."""
    site = get_site(site_id)
    return site.get("display_name", site_id) if site else site_id


def list_sites() -> List[Dict[str, Any]]:
    """List all known sites (from files and explicit entries)."""
    with get_db() as conn:
        # Get all unique site_ids from files
        file_sites = conn.execute(
            "SELECT DISTINCT site_id FROM files WHERE site_id IS NOT NULL"
        ).fetchall()

        # Get all sites from sites table
        explicit_sites = conn.execute("SELECT * FROM sites").fetchall()
        explicit_map = {row["site_id"]: dict(row) for row in explicit_sites}

        # Merge: explicit entries take precedence
        all_site_ids = set(row["site_id"] for row in file_sites)
        all_site_ids.update(explicit_map.keys())

        results = []
        for site_id in sorted(all_site_ids):
            if site_id in explicit_map:
                site = explicit_map[site_id]
                has_custom_name = bool(site.get("display_name"))
                if not has_custom_name:
                    site["display_name"] = auto_format_site_name(site_id)
                site["is_custom"] = has_custom_name
                results.append(site)
            else:
                results.append({
                    "site_id": site_id,
                    "display_name": auto_format_site_name(site_id),
                    "is_custom": False,
                    "created_at": None,
                    "updated_at": None
                })

        return results


def update_site_display_name(site_id: str, display_name: Optional[str]) -> Dict[str, Any]:
    """Update or create a site's display name. Pass None to reset to auto-format."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        # Check if site exists
        existing = conn.execute(
            "SELECT * FROM sites WHERE site_id = ?",
            (site_id,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE sites SET display_name = ?, updated_at = ? WHERE site_id = ?",
                (display_name, now, site_id)
            )
        else:
            conn.execute(
                "INSERT INTO sites (site_id, display_name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (site_id, display_name, now, now)
            )

    return get_site(site_id)
