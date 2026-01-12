"""
Ignored items database operations (for purchase match).
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
import uuid

from .base import get_db


def add_ignored_item(
    site_id: str,
    sku: str,
    reason: Optional[str] = None,
    notes: Optional[str] = None,
    created_by: Optional[str] = None
) -> Dict[str, Any]:
    """Add an item to the site's ignore list."""
    item_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO ignored_items (id, site_id, sku, reason, notes, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (item_id, site_id, sku, reason, notes, created_by, now))

    return get_ignored_item(site_id, sku)


def get_ignored_item(site_id: str, sku: str) -> Optional[Dict[str, Any]]:
    """Get a specific ignored item."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM ignored_items WHERE site_id = ? AND sku = ?",
            (site_id, sku)
        ).fetchone()
        if row:
            return dict(row)
    return None


def remove_ignored_item(site_id: str, sku: str) -> bool:
    """Remove an item from the site's ignore list. Returns True if item was found and removed."""
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM ignored_items WHERE site_id = ? AND sku = ?",
            (site_id, sku)
        )
        return result.rowcount > 0


def list_ignored_items(site_id: str) -> List[Dict[str, Any]]:
    """List all ignored items for a site."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM ignored_items WHERE site_id = ? ORDER BY created_at DESC",
            (site_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_ignored_skus(site_id: str) -> Set[str]:
    """Get set of ignored SKUs for a site (for quick lookup in matcher)."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT sku FROM ignored_items WHERE site_id = ?",
            (site_id,)
        ).fetchall()
        return {row["sku"] for row in rows}
