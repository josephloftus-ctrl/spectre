"""
Scores API router.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
import uuid

from backend.core.database import (
    get_file, list_files,
    get_unit_score, list_unit_scores,
    get_score_history, get_score_trend, save_score_snapshot
)
from backend.core.worker import refresh_all_scores

router = APIRouter(prefix="/api/scores", tags=["Scores"])


@router.get("")
def get_all_scores(
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500)
):
    """
    Get all unit scores, sorted by score descending (worst first).
    Returns status indicators, not raw scores.
    Now includes file attribution info.
    """
    scores = list_unit_scores(status=status, limit=limit)

    units = []
    for s in scores:
        trend = get_score_trend(s["site_id"])

        source_file = None
        if s.get("file_id"):
            file_record = get_file(s["file_id"])
            if file_record:
                source_file = {
                    "id": file_record["id"],
                    "filename": file_record["filename"],
                    "processed_at": file_record.get("processed_at")
                }

        units.append({
            "site_id": s["site_id"],
            "status": s["status"],
            "item_flags": s["item_flag_count"],
            "total_value": s["total_value"],
            "last_scored": s["created_at"],
            "trend": trend,
            "source_file": source_file
        })

    return {
        "units": units,
        "count": len(units)
    }


@router.get("/{site_id}")
def get_site_score(site_id: str):
    """
    Get score details for a specific site.
    Includes flagged items for drill-down.
    """
    score = get_unit_score(site_id)
    if not score:
        raise HTTPException(status_code=404, detail="No score found for site")

    trend = get_score_trend(site_id)

    return {
        "site_id": site_id,
        "status": score["status"],
        "item_flags": score["item_flag_count"],
        "total_value": score["total_value"],
        "item_count": score["item_count"],
        "last_scored": score["created_at"],
        "trend": trend,
        "flagged_items": score["flagged_items"]
    }


@router.get("/{site_id}/items")
def get_site_flagged_items(site_id: str):
    """Get just the flagged items for a site (for drill-down)."""
    score = get_unit_score(site_id)
    if not score:
        raise HTTPException(status_code=404, detail="No score found for site")

    return {
        "site_id": site_id,
        "items": score["flagged_items"],
        "count": score["item_flag_count"]
    }


@router.get("/{site_id}/history")
def get_site_score_history(
    site_id: str,
    limit: int = Query(12, le=52)
):
    """Get weekly score history for trend analysis."""
    history = get_score_history(site_id, limit=limit)
    return {
        "site_id": site_id,
        "history": history,
        "count": len(history)
    }


@router.post("/refresh")
def trigger_score_refresh():
    """Manually trigger a re-score of all sites."""
    count = refresh_all_scores()
    return {
        "success": True,
        "message": f"Queued {count} sites for re-scoring"
    }


@router.post("/snapshot")
def create_score_snapshot():
    """
    Manually create a score history snapshot for all sites.
    Use this to immediately capture current scores for week-over-week comparison
    instead of waiting for the Sunday 2 AM automatic snapshot.
    """
    snapshot_date = datetime.utcnow().strftime("%Y-%m-%d")
    current_scores = list_unit_scores(limit=1000)

    snapshots_created = 0
    for score in current_scores:
        snapshot_id = str(uuid.uuid4())
        save_score_snapshot(
            snapshot_id=snapshot_id,
            site_id=score["site_id"],
            score=score["score"],
            status=score["status"],
            item_flag_count=score["item_flag_count"],
            room_flag_count=score.get("room_flag_count", 0),
            total_value=score.get("total_value", 0),
            snapshot_date=snapshot_date
        )
        snapshots_created += 1

    return {
        "success": True,
        "message": f"Created {snapshots_created} score snapshots for {snapshot_date}",
        "snapshot_date": snapshot_date,
        "count": snapshots_created
    }


@router.get("/{site_id}/files")
def get_site_scored_files(site_id: str):
    """
    Get all files that have been processed for a specific site.
    Shows which files contributed to scoring and when.
    """
    files = list_files(site_id=site_id, limit=50)

    current_score = get_unit_score(site_id)
    active_file_id = current_score["file_id"] if current_score else None

    file_list = []
    for f in files:
        file_list.append({
            "id": f["id"],
            "filename": f["filename"],
            "status": f["status"],
            "processed_at": f.get("processed_at"),
            "created_at": f["created_at"],
            "is_active_score": f["id"] == active_file_id
        })

    return {
        "site_id": site_id,
        "files": file_list,
        "active_file_id": active_file_id,
        "count": len(file_list)
    }
