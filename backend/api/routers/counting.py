"""
Count sessions API router.
"""
from fastapi import APIRouter, HTTPException, Form, Query
from typing import Any, Dict, Optional
import json

from backend.core.database import (
    FileStatus, list_files,
    create_count_session, get_count_session, list_count_sessions,
    update_count_session, add_count_item, list_count_items,
    delete_count_session, bulk_add_count_items, get_item_location,
    bulk_set_item_locations
)
from backend.core.categorize import categorize_item, get_location_sort_key
from backend.api.models import CountItemRequest, BulkCountItemsRequest

router = APIRouter(prefix="/api/count-sessions", tags=["Count Sessions"])


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


@router.get("")
def get_count_sessions(
    site_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200)
):
    """List count sessions with optional filters."""
    sessions = list_count_sessions(site_id=site_id, status=status, limit=limit)
    return {"sessions": sessions, "count": len(sessions)}


@router.post("")
def create_new_count_session(
    site_id: str = Form(...),
    name: Optional[str] = Form(None)
):
    """Create a new inventory count session."""
    session = create_count_session(site_id=site_id, name=name)
    return {"success": True, "session": session}


@router.get("/{session_id}")
def get_count_session_detail(session_id: str):
    """Get count session details including items."""
    session = get_count_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    items = list_count_items(session_id)
    return {
        "session": session,
        "items": items,
        "item_count": len(items)
    }


@router.put("/{session_id}")
def update_count_session_status(
    session_id: str,
    status: Optional[str] = Form(None),
    name: Optional[str] = Form(None)
):
    """Update count session status or name."""
    session = update_count_session(session_id, status=status, name=name)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session": session}


@router.post("/{session_id}/items")
def add_count_session_item(session_id: str, request: CountItemRequest):
    """Add or update a counted item in a session."""
    session = get_count_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    item = add_count_item(
        session_id=session_id,
        sku=request.sku,
        description=request.description,
        counted_qty=request.counted_qty,
        expected_qty=request.expected_qty,
        unit_price=request.unit_price,
        uom=request.uom,
        location=request.location,
        notes=request.notes
    )
    return {"success": True, "item": item}


@router.post("/{session_id}/bulk")
def bulk_add_count_items_endpoint(session_id: str, request: BulkCountItemsRequest):
    """Bulk add items to a count session from inventory snapshot."""
    session = get_count_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    added = bulk_add_count_items(session_id, request.items)

    session = get_count_session(session_id)
    return {
        "success": True,
        "added_count": added,
        "session": session
    }


@router.post("/{session_id}/populate-from-inventory")
def populate_count_from_inventory(
    session_id: str,
    skip_never_count: bool = Query(True, description="Skip items marked as NEVER INVENTORY"),
    auto_categorize: bool = Query(True, description="Auto-assign locations to items")
):
    """
    Populate a count session with items from the site's latest inventory valuation file.

    Items are automatically categorized by location and sorted in walking order:
    Freezer -> Walk In Cooler -> Beverage Room -> Dry Storage Food -> Dry Storage Supplies -> Chemical Locker

    Items categorized as 'NEVER INVENTORY' (fresh produce, dry seasonings, etc.) are skipped by default.
    """
    session = get_count_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    site_id = session["site_id"]

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
    if not rows:
        raise HTTPException(status_code=404, detail="No items found in inventory file")

    normalized_items = []
    location_updates = []
    skipped_never_count = 0

    for row in rows:
        item = normalize_inventory_row(row)
        if not item:
            continue

        sku = item.get("sku", "")
        description = item.get("description", "")
        brand = row.get("Brand", "")
        pack = row.get("Pack", "")

        saved_location = get_item_location(site_id, sku)

        if saved_location:
            location = saved_location["location"]
            never_count = bool(saved_location.get("never_count", 0))
        elif auto_categorize:
            location, never_count = categorize_item(description, brand, pack)
            location_updates.append({
                "sku": sku,
                "location": location,
                "never_count": never_count,
                "auto_assigned": True
            })
        else:
            location = "UNASSIGNED"
            never_count = False

        if skip_never_count and (never_count or location == "NEVER INVENTORY"):
            skipped_never_count += 1
            continue

        item["location"] = location
        normalized_items.append(item)

    if not normalized_items:
        raise HTTPException(status_code=404, detail="No countable items found in inventory file")

    if location_updates:
        bulk_set_item_locations(site_id, location_updates)

    normalized_items.sort(key=lambda x: (
        get_location_sort_key(x.get("location", "UNASSIGNED")),
        x.get("description", "").upper()
    ))

    added = bulk_add_count_items(session_id, normalized_items)

    session = get_count_session(session_id)
    items = list_count_items(session_id)

    location_counts = {}
    for item in normalized_items:
        loc = item.get("location", "UNASSIGNED")
        location_counts[loc] = location_counts.get(loc, 0) + 1

    return {
        "success": True,
        "added_count": added,
        "skipped_never_count": skipped_never_count,
        "total_rows": len(rows),
        "source_file": file_record.get("filename"),
        "location_summary": location_counts,
        "session": session,
        "items": items
    }


@router.delete("/{session_id}")
def delete_count_session_endpoint(session_id: str):
    """Delete a count session and all its items."""
    deleted = delete_count_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": "Session deleted"}
