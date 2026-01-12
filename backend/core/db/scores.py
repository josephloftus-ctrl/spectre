"""
Unit score and score history database operations.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from .base import get_db


def save_unit_score(
    score_id: str,
    site_id: str,
    score: int,
    status: str,
    item_flag_count: int,
    room_flag_count: int,
    flagged_items: List[Dict],
    flagged_rooms: List[Dict],
    room_totals: Dict[str, float],
    total_value: float,
    item_count: int,
    file_id: Optional[str] = None
) -> Dict[str, Any]:
    """Save or update a unit score."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        # Delete existing score for this site (we only keep latest)
        conn.execute("DELETE FROM unit_scores WHERE site_id = ?", (site_id,))

        conn.execute("""
            INSERT INTO unit_scores (
                id, file_id, site_id, score, status,
                item_flag_count, room_flag_count,
                flagged_items, flagged_rooms, room_totals,
                total_value, item_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            score_id, file_id, site_id, score, status,
            item_flag_count, room_flag_count,
            json.dumps(flagged_items), json.dumps(flagged_rooms), json.dumps(room_totals),
            total_value, item_count, now
        ))

    return get_unit_score(site_id)


def get_unit_score(site_id: str) -> Optional[Dict[str, Any]]:
    """Get the latest score for a site."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM unit_scores WHERE site_id = ?",
            (site_id,)
        ).fetchone()
        if row:
            result = dict(row)
            # Parse JSON fields
            result["flagged_items"] = json.loads(result.get("flagged_items") or "[]")
            result["flagged_rooms"] = json.loads(result.get("flagged_rooms") or "[]")
            result["room_totals"] = json.loads(result.get("room_totals") or "{}")
            return result
    return None


def list_unit_scores(
    status: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """List all unit scores, sorted by score descending (worst first)."""
    query = "SELECT * FROM unit_scores WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY score DESC, site_id ASC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            result = dict(row)
            result["flagged_items"] = json.loads(result.get("flagged_items") or "[]")
            result["flagged_rooms"] = json.loads(result.get("flagged_rooms") or "[]")
            result["room_totals"] = json.loads(result.get("room_totals") or "{}")
            results.append(result)
        return results


def get_all_site_ids_with_scores() -> List[str]:
    """Get list of all site IDs that have scores."""
    with get_db() as conn:
        rows = conn.execute("SELECT DISTINCT site_id FROM unit_scores").fetchall()
        return [row["site_id"] for row in rows]


# ============== Score History Operations ==============

def save_score_snapshot(
    snapshot_id: str,
    site_id: str,
    score: int,
    status: str,
    item_flag_count: int,
    room_flag_count: int,
    total_value: float,
    snapshot_date: str
) -> Dict[str, Any]:
    """Save a weekly score snapshot."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT INTO score_history (
                id, site_id, score, status,
                item_flag_count, room_flag_count,
                total_value, snapshot_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id, site_id, score, status,
            item_flag_count, room_flag_count,
            total_value, snapshot_date, now
        ))

    return {
        "id": snapshot_id,
        "site_id": site_id,
        "score": score,
        "snapshot_date": snapshot_date
    }


def get_score_history(
    site_id: str,
    limit: int = 12  # ~3 months of weekly data
) -> List[Dict[str, Any]]:
    """Get score history for a site, most recent first."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM score_history
            WHERE site_id = ?
            ORDER BY snapshot_date DESC
            LIMIT ?
        """, (site_id, limit)).fetchall()
        return [dict(row) for row in rows]


def get_latest_snapshot_date() -> Optional[str]:
    """Get the most recent snapshot date across all sites."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT MAX(snapshot_date) as latest FROM score_history"
        ).fetchone()
        return row["latest"] if row else None


def get_score_trend(site_id: str) -> Optional[str]:
    """
    Get trend indicator for a site.

    Returns:
        'up' - Score increased (got worse)
        'down' - Score decreased (improved)
        'stable' - No change
        None - Not enough history
    """
    history = get_score_history(site_id, limit=2)
    if len(history) < 2:
        return None

    current = history[0]["score"]
    previous = history[1]["score"]

    if current > previous:
        return "up"
    elif current < previous:
        return "down"
    else:
        return "stable"
