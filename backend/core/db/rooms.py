"""
Room management database operations.

Handles predefined rooms (Freezer, Walk In Cooler, etc.) and custom user-created rooms.
Uses item_locations table for item-to-room assignments.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
import json

from .base import get_db, DEFAULT_LOCATION_ORDER
from .locations import (
    get_item_location,
    set_item_location,
    list_item_locations,
    get_location_summary,
    get_location_order,
)
from .files import list_files
from .base import FileStatus


def list_rooms(site_id: str, include_empty: bool = True) -> List[Dict[str, Any]]:
    """
    List all rooms for a site (predefined + custom).

    Returns rooms with item counts, sorted by sort_order.
    """
    # Get item counts per location
    location_counts = get_location_summary(site_id)

    # Get custom room order if exists
    location_order = get_location_order(site_id)

    # Build predefined rooms list
    predefined_rooms = []
    for name, default_order in DEFAULT_LOCATION_ORDER.items():
        count = location_counts.get(name, 0)
        if include_empty or count > 0:
            predefined_rooms.append({
                "name": name,
                "display_name": name,
                "sort_order": location_order.get(name, default_order),
                "item_count": count,
                "is_predefined": True,
                "color": _get_room_color(name),
                "is_active": True,
            })

    # Get custom rooms
    custom_rooms = []
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM custom_rooms
            WHERE site_id = ? AND is_active = 1
            ORDER BY sort_order, name
        """, (site_id,)).fetchall()

        for row in rows:
            room = dict(row)
            count = location_counts.get(room["name"], 0)
            if include_empty or count > 0:
                custom_rooms.append({
                    "id": room["id"],
                    "name": room["name"],
                    "display_name": room["display_name"] or room["name"],
                    "sort_order": room["sort_order"],
                    "item_count": count,
                    "is_predefined": False,
                    "color": room.get("color"),
                    "is_active": True,
                })

    # Combine and sort
    all_rooms = predefined_rooms + custom_rooms
    all_rooms.sort(key=lambda r: (r["sort_order"], r["name"]))

    return all_rooms


def get_room(site_id: str, room_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific room by name."""
    # Check if predefined
    if room_name in DEFAULT_LOCATION_ORDER:
        location_counts = get_location_summary(site_id)
        location_order = get_location_order(site_id)
        return {
            "name": room_name,
            "display_name": room_name,
            "sort_order": location_order.get(room_name, DEFAULT_LOCATION_ORDER[room_name]),
            "item_count": location_counts.get(room_name, 0),
            "is_predefined": True,
            "color": _get_room_color(room_name),
            "is_active": True,
        }

    # Check custom rooms
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM custom_rooms
            WHERE site_id = ? AND name = ? AND is_active = 1
        """, (site_id, room_name)).fetchone()

        if row:
            room = dict(row)
            location_counts = get_location_summary(site_id)
            return {
                "id": room["id"],
                "name": room["name"],
                "display_name": room["display_name"] or room["name"],
                "sort_order": room["sort_order"],
                "item_count": location_counts.get(room["name"], 0),
                "is_predefined": False,
                "color": room.get("color"),
                "is_active": True,
            }

    return None


def create_custom_room(
    site_id: str,
    name: str,
    display_name: Optional[str] = None,
    sort_order: int = 50,
    color: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new custom room.

    Raises ValueError if room name conflicts with predefined room.
    """
    # Check for predefined room conflict
    if name.upper() in [k.upper() for k in DEFAULT_LOCATION_ORDER.keys()]:
        raise ValueError(f"Cannot create custom room with predefined name: {name}")

    room_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT INTO custom_rooms
            (id, site_id, name, display_name, sort_order, color, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (room_id, site_id, name, display_name, sort_order, color, now, now))

    return get_room(site_id, name)


def update_custom_room(
    site_id: str,
    name: str,
    display_name: Optional[str] = None,
    sort_order: Optional[int] = None,
    color: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update a custom room's properties."""
    now = datetime.utcnow().isoformat()

    updates = []
    values = []

    if display_name is not None:
        updates.append("display_name = ?")
        values.append(display_name)
    if sort_order is not None:
        updates.append("sort_order = ?")
        values.append(sort_order)
    if color is not None:
        updates.append("color = ?")
        values.append(color)

    if not updates:
        return get_room(site_id, name)

    updates.append("updated_at = ?")
    values.append(now)
    values.extend([site_id, name])

    with get_db() as conn:
        conn.execute(f"""
            UPDATE custom_rooms
            SET {", ".join(updates)}
            WHERE site_id = ? AND name = ? AND is_active = 1
        """, values)

    return get_room(site_id, name)


def delete_custom_room(
    site_id: str,
    name: str,
    move_items_to: str = "UNASSIGNED"
) -> bool:
    """
    Delete a custom room.

    Items in the room are moved to the specified location (default: UNASSIGNED).
    Cannot delete predefined rooms.
    """
    # Check if predefined
    if name.upper() in [k.upper() for k in DEFAULT_LOCATION_ORDER.keys()]:
        raise ValueError(f"Cannot delete predefined room: {name}")

    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        # Move items to new location
        conn.execute("""
            UPDATE item_locations
            SET location = ?, auto_assigned = 0, updated_at = ?
            WHERE site_id = ? AND location = ?
        """, (move_items_to, now, site_id, name))

        # Soft delete the room
        result = conn.execute("""
            UPDATE custom_rooms
            SET is_active = 0, updated_at = ?
            WHERE site_id = ? AND name = ?
        """, (now, site_id, name))

        return result.rowcount > 0


def get_items_by_room(
    site_id: str,
    include_empty_rooms: bool = True
) -> List[Dict[str, Any]]:
    """
    Get all inventory items organized by room.

    Loads items from parsed inventory files and merges with room assignments.
    Items without explicit room assignments go to UNASSIGNED.
    """
    rooms = list_rooms(site_id, include_empty=include_empty_rooms)

    # Get all room assignments for this site
    item_locations = list_item_locations(site_id)
    location_by_sku = {item["sku"]: item for item in item_locations}

    # Load inventory items from the latest parsed file
    inventory_items = _load_inventory_items(site_id)

    # Group items by location
    items_by_location: Dict[str, List[Dict]] = {}
    for item in inventory_items:
        sku = item.get("sku", "")
        # Check if this item has a room assignment
        if sku in location_by_sku:
            location_data = location_by_sku[sku]
            location = location_data.get("location", "UNASSIGNED")
            # Merge location data into item
            item["location"] = location
            item["auto_assigned"] = location_data.get("auto_assigned", True)
            item["sort_order"] = location_data.get("sort_order", 0)
        else:
            location = "UNASSIGNED"
            item["location"] = location
            item["auto_assigned"] = True
            item["sort_order"] = 0

        if location not in items_by_location:
            items_by_location[location] = []
        items_by_location[location].append(item)

    # Add items to rooms and update counts
    result = []
    for room in rooms:
        room_with_items = dict(room)
        room_items = items_by_location.get(room["name"], [])
        room_with_items["items"] = room_items
        room_with_items["item_count"] = len(room_items)
        result.append(room_with_items)

    return result


def _load_inventory_items(site_id: str, limit: int = 2000) -> List[Dict[str, Any]]:
    """Load inventory items from the latest parsed file for a site."""
    files = list_files(status=FileStatus.COMPLETED, site_id=site_id, limit=1)
    if not files:
        return []

    file_record = files[0]
    parsed_data = file_record.get("parsed_data")

    if not parsed_data:
        return []

    try:
        if isinstance(parsed_data, str):
            data = json.loads(parsed_data)
        else:
            data = parsed_data
    except json.JSONDecodeError:
        return []

    rows = data.get("rows", [])
    items = []

    for row in rows[:limit]:
        item = _normalize_row(row)
        if item:
            items.append(item)

    return items


def _normalize_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize a row from parsed data into an inventory item."""
    item = {
        "sku": "",
        "description": "",
        "quantity": 0,
        "unit_price": None,
        "uom": None,
        "vendor": None,
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
        elif "vendor" in key_lower or "supplier" in key_lower:
            item["vendor"] = str(value).strip() if value else None

    if not item["sku"] and item["description"]:
        item["sku"] = item["description"][:20].upper().replace(" ", "_")
    if not item["sku"] and not item["description"]:
        return None
    if not item["description"]:
        item["description"] = item["sku"]

    return item


def move_item_to_room(
    site_id: str,
    sku: str,
    room: str,
    sort_order: int = 0
) -> Dict[str, Any]:
    """
    Move an item to a specific room.

    Creates or updates the item_locations entry.
    """
    # Verify room exists (predefined or custom)
    room_info = get_room(site_id, room)
    if not room_info:
        raise ValueError(f"Room not found: {room}")

    return set_item_location(
        site_id=site_id,
        sku=sku,
        location=room,
        sort_order=sort_order,
        auto_assigned=False  # Manual assignment
    )


def bulk_move_items(
    site_id: str,
    moves: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Bulk move items between rooms.

    Each move should have: sku, room, and optionally sort_order.
    """
    now = datetime.utcnow().isoformat()
    moved = 0
    errors = 0

    with get_db() as conn:
        for move in moves:
            sku = move.get("sku")
            room = move.get("room")
            sort_order = move.get("sort_order", 0)

            if not sku or not room:
                errors += 1
                continue

            # Check if item location exists
            existing = conn.execute(
                "SELECT id FROM item_locations WHERE site_id = ? AND sku = ?",
                (site_id, sku)
            ).fetchone()

            if existing:
                conn.execute("""
                    UPDATE item_locations
                    SET location = ?, sort_order = ?, auto_assigned = 0, updated_at = ?
                    WHERE site_id = ? AND sku = ?
                """, (room, sort_order, now, site_id, sku))
            else:
                item_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO item_locations
                    (id, site_id, sku, location, sort_order, auto_assigned, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                """, (item_id, site_id, sku, room, sort_order, now, now))

            moved += 1

    return {"moved": moved, "errors": errors}


def _get_room_color(room_name: str) -> str:
    """Get default color for predefined rooms."""
    colors = {
        "Freezer": "#60A5FA",           # Blue
        "Walk In Cooler": "#34D399",    # Green
        "Beverage Room": "#A78BFA",     # Purple
        "Dry Storage Food": "#FBBF24",  # Yellow
        "Dry Storage Supplies": "#FB923C",  # Orange
        "Chemical Locker": "#F87171",   # Red
        "NEVER INVENTORY": "#6B7280",   # Gray
        "UNASSIGNED": "#9CA3AF",        # Light gray
    }
    return colors.get(room_name, "#94A3B8")  # Default slate
