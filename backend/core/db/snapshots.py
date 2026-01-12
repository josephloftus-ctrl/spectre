"""
Inventory snapshot database operations (safe state return).
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import uuid

from .base import get_db


def create_inventory_snapshot(
    site_id: str,
    snapshot_data: List[Dict[str, Any]],
    name: Optional[str] = None,
    source_file_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a snapshot of inventory state for safe restoration."""
    snapshot_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    if not name:
        name = f"Snapshot {now[:10]}"

    # Calculate totals
    item_count = len(snapshot_data)
    total_value = sum(
        (item.get("quantity", 0) * (item.get("unit_price", 0) or 0))
        for item in snapshot_data
    )

    with get_db() as conn:
        conn.execute("""
            INSERT INTO inventory_snapshots
            (id, site_id, name, source_file_id, snapshot_data, item_count, total_value, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
        """, (snapshot_id, site_id, name, source_file_id, json.dumps(snapshot_data),
              item_count, total_value, now))

    return get_inventory_snapshot(snapshot_id)


def get_inventory_snapshot(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """Get a snapshot by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM inventory_snapshots WHERE id = ?",
            (snapshot_id,)
        ).fetchone()
        if row:
            result = dict(row)
            result["snapshot_data"] = json.loads(result.get("snapshot_data") or "[]")
            return result
    return None


def list_inventory_snapshots(
    site_id: str,
    status: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """List inventory snapshots for a site."""
    query = "SELECT id, site_id, name, source_file_id, item_count, total_value, status, created_at FROM inventory_snapshots WHERE site_id = ?"
    params = [site_id]

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def restore_inventory_snapshot(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """Mark a snapshot as restored (for tracking)."""
    with get_db() as conn:
        conn.execute(
            "UPDATE inventory_snapshots SET status = 'restored' WHERE id = ?",
            (snapshot_id,)
        )

    return get_inventory_snapshot(snapshot_id)


def delete_inventory_snapshot(snapshot_id: str) -> bool:
    """Delete a snapshot."""
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM inventory_snapshots WHERE id = ?",
            (snapshot_id,)
        )
        return result.rowcount > 0


def get_latest_snapshot(site_id: str) -> Optional[Dict[str, Any]]:
    """Get the most recent active snapshot for a site."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM inventory_snapshots
            WHERE site_id = ? AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """, (site_id,)).fetchone()
        if row:
            result = dict(row)
            result["snapshot_data"] = json.loads(result.get("snapshot_data") or "[]")
            return result
    return None
