"""
Inventory snapshots API router (Safe State Return).
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.core.database import (
    create_inventory_snapshot, get_inventory_snapshot, list_inventory_snapshots,
    restore_inventory_snapshot, delete_inventory_snapshot, get_latest_snapshot
)

router = APIRouter(prefix="/api/inventory", tags=["Inventory Snapshots"])


@router.get("/snapshots/{site_id}")
def get_site_snapshots(
    site_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=100)
):
    """List inventory snapshots for a site (restore points)."""
    snapshots = list_inventory_snapshots(site_id, status=status, limit=limit)
    return {"snapshots": snapshots, "count": len(snapshots)}


@router.get("/snapshots/{site_id}/latest")
def get_latest_site_snapshot(site_id: str):
    """Get the most recent active snapshot for restoring."""
    snapshot = get_latest_snapshot(site_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="No active snapshot found")
    return snapshot


@router.get("/snapshot/{snapshot_id}")
def get_snapshot_detail(snapshot_id: str):
    """Get full snapshot details including data."""
    snapshot = get_inventory_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot


@router.post("/snapshot/{snapshot_id}/restore")
def restore_snapshot(snapshot_id: str):
    """
    Restore inventory to a snapshot state.
    Returns the snapshot data that should be used to regenerate the inventory export.
    """
    snapshot = restore_inventory_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return {
        "success": True,
        "message": "Snapshot marked for restoration",
        "snapshot": snapshot
    }


@router.delete("/snapshot/{snapshot_id}")
def delete_snapshot(snapshot_id: str):
    """Delete a snapshot."""
    deleted = delete_inventory_snapshot(snapshot_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return {"success": True, "message": "Snapshot deleted"}
