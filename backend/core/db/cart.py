"""
Shopping cart database operations.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

from .base import get_db


def add_cart_item(
    site_id: str,
    sku: str,
    description: str,
    quantity: float = 1,
    unit_price: Optional[float] = None,
    uom: Optional[str] = None,
    vendor: Optional[str] = None,
    notes: Optional[str] = None,
    source: str = "manual"
) -> Dict[str, Any]:
    """Add or update an item in the shopping cart.

    Preserves the original ID when updating an existing item.
    """
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        # Check if item already exists
        existing = conn.execute(
            "SELECT id, created_at FROM cart_items WHERE site_id = ? AND sku = ?",
            (site_id, sku)
        ).fetchone()

        if existing:
            # Update existing item, preserve original ID and created_at
            conn.execute("""
                UPDATE cart_items
                SET description = ?, quantity = ?, unit_price = ?, uom = ?,
                    vendor = ?, notes = ?, source = ?, updated_at = ?
                WHERE site_id = ? AND sku = ?
            """, (description, quantity, unit_price, uom, vendor, notes, source, now, site_id, sku))
        else:
            # Insert new item with new UUID
            item_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO cart_items
                (id, site_id, sku, description, quantity, unit_price, uom, vendor, notes, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (item_id, site_id, sku, description, quantity, unit_price, uom, vendor, notes, source, now, now))

    return get_cart_item(site_id, sku)


def get_cart_item(site_id: str, sku: str) -> Optional[Dict[str, Any]]:
    """Get a specific cart item."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM cart_items WHERE site_id = ? AND sku = ?",
            (site_id, sku)
        ).fetchone()
        if row:
            return dict(row)
    return None


def update_cart_item_quantity(site_id: str, sku: str, quantity: float) -> Optional[Dict[str, Any]]:
    """Update quantity for a cart item."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE cart_items SET quantity = ?, updated_at = ? WHERE site_id = ? AND sku = ?",
            (quantity, now, site_id, sku)
        )
    return get_cart_item(site_id, sku)


def remove_cart_item(site_id: str, sku: str) -> bool:
    """Remove an item from the cart."""
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM cart_items WHERE site_id = ? AND sku = ?",
            (site_id, sku)
        )
        return result.rowcount > 0


def list_cart_items(site_id: str) -> List[Dict[str, Any]]:
    """List all items in a site's shopping cart."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM cart_items WHERE site_id = ? ORDER BY created_at DESC",
            (site_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_cart_summary(site_id: str) -> Dict[str, Any]:
    """Get cart summary with totals."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as item_count,
                SUM(quantity) as total_quantity,
                SUM(quantity * COALESCE(unit_price, 0)) as total_value
            FROM cart_items WHERE site_id = ?
        """, (site_id,)).fetchone()

        return {
            "site_id": site_id,
            "item_count": row["item_count"] or 0,
            "total_quantity": row["total_quantity"] or 0,
            "total_value": row["total_value"] or 0
        }


def clear_cart(site_id: str) -> int:
    """Clear all items from a site's cart. Returns count of items removed."""
    with get_db() as conn:
        result = conn.execute("DELETE FROM cart_items WHERE site_id = ?", (site_id,))
        return result.rowcount


def bulk_add_cart_items(site_id: str, items: List[Dict[str, Any]], source: str = "bulk") -> int:
    """Add multiple items to cart at once. Returns count added."""
    now = datetime.utcnow().isoformat()
    added = 0

    with get_db() as conn:
        for item in items:
            item_id = str(uuid.uuid4())
            conn.execute("""
                INSERT OR REPLACE INTO cart_items
                (id, site_id, sku, description, quantity, unit_price, uom, vendor, notes, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id, site_id,
                item.get("sku", ""),
                item.get("description", ""),
                item.get("quantity", 1),
                item.get("unit_price"),
                item.get("uom"),
                item.get("vendor"),
                item.get("notes"),
                source, now, now
            ))
            added += 1

    return added
