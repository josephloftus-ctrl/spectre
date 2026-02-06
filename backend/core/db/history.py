"""
Weekly inventory item history functions.

Provides item-level tracking for week-to-week inventory changes.
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from .base import get_db
from .utils import now, row_to_dict, rows_to_dicts


def get_week_ending_date(date: Optional[datetime] = None) -> str:
    """
    Get the ISO date string for the Sunday ending the week containing the given date.
    If no date provided, uses current date.
    Returns format: YYYY-MM-DD
    """
    if date is None:
        date = datetime.utcnow()

    # Get the Sunday of this week (0=Monday, 6=Sunday)
    days_until_sunday = (6 - date.weekday()) % 7
    if days_until_sunday == 0 and date.weekday() != 6:
        # It's not Sunday yet, so get the upcoming Sunday
        days_until_sunday = 7

    # Actually, we want the Sunday that ENDS the week
    # So if today is Monday (0), Sunday is in 6 days
    # If today is Sunday (6), that's the week ending date
    days_until_sunday = (6 - date.weekday()) % 7
    sunday = date + timedelta(days=days_until_sunday)

    return sunday.strftime("%Y-%m-%d")


def save_weekly_item_snapshot(
    site_id: str,
    week_ending: str,
    items: List[Dict[str, Any]]
) -> int:
    """
    Save item-level inventory snapshot for a specific week.
    Uses UPSERT to update existing items or insert new ones.

    Args:
        site_id: Site identifier
        week_ending: ISO date string for week ending (Sunday)
        items: List of item dicts with keys: sku, description, quantity, unit_price, vendor, location

    Returns:
        Number of items saved
    """
    with get_db() as conn:
        saved = 0
        for item in items:
            sku = item.get("sku") or item.get("Dist #") or item.get("Item Number")
            if not sku:
                continue

            desc = item.get("description") or item.get("Item Description") or item.get("Description") or ""
            qty = float(item.get("quantity") or item.get("Quantity") or 0)
            price = float(item.get("unit_price") or item.get("Unit Price") or item.get("Price") or 0)
            total = qty * price
            vendor = item.get("vendor") or item.get("Vendor") or ""
            location = item.get("location") or item.get("Location") or item.get("GL Code") or ""

            item_id = str(uuid.uuid4())

            # UPSERT: Insert or replace on conflict
            conn.execute("""
                INSERT INTO inventory_item_history
                    (id, site_id, week_ending, sku, description, quantity, unit_price, total_value, vendor, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(site_id, week_ending, sku) DO UPDATE SET
                    description = excluded.description,
                    quantity = excluded.quantity,
                    unit_price = excluded.unit_price,
                    total_value = excluded.total_value,
                    vendor = excluded.vendor,
                    location = excluded.location
            """, (item_id, site_id, week_ending, str(sku), desc[:200], qty, price, total, vendor[:100], location[:100]))
            saved += 1

        return saved


def get_weekly_item_snapshot(
    site_id: str,
    week_ending: str
) -> List[Dict[str, Any]]:
    """
    Get all items from a specific week's snapshot.

    Args:
        site_id: Site identifier
        week_ending: ISO date string for week ending (Sunday)

    Returns:
        List of item dictionaries
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT sku, description, quantity, unit_price, total_value, vendor, location, created_at
            FROM inventory_item_history
            WHERE site_id = ? AND week_ending = ?
            ORDER BY description
        """, (site_id, week_ending))

        return rows_to_dicts(cursor.fetchall())


def get_item_history(
    site_id: str,
    sku: str,
    weeks: int = 12
) -> List[Dict[str, Any]]:
    """
    Get history for a specific item across multiple weeks.

    Args:
        site_id: Site identifier
        sku: Item SKU
        weeks: Number of weeks to look back (default 12)

    Returns:
        List of weekly records for this item, ordered by week_ending desc
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT week_ending, quantity, unit_price, total_value, description, vendor, location
            FROM inventory_item_history
            WHERE site_id = ? AND sku = ?
            ORDER BY week_ending DESC
            LIMIT ?
        """, (site_id, sku, weeks))

        return rows_to_dicts(cursor.fetchall())


def compare_weeks(
    site_id: str,
    week1: str,
    week2: str
) -> Dict[str, Any]:
    """
    Compare inventory between two weeks.

    Args:
        site_id: Site identifier
        week1: Earlier week (ISO date)
        week2: Later week (ISO date)

    Returns:
        Dictionary with added, removed, changed items and summary stats
    """
    items1 = {item["sku"]: item for item in get_weekly_item_snapshot(site_id, week1)}
    items2 = {item["sku"]: item for item in get_weekly_item_snapshot(site_id, week2)}

    skus1 = set(items1.keys())
    skus2 = set(items2.keys())

    added_skus = skus2 - skus1
    removed_skus = skus1 - skus2
    common_skus = skus1 & skus2

    added = [items2[sku] for sku in added_skus]
    removed = [items1[sku] for sku in removed_skus]

    changed = []
    for sku in common_skus:
        item1 = items1[sku]
        item2 = items2[sku]

        qty_change = item2["quantity"] - item1["quantity"]
        value_change = item2["total_value"] - item1["total_value"]

        if qty_change != 0 or abs(value_change) > 0.01:
            changed.append({
                "sku": sku,
                "description": item2["description"],
                "previous_qty": item1["quantity"],
                "current_qty": item2["quantity"],
                "qty_change": qty_change,
                "previous_value": item1["total_value"],
                "current_value": item2["total_value"],
                "value_change": value_change,
            })

    # Sort by absolute value change
    changed.sort(key=lambda x: abs(x["value_change"]), reverse=True)

    # Calculate summary
    total_value_1 = sum(items1[sku]["total_value"] for sku in skus1)
    total_value_2 = sum(items2[sku]["total_value"] for sku in skus2)

    return {
        "week1": week1,
        "week2": week2,
        "added": added[:50],  # Limit to top 50
        "removed": removed[:50],
        "changed": changed[:50],
        "summary": {
            "added_count": len(added_skus),
            "removed_count": len(removed_skus),
            "changed_count": len(changed),
            "week1_total_value": total_value_1,
            "week2_total_value": total_value_2,
            "value_change": total_value_2 - total_value_1,
            "week1_item_count": len(skus1),
            "week2_item_count": len(skus2),
        }
    }


def get_available_weeks(
    site_id: str,
    limit: int = 52
) -> List[str]:
    """
    Get list of available week snapshots for a site.

    Args:
        site_id: Site identifier
        limit: Maximum number of weeks to return (default 52)

    Returns:
        List of week_ending dates (ISO format), ordered newest first
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT DISTINCT week_ending
            FROM inventory_item_history
            WHERE site_id = ?
            ORDER BY week_ending DESC
            LIMIT ?
        """, (site_id, limit))

        return [row[0] for row in cursor.fetchall()]


def get_week_summary(site_id: str, week_ending: str) -> Dict[str, Any]:
    """
    Get summary statistics for a specific week.

    Args:
        site_id: Site identifier
        week_ending: ISO date string for week ending

    Returns:
        Summary with item count, total value, etc.
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT
                COUNT(*) as item_count,
                COALESCE(SUM(quantity), 0) as total_quantity,
                COALESCE(SUM(total_value), 0) as total_value
            FROM inventory_item_history
            WHERE site_id = ? AND week_ending = ?
        """, (site_id, week_ending))

        row = cursor.fetchone()
        if row:
            return {
                "week_ending": week_ending,
                "item_count": row[0],
                "total_quantity": row[1],
                "total_value": row[2]
            }
        return {
            "week_ending": week_ending,
            "item_count": 0,
            "total_quantity": 0,
            "total_value": 0
        }
