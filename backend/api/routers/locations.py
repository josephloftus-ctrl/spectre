"""
Item locations API router (Smart Sorting).
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, List, Optional
import json

from backend.core.database import (
    FileStatus, DEFAULT_LOCATION_ORDER, list_files,
    get_item_location, set_item_location, bulk_set_item_locations,
    list_item_locations, get_location_summary, delete_item_location,
    clear_item_locations, get_location_order, set_location_order,
    reset_location_order, list_available_locations
)
from backend.core.categorize import categorize_item, LOCATION_ORDER, get_location_sort_key

router = APIRouter(prefix="/api/locations", tags=["Locations"])


def normalize_inventory_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract standardized item data from a parsed inventory row."""
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

    if not item["sku"] and item["description"]:
        item["sku"] = item["description"][:20].upper().replace(" ", "_")
    if not item["sku"] and not item["description"]:
        return None
    if not item["description"]:
        item["description"] = item["sku"]

    return item


@router.get("/{site_id}")
def get_site_locations(
    site_id: str,
    location: Optional[str] = Query(None, description="Filter by location"),
    include_never_count: bool = Query(True, description="Include NEVER INVENTORY items")
):
    """Get all item locations for a site."""
    items = list_item_locations(site_id, location=location, include_never_count=include_never_count)
    summary = get_location_summary(site_id)
    return {
        "items": items,
        "count": len(items),
        "summary": summary,
        "location_order": list(LOCATION_ORDER.keys())
    }


@router.get("/{site_id}/summary")
def get_site_location_summary(site_id: str):
    """Get summary of items per location for a site."""
    summary = get_location_summary(site_id)
    order = get_location_order(site_id)
    sorted_locs = sorted(order.items(), key=lambda x: x[1])
    return {
        "summary": summary,
        "location_order": [loc for loc, _ in sorted_locs]
    }


@router.get("/{site_id}/order")
def get_walking_order(site_id: str):
    """
    Get the walking order for locations at a site.
    Returns custom order if set, otherwise default order.
    """
    order = get_location_order(site_id)
    sorted_locations = sorted(order.items(), key=lambda x: x[1])
    return {
        "site_id": site_id,
        "order": [loc for loc, _ in sorted_locations],
        "is_custom": order != DEFAULT_LOCATION_ORDER,
        "available_locations": list_available_locations(site_id)
    }


@router.put("/{site_id}/order")
def set_walking_order(site_id: str, order: List[str]):
    """
    Set a custom walking order for locations at a site.
    Pass a list of location names in desired walking order.

    Example:
    ["Walk In Cooler", "Freezer", "Beverage Room", "Dry Storage Food", ...]
    """
    new_order = set_location_order(site_id, order)
    return {
        "success": True,
        "site_id": site_id,
        "order": order,
        "order_map": new_order
    }


@router.delete("/{site_id}/order")
def reset_walking_order(site_id: str):
    """Reset walking order to defaults for a site."""
    reset_location_order(site_id)
    return {
        "success": True,
        "site_id": site_id,
        "order": list(DEFAULT_LOCATION_ORDER.keys()),
        "message": "Walking order reset to defaults"
    }


@router.get("/{site_id}/available")
def get_available_locations_endpoint(site_id: str):
    """Get all unique locations used by items at a site."""
    locations = list_available_locations(site_id)
    return {
        "site_id": site_id,
        "locations": locations,
        "count": len(locations)
    }


@router.get("/{site_id}/{sku}")
def get_item_location_endpoint(site_id: str, sku: str):
    """Get location for a specific item."""
    location = get_item_location(site_id, sku)
    if not location:
        raise HTTPException(status_code=404, detail="Item location not found")
    return location


@router.put("/{site_id}/{sku}")
def set_item_location_endpoint(
    site_id: str,
    sku: str,
    location: str = Query(..., description="Location name"),
    zone: Optional[str] = Query(None, description="Sub-area within location"),
    sort_order: int = Query(0, description="Sort order within location"),
    never_count: bool = Query(False, description="Skip this item during counts")
):
    """Set or update location for an item."""
    result = set_item_location(
        site_id=site_id,
        sku=sku,
        location=location,
        zone=zone,
        sort_order=sort_order,
        never_count=never_count,
        auto_assigned=False
    )
    return result


@router.post("/{site_id}/bulk")
def bulk_set_locations(site_id: str, items: List[Dict[str, Any]]):
    """
    Bulk set locations for multiple items.
    Each item should have: sku, location, and optionally zone, sort_order, never_count
    """
    updated = bulk_set_item_locations(site_id, items)
    return {"success": True, "updated_count": updated}


@router.post("/{site_id}/auto-categorize")
def auto_categorize_site(site_id: str, overwrite: bool = Query(False)):
    """
    Auto-categorize all items for a site based on their descriptions.
    Uses keyword matching to assign locations.

    Args:
        overwrite: If True, overwrite existing manual assignments
    """
    files = list_files(status=FileStatus.COMPLETED, site_id=site_id, limit=1)
    if not files:
        raise HTTPException(status_code=404, detail="No inventory file found for this site")

    file_record = files[0]
    parsed_data = file_record.get("parsed_data")

    if not parsed_data:
        raise HTTPException(status_code=404, detail="No parsed data in inventory file")

    if isinstance(parsed_data, str):
        data = json.loads(parsed_data)
    else:
        data = parsed_data

    rows = data.get("rows", [])

    categorized = 0
    skipped = 0
    location_updates = []

    for row in rows:
        item = normalize_inventory_row(row)
        if not item:
            continue

        sku = item.get("sku", "")
        if not sku:
            continue

        existing = get_item_location(site_id, sku)
        if existing and not existing.get("auto_assigned", True) and not overwrite:
            skipped += 1
            continue

        description = item.get("description", "")
        brand = row.get("Brand", "")
        pack = row.get("Pack", "")

        location, never_count = categorize_item(description, brand, pack)

        location_updates.append({
            "sku": sku,
            "location": location,
            "never_count": never_count,
            "auto_assigned": True
        })
        categorized += 1

    if location_updates:
        bulk_set_item_locations(site_id, location_updates)

    summary = get_location_summary(site_id)

    return {
        "success": True,
        "categorized": categorized,
        "skipped_manual": skipped,
        "total_rows": len(rows),
        "summary": summary
    }


@router.delete("/{site_id}/{sku}")
def delete_item_location_endpoint(site_id: str, sku: str):
    """Delete location for a specific item."""
    deleted = delete_item_location(site_id, sku)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item location not found")
    return {"success": True, "message": "Location deleted"}


@router.delete("/{site_id}")
def clear_site_locations(site_id: str):
    """Clear all item locations for a site."""
    deleted = clear_item_locations(site_id)
    return {"success": True, "deleted_count": deleted}
