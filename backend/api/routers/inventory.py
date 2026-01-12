"""
Inventory API router.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, Optional
import json

from backend.core.database import (
    FileStatus, list_files, get_file,
    list_unit_scores, get_unit_score, get_score_history
)

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


@router.get("/summary")
def get_inventory_summary():
    """
    Returns global stats and list of sites with their health.
    Now reads from unit_scores database table instead of filesystem.
    """
    scores = list_unit_scores(limit=500)

    if not scores:
        return {"sites": [], "global_value": 0, "active_sites": 0, "total_issues": 0}

    site_summaries = []
    global_value = 0.0
    total_issues = 0

    for score in scores:
        delta_pct = 0.0
        history = get_score_history(score["site_id"], limit=2)
        if len(history) >= 2:
            prev_value = history[1].get("total_value", 0)
            curr_value = history[0].get("total_value", 0)
            if prev_value > 0:
                delta_pct = round(((curr_value - prev_value) / prev_value) * 100, 1)

        site_summaries.append({
            "site": score["site_id"],
            "latest_total": score["total_value"],
            "delta_pct": delta_pct,
            "issue_count": score["item_flag_count"],
            "last_updated": score["created_at"]
        })

        global_value += score["total_value"]
        total_issues += score["item_flag_count"]

    return {
        "global_value": global_value,
        "active_sites": len(scores),
        "total_issues": total_issues,
        "sites": site_summaries
    }


@router.get("/sites/{site_id}")
def get_site_detail(site_id: str):
    """
    Get site details. Now reads from unit_scores database.
    """
    score = get_unit_score(site_id)
    if not score:
        raise HTTPException(status_code=404, detail="Site not found")

    delta_pct = 0.0
    history = get_score_history(site_id, limit=2)
    if len(history) >= 2:
        prev_value = history[1].get("total_value", 0)
        curr_value = history[0].get("total_value", 0)
        if prev_value > 0:
            delta_pct = round(((curr_value - prev_value) / prev_value) * 100, 1)

    return {
        "site": site_id,
        "latest_total": score["total_value"],
        "delta_pct": delta_pct,
        "latest_date": score["created_at"],
        "total_drifts": [],
        "qty_drifts": [],
        "file_summaries": []
    }


@router.get("/sites/{site_id}/items")
def get_site_inventory_items(site_id: str, limit: int = Query(500, le=2000)):
    """
    Get inventory items from the latest valuation file for a site.
    Returns normalized item data suitable for order building or count sessions.
    """
    files = list_files(status=FileStatus.COMPLETED, site_id=site_id, limit=1)
    if not files:
        raise HTTPException(status_code=404, detail="No inventory file found for this site")

    file_record = files[0]
    parsed_data = file_record.get("parsed_data")

    if not parsed_data:
        raise HTTPException(status_code=404, detail="No parsed data in inventory file")

    try:
        if isinstance(parsed_data, str):
            data = json.loads(parsed_data)
        else:
            data = parsed_data
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid parsed data format")

    rows = data.get("rows", [])

    def normalize_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        item = {
            "sku": "",
            "description": "",
            "quantity": 0,
            "unit_price": None,
            "uom": None,
            "location": None,
            "vendor": None
        }

        for key, value in row.items():
            if not key or not isinstance(key, str):
                continue
            key_lower = key.lower().strip()

            if "sku" in key_lower or "item #" in key_lower or "item number" in key_lower or key_lower == "item":
                item["sku"] = str(value).strip() if value else ""
            elif "description" in key_lower or "item name" in key_lower:
                item["description"] = str(value).strip() if value else ""
            elif "quantity" in key_lower or key_lower == "qty" or key_lower == "count":
                try:
                    item["quantity"] = float(str(value).replace(",", "")) if value else 0
                except (ValueError, TypeError):
                    item["quantity"] = 0
            elif "unit" in key_lower and "price" in key_lower:
                try:
                    val_str = str(value).replace("$", "").replace(",", "").strip()
                    item["unit_price"] = float(val_str) if val_str else None
                except (ValueError, TypeError):
                    pass
            elif key_lower == "uom" or "unit of" in key_lower:
                item["uom"] = str(value).strip() if value else None
            elif "location" in key_lower or "loc" == key_lower:
                item["location"] = str(value).strip() if value else None
            elif "vendor" in key_lower or "supplier" in key_lower:
                item["vendor"] = str(value).strip() if value else None

        if not item["sku"] and item["description"]:
            item["sku"] = item["description"][:20].upper().replace(" ", "_")
        if not item["sku"] and not item["description"]:
            return None
        if not item["description"]:
            item["description"] = item["sku"]

        return item

    items = []
    for row in rows[:limit]:
        item = normalize_row(row)
        if item:
            items.append(item)

    return {
        "items": items,
        "count": len(items),
        "total_in_file": len(rows),
        "source_file": file_record.get("filename"),
        "file_date": file_record.get("created_at")
    }
