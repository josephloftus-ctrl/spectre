"""
Count session and count item database operations.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

from .base import get_db, DEFAULT_LOCATION_ORDER
from .locations import get_location_order


def create_count_session(
    site_id: str,
    name: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new inventory count session."""
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    if not name:
        name = f"Count {now[:10]}"

    with get_db() as conn:
        conn.execute("""
            INSERT INTO count_sessions (id, site_id, name, status, created_at, updated_at)
            VALUES (?, ?, ?, 'active', ?, ?)
        """, (session_id, site_id, name, now, now))

    return get_count_session(session_id)


def get_count_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get a count session by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM count_sessions WHERE id = ?",
            (session_id,)
        ).fetchone()
        if row:
            return dict(row)
    return None


def list_count_sessions(
    site_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """List count sessions with optional filters."""
    query = "SELECT * FROM count_sessions WHERE 1=1"
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def update_count_session(
    session_id: str,
    status: Optional[str] = None,
    name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update a count session."""
    now = datetime.utcnow().isoformat()

    updates = ["updated_at = ?"]
    params = [now]

    if status:
        updates.append("status = ?")
        params.append(status)
        if status == "completed":
            updates.append("completed_at = ?")
            params.append(now)

    if name:
        updates.append("name = ?")
        params.append(name)

    params.append(session_id)

    with get_db() as conn:
        conn.execute(f"UPDATE count_sessions SET {', '.join(updates)} WHERE id = ?", params)

        # Update item count and total value
        conn.execute("""
            UPDATE count_sessions SET
                item_count = (SELECT COUNT(*) FROM count_items WHERE session_id = ?),
                total_value = (SELECT SUM(counted_qty * COALESCE(unit_price, 0)) FROM count_items WHERE session_id = ?)
            WHERE id = ?
        """, (session_id, session_id, session_id))

    return get_count_session(session_id)


def add_count_item(
    session_id: str,
    sku: str,
    description: str,
    counted_qty: float,
    expected_qty: Optional[float] = None,
    unit_price: Optional[float] = None,
    uom: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Add or update a counted item in a session."""
    item_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    variance = None
    if expected_qty is not None:
        variance = counted_qty - expected_qty

    with get_db() as conn:
        # Check if item already exists in session
        existing = conn.execute(
            "SELECT id FROM count_items WHERE session_id = ? AND sku = ?",
            (session_id, sku)
        ).fetchone()

        if existing:
            # Update existing
            conn.execute("""
                UPDATE count_items SET
                    description = ?, counted_qty = ?, expected_qty = ?,
                    unit_price = ?, uom = ?, location = ?,
                    variance = ?, notes = ?, counted_at = ?
                WHERE session_id = ? AND sku = ?
            """, (description, counted_qty, expected_qty, unit_price, uom,
                  location, variance, notes, now, session_id, sku))
        else:
            # Insert new
            conn.execute("""
                INSERT INTO count_items
                (id, session_id, sku, description, counted_qty, expected_qty,
                 unit_price, uom, location, variance, notes, counted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (item_id, session_id, sku, description, counted_qty, expected_qty,
                  unit_price, uom, location, variance, notes, now))

    return get_count_item(session_id, sku)


def get_count_item(session_id: str, sku: str) -> Optional[Dict[str, Any]]:
    """Get a specific count item."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM count_items WHERE session_id = ? AND sku = ?",
            (session_id, sku)
        ).fetchone()
        if row:
            return dict(row)
    return None


def list_count_items(session_id: str) -> List[Dict[str, Any]]:
    """List all items in a count session, sorted by location walking order."""
    with get_db() as conn:
        # Get session to find site_id for custom order
        session = conn.execute(
            "SELECT site_id FROM count_sessions WHERE id = ?",
            (session_id,)
        ).fetchone()

        # Get all items
        rows = conn.execute(
            "SELECT * FROM count_items WHERE session_id = ?",
            (session_id,)
        ).fetchall()
        items = [dict(row) for row in rows]

    if not items:
        return items

    # Get location order (custom or default)
    site_id = session["site_id"] if session else None
    if site_id:
        order = get_location_order(site_id)
    else:
        order = DEFAULT_LOCATION_ORDER

    # Sort by location order, then by description
    items.sort(key=lambda x: (
        order.get(x.get("location", "UNASSIGNED"), 50),
        (x.get("description") or "").upper()
    ))

    return items


def bulk_add_count_items(
    session_id: str,
    items: List[Dict[str, Any]]
) -> int:
    """Bulk add items to a count session from inventory snapshot."""
    now = datetime.utcnow().isoformat()
    added = 0

    with get_db() as conn:
        for item in items:
            item_id = str(uuid.uuid4())
            sku = item.get("sku", "")
            description = item.get("description", "")
            expected_qty = item.get("quantity")  # From inventory
            unit_price = item.get("unit_price")
            uom = item.get("uom")
            location = item.get("location")

            # Check if item already exists
            existing = conn.execute(
                "SELECT id FROM count_items WHERE session_id = ? AND sku = ?",
                (session_id, sku)
            ).fetchone()

            if not existing and sku:
                conn.execute("""
                    INSERT INTO count_items
                    (id, session_id, sku, description, counted_qty, expected_qty,
                     unit_price, uom, location, variance, notes, counted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (item_id, session_id, sku, description, 0, expected_qty,
                      unit_price, uom, location, None, None, now))
                added += 1

    return added


def delete_count_session(session_id: str) -> bool:
    """Delete a count session and all its items."""
    with get_db() as conn:
        conn.execute("DELETE FROM count_items WHERE session_id = ?", (session_id,))
        result = conn.execute("DELETE FROM count_sessions WHERE id = ?", (session_id,))
        return result.rowcount > 0
