"""
Item locations and walking order database operations.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import uuid

from .base import get_db, DEFAULT_LOCATION_ORDER


def get_item_location(site_id: str, sku: str) -> Optional[Dict[str, Any]]:
    """Get location for a specific item at a site."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM item_locations WHERE site_id = ? AND sku = ?",
            (site_id, sku)
        ).fetchone()
        if row:
            return dict(row)
    return None


def set_item_location(
    site_id: str,
    sku: str,
    location: str,
    zone: Optional[str] = None,
    sort_order: int = 0,
    never_count: bool = False,
    auto_assigned: bool = True
) -> Dict[str, Any]:
    """Set or update location for an item (upsert)."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM item_locations WHERE site_id = ? AND sku = ?",
            (site_id, sku)
        ).fetchone()

        if existing:
            conn.execute("""
                UPDATE item_locations
                SET location = ?, zone = ?, sort_order = ?, never_count = ?,
                    auto_assigned = ?, updated_at = ?
                WHERE site_id = ? AND sku = ?
            """, (location, zone, sort_order, 1 if never_count else 0,
                  1 if auto_assigned else 0, now, site_id, sku))
        else:
            item_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO item_locations
                (id, site_id, sku, location, zone, sort_order, never_count, auto_assigned, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (item_id, site_id, sku, location, zone, sort_order,
                  1 if never_count else 0, 1 if auto_assigned else 0, now, now))

    return get_item_location(site_id, sku)


def bulk_set_item_locations(
    site_id: str,
    items: List[Dict[str, Any]]
) -> int:
    """Bulk set locations for multiple items."""
    now = datetime.utcnow().isoformat()
    updated = 0

    with get_db() as conn:
        for item in items:
            sku = item.get("sku", "")
            if not sku:
                continue

            location = item.get("location", "UNASSIGNED")
            zone = item.get("zone")
            sort_order = item.get("sort_order", 0)
            never_count = item.get("never_count", False)
            auto_assigned = item.get("auto_assigned", True)

            existing = conn.execute(
                "SELECT id FROM item_locations WHERE site_id = ? AND sku = ?",
                (site_id, sku)
            ).fetchone()

            if existing:
                conn.execute("""
                    UPDATE item_locations
                    SET location = ?, zone = ?, sort_order = ?, never_count = ?,
                        auto_assigned = ?, updated_at = ?
                    WHERE site_id = ? AND sku = ?
                """, (location, zone, sort_order, 1 if never_count else 0,
                      1 if auto_assigned else 0, now, site_id, sku))
            else:
                item_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO item_locations
                    (id, site_id, sku, location, zone, sort_order, never_count, auto_assigned, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (item_id, site_id, sku, location, zone, sort_order,
                      1 if never_count else 0, 1 if auto_assigned else 0, now, now))

            updated += 1

    return updated


def list_item_locations(
    site_id: str,
    location: Optional[str] = None,
    include_never_count: bool = True
) -> List[Dict[str, Any]]:
    """List all item locations for a site, optionally filtered by location."""
    with get_db() as conn:
        query = "SELECT * FROM item_locations WHERE site_id = ?"
        params = [site_id]

        if location:
            query += " AND location = ?"
            params.append(location)

        if not include_never_count:
            query += " AND never_count = 0"

        query += " ORDER BY location, sort_order, sku"

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_location_summary(site_id: str) -> Dict[str, int]:
    """Get count of items per location for a site."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT location, COUNT(*) as count
            FROM item_locations
            WHERE site_id = ?
            GROUP BY location
            ORDER BY location
        """, (site_id,)).fetchall()
        return {row["location"]: row["count"] for row in rows}


def delete_item_location(site_id: str, sku: str) -> bool:
    """Delete a specific item location."""
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM item_locations WHERE site_id = ? AND sku = ?",
            (site_id, sku)
        )
        return result.rowcount > 0


def clear_item_locations(site_id: str) -> int:
    """Clear all item locations for a site."""
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM item_locations WHERE site_id = ?",
            (site_id,)
        )
        return result.rowcount


# ============== Location Walking Order Operations ==============

def get_location_order(site_id: str) -> Dict[str, int]:
    """Get the walking order for locations at a site."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT location, sort_order FROM location_order WHERE site_id = ? ORDER BY sort_order",
            (site_id,)
        ).fetchall()

        if rows:
            return {row["location"]: row["sort_order"] for row in rows}

    # Return default order
    return DEFAULT_LOCATION_ORDER.copy()


def set_location_order(site_id: str, order: List[str]) -> Dict[str, int]:
    """Set the walking order for locations at a site."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        # Clear existing order for this site
        conn.execute("DELETE FROM location_order WHERE site_id = ?", (site_id,))

        # Insert new order
        for idx, location in enumerate(order, 1):
            order_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO location_order (id, site_id, location, sort_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (order_id, site_id, location, idx, now, now))

    return get_location_order(site_id)


def reset_location_order(site_id: str) -> bool:
    """Reset location order to defaults for a site."""
    with get_db() as conn:
        conn.execute("DELETE FROM location_order WHERE site_id = ?", (site_id,))
    return True


def list_available_locations(site_id: str) -> List[str]:
    """Get all unique locations used by items at a site."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT DISTINCT location FROM item_locations
            WHERE site_id = ? AND location IS NOT NULL
            ORDER BY location
        """, (site_id,)).fetchall()
        return [row["location"] for row in rows]


def get_location_sort_key(site_id: str) -> Callable[[str], int]:
    """Get a sort key function for locations at a site."""
    order = get_location_order(site_id)

    def sort_key(location: str) -> int:
        return order.get(location, 50)  # Unknown locations get middle priority

    return sort_key
