"""
Off-catalog items database operations.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

from .base import get_db


def create_off_catalog_item(
    site_id: str,
    dist_num: str,
    cust_num: str,
    description: str = "",
    pack: str = "",
    uom: str = "",
    unit_price: Optional[float] = None,
    distributor: str = "",
    **kwargs
) -> Dict[str, Any]:
    """
    Create a new off-catalog item.

    Off-catalog items are custom items not in the Master Order Guide.
    Required fields: dist_num (Dist #) and cust_num (Cust #).
    """
    item_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT INTO off_catalog_items
            (id, site_id, dist_num, cust_num, description, pack, uom, break_uom,
             unit_price, break_price, distributor, distribution_center, brand,
             manufacturer, manufacturer_num, gtin, upc, catch_weight,
             average_weight, units_per_case, location, area, place, notes,
             is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (
            item_id, site_id, dist_num, cust_num, description, pack,
            uom, kwargs.get("break_uom"),
            unit_price, kwargs.get("break_price"),
            distributor, kwargs.get("distribution_center"),
            kwargs.get("brand"), kwargs.get("manufacturer"),
            kwargs.get("manufacturer_num"), kwargs.get("gtin"),
            kwargs.get("upc"), kwargs.get("catch_weight", 0),
            kwargs.get("average_weight"), kwargs.get("units_per_case"),
            kwargs.get("location"), kwargs.get("area"), kwargs.get("place"),
            kwargs.get("notes"), now, now
        ))

    return get_off_catalog_item(site_id, cust_num)


def get_off_catalog_item(site_id: str, cust_num: str) -> Optional[Dict[str, Any]]:
    """Get an off-catalog item by customer number."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM off_catalog_items WHERE site_id = ? AND cust_num = ? AND is_active = 1",
            (site_id, cust_num)
        ).fetchone()
        if row:
            return dict(row)
    return None


def get_off_catalog_item_by_dist(site_id: str, dist_num: str) -> Optional[Dict[str, Any]]:
    """Get an off-catalog item by distributor number."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM off_catalog_items WHERE site_id = ? AND dist_num = ? AND is_active = 1",
            (site_id, dist_num)
        ).fetchone()
        if row:
            return dict(row)
    return None


def update_off_catalog_item(
    site_id: str,
    cust_num: str,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """Update an off-catalog item."""
    now = datetime.utcnow().isoformat()

    # Build update query dynamically
    allowed_fields = {
        "dist_num", "description", "pack", "uom", "break_uom",
        "unit_price", "break_price", "distributor", "distribution_center",
        "brand", "manufacturer", "manufacturer_num", "gtin", "upc",
        "catch_weight", "average_weight", "units_per_case",
        "location", "area", "place", "notes"
    }

    updates = []
    values = []
    for key, value in kwargs.items():
        if key in allowed_fields:
            updates.append(f"{key} = ?")
            values.append(value)

    if not updates:
        return get_off_catalog_item(site_id, cust_num)

    updates.append("updated_at = ?")
    values.append(now)
    values.extend([site_id, cust_num])

    with get_db() as conn:
        conn.execute(f"""
            UPDATE off_catalog_items
            SET {", ".join(updates)}
            WHERE site_id = ? AND cust_num = ? AND is_active = 1
        """, values)

    return get_off_catalog_item(site_id, cust_num)


def delete_off_catalog_item(site_id: str, cust_num: str, hard_delete: bool = False) -> bool:
    """Delete an off-catalog item (soft or hard delete)."""
    with get_db() as conn:
        if hard_delete:
            result = conn.execute(
                "DELETE FROM off_catalog_items WHERE site_id = ? AND cust_num = ?",
                (site_id, cust_num)
            )
        else:
            result = conn.execute(
                "UPDATE off_catalog_items SET is_active = 0, updated_at = ? WHERE site_id = ? AND cust_num = ?",
                (datetime.utcnow().isoformat(), site_id, cust_num)
            )
        return result.rowcount > 0


def list_off_catalog_items(
    site_id: str,
    include_inactive: bool = False
) -> List[Dict[str, Any]]:
    """List all off-catalog items for a site."""
    with get_db() as conn:
        if include_inactive:
            rows = conn.execute(
                "SELECT * FROM off_catalog_items WHERE site_id = ? ORDER BY description",
                (site_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM off_catalog_items WHERE site_id = ? AND is_active = 1 ORDER BY description",
                (site_id,)
            ).fetchall()
        return [dict(row) for row in rows]


def bulk_import_off_catalog_items(
    site_id: str,
    items: List[Dict[str, Any]],
    update_existing: bool = True
) -> Dict[str, int]:
    """Bulk import off-catalog items."""
    now = datetime.utcnow().isoformat()
    created = 0
    updated = 0
    skipped = 0

    with get_db() as conn:
        for item in items:
            dist_num = item.get("dist_num") or item.get("Dist #") or ""
            cust_num = item.get("cust_num") or item.get("Cust #") or ""

            if not dist_num or not cust_num:
                skipped += 1
                continue

            # Check if exists
            existing = conn.execute(
                "SELECT id FROM off_catalog_items WHERE site_id = ? AND cust_num = ?",
                (site_id, cust_num)
            ).fetchone()

            if existing:
                if update_existing:
                    conn.execute("""
                        UPDATE off_catalog_items SET
                            dist_num = ?, description = ?, pack = ?, uom = ?,
                            unit_price = ?, distributor = ?, brand = ?, gtin = ?,
                            location = ?, is_active = 1, updated_at = ?
                        WHERE site_id = ? AND cust_num = ?
                    """, (
                        dist_num,
                        item.get("description") or item.get("Item Description") or "",
                        item.get("pack") or item.get("Pack") or "",
                        item.get("uom") or item.get("UOM") or "",
                        item.get("unit_price") or item.get("Price"),
                        item.get("distributor") or item.get("Distributor") or "",
                        item.get("brand") or item.get("Brand") or "",
                        item.get("gtin") or item.get("GTIN") or "",
                        item.get("location") or item.get("Location") or "",
                        now, site_id, cust_num
                    ))
                    updated += 1
                else:
                    skipped += 1
            else:
                item_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO off_catalog_items
                    (id, site_id, dist_num, cust_num, description, pack, uom,
                     unit_price, distributor, brand, gtin, location,
                     is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (
                    item_id, site_id, dist_num, cust_num,
                    item.get("description") or item.get("Item Description") or "",
                    item.get("pack") or item.get("Pack") or "",
                    item.get("uom") or item.get("UOM") or "",
                    item.get("unit_price") or item.get("Price"),
                    item.get("distributor") or item.get("Distributor") or "",
                    item.get("brand") or item.get("Brand") or "",
                    item.get("gtin") or item.get("GTIN") or "",
                    item.get("location") or item.get("Location") or "",
                    now, now
                ))
                created += 1

    return {"created": created, "updated": updated, "skipped": skipped}


def generate_cust_num(site_id: str, prefix: str = "SPEC") -> str:
    """Generate a unique Cust # for a new off-catalog item."""
    with get_db() as conn:
        # Get highest existing number with this prefix
        row = conn.execute("""
            SELECT cust_num FROM off_catalog_items
            WHERE site_id = ? AND cust_num LIKE ?
            ORDER BY cust_num DESC LIMIT 1
        """, (site_id, f"{prefix}%")).fetchone()

        if row:
            # Extract number and increment
            try:
                num = int(row["cust_num"][len(prefix):]) + 1
            except (ValueError, IndexError):
                num = 10001
        else:
            num = 10001

        return f"{prefix}{num}"
