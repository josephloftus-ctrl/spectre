"""
History API router.
"""
from fastapi import APIRouter, HTTPException, Query
import json

from backend.core.database import (
    FileStatus, list_files,
    get_unit_score, get_score_history
)
from backend.core.db.history import (
    get_available_weeks,
    compare_weeks,
    get_item_history,
    get_week_summary
)

router = APIRouter(prefix="/api/history", tags=["History"])


@router.get("/{site_id}")
def get_site_history(
    site_id: str,
    weeks: int = Query(3, ge=1, le=52, description="Number of weeks of history (default: 3 = current + 2 previous)"),
    days: int = Query(None, le=365, description="Deprecated: use weeks instead")
):
    """
    Get historical data for a site.
    Returns score history plus computed metrics.

    Default shows current week + 2 previous weeks (weeks=3).
    Set weeks higher to see more history (max 52 weeks / 1 year).
    Data is stored forever, this just controls the view.
    """
    # Support legacy days param for backwards compatibility
    if days is not None:
        weeks = max(1, days // 7)

    history = get_score_history(site_id, limit=weeks)
    current = get_unit_score(site_id)

    if not current and not history:
        raise HTTPException(status_code=404, detail="No data found for site")

    value_trend = None
    count_trend = None

    if len(history) >= 2:
        latest = history[0]
        previous = history[1]

        if previous.get("total_value", 0) > 0:
            value_change = latest.get("total_value", 0) - previous.get("total_value", 0)
            value_pct = (value_change / previous["total_value"]) * 100
            value_trend = {
                "change": value_change,
                "percent": round(value_pct, 1),
                "direction": "up" if value_change > 0 else "down" if value_change < 0 else "stable"
            }

        prev_count = previous.get("item_flag_count", 0)
        curr_count = latest.get("item_flag_count", 0)
        count_change = curr_count - prev_count
        count_trend = {
            "change": count_change,
            "direction": "up" if count_change > 0 else "down" if count_change < 0 else "stable"
        }

    return {
        "site_id": site_id,
        "current": current,
        "history": history,
        "trends": {
            "value": value_trend,
            "flags": count_trend
        }
    }


@router.get("/{site_id}/movers")
def get_site_movers(
    site_id: str,
    limit: int = Query(10, le=50)
):
    """
    Get items with biggest quantity changes between latest and previous file.
    """
    files = list_files(status=FileStatus.COMPLETED, site_id=site_id, limit=2)

    if len(files) < 2:
        return {
            "site_id": site_id,
            "movers": [],
            "message": "Need at least 2 files to compare"
        }

    def get_items(file_record):
        parsed = file_record.get("parsed_data")
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        if not parsed:
            return {}

        items = {}
        for row in parsed.get("rows", []):
            sku = row.get("Dist #") or row.get("Item Number") or row.get("SKU")
            qty = row.get("Quantity", 0)
            desc = row.get("Item Description") or row.get("Description") or ""
            if sku:
                try:
                    items[str(sku)] = {
                        "quantity": float(qty) if qty else 0,
                        "description": str(desc)[:50]
                    }
                except (ValueError, TypeError):
                    pass
        return items

    latest_items = get_items(files[0])
    previous_items = get_items(files[1])

    movers = []
    all_skus = set(latest_items.keys()) | set(previous_items.keys())

    for sku in all_skus:
        latest = latest_items.get(sku, {})
        previous = previous_items.get(sku, {})

        latest_qty = latest.get("quantity", 0)
        previous_qty = previous.get("quantity", 0)
        change = latest_qty - previous_qty

        if change != 0:
            movers.append({
                "sku": sku,
                "description": latest.get("description") or previous.get("description", ""),
                "previous_qty": previous_qty,
                "current_qty": latest_qty,
                "change": change,
                "direction": "up" if change > 0 else "down"
            })

    movers.sort(key=lambda x: abs(x["change"]), reverse=True)

    return {
        "site_id": site_id,
        "movers": movers[:limit],
        "latest_file": files[0].get("filename"),
        "previous_file": files[1].get("filename")
    }


@router.get("/{site_id}/anomalies")
def get_site_anomalies(
    site_id: str,
    limit: int = Query(20, le=100)
):
    """
    Get items that appeared or vanished between latest and previous file.
    """
    files = list_files(status=FileStatus.COMPLETED, site_id=site_id, limit=2)

    if len(files) < 2:
        return {
            "site_id": site_id,
            "appeared": [],
            "vanished": [],
            "message": "Need at least 2 files to compare"
        }

    def get_items(file_record):
        parsed = file_record.get("parsed_data")
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        if not parsed:
            return {}

        items = {}
        for row in parsed.get("rows", []):
            sku = row.get("Dist #") or row.get("Item Number") or row.get("SKU")
            qty = row.get("Quantity", 0)
            desc = row.get("Item Description") or row.get("Description") or ""
            price = row.get("Unit Price") or row.get("Price") or 0
            if sku:
                try:
                    items[str(sku)] = {
                        "quantity": float(qty) if qty else 0,
                        "description": str(desc)[:50],
                        "price": float(price) if price else 0
                    }
                except (ValueError, TypeError):
                    pass
        return items

    latest_items = get_items(files[0])
    previous_items = get_items(files[1])

    appeared = []
    for sku, data in latest_items.items():
        if sku not in previous_items:
            appeared.append({
                "sku": sku,
                "description": data["description"],
                "quantity": data["quantity"],
                "price": data["price"]
            })

    vanished = []
    for sku, data in previous_items.items():
        if sku not in latest_items:
            vanished.append({
                "sku": sku,
                "description": data["description"],
                "quantity": data["quantity"],
                "price": data["price"]
            })

    appeared.sort(key=lambda x: x["quantity"], reverse=True)
    vanished.sort(key=lambda x: x["quantity"], reverse=True)

    return {
        "site_id": site_id,
        "appeared": appeared[:limit],
        "vanished": vanished[:limit],
        "appeared_count": len(appeared),
        "vanished_count": len(vanished),
        "latest_file": files[0].get("filename"),
        "previous_file": files[1].get("filename")
    }


# ============== Item-Level Weekly History ==============

@router.get("/{site_id}/weeks")
def get_site_weeks(
    site_id: str,
    limit: int = Query(52, le=104)
):
    """Get available weekly snapshots for a site."""
    weeks = get_available_weeks(site_id, limit=limit)
    return {
        "site_id": site_id,
        "weeks": weeks,
        "count": len(weeks)
    }


@router.get("/{site_id}/compare")
def compare_site_weeks(
    site_id: str,
    week1: str = Query(..., description="Earlier week (YYYY-MM-DD)"),
    week2: str = Query(..., description="Later week (YYYY-MM-DD)")
):
    """Compare inventory between two weeks at item level."""
    result = compare_weeks(site_id, week1, week2)

    if result["summary"]["week1_item_count"] == 0 and result["summary"]["week2_item_count"] == 0:
        raise HTTPException(status_code=404, detail="No data found for either week")

    return result


@router.get("/{site_id}/items/{sku}")
def get_item_weekly_history(
    site_id: str,
    sku: str,
    weeks: int = Query(12, ge=1, le=52)
):
    """Get weekly history for a specific item."""
    history = get_item_history(site_id, sku, weeks=weeks)
    return {
        "site_id": site_id,
        "sku": sku,
        "history": history,
        "count": len(history)
    }
