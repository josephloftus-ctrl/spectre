"""
Rooms API router - manage room-based inventory categorization.
"""
from fastapi import APIRouter, HTTPException, Query

from backend.core.database import (
    list_rooms,
    get_room,
    create_custom_room,
    update_custom_room,
    delete_custom_room,
    get_items_by_room,
    move_item_to_room,
    bulk_move_items,
)
from backend.api.models import (
    CreateRoomRequest,
    UpdateRoomRequest,
    MoveItemRequest,
    BulkMoveItemsRequest,
)

router = APIRouter(prefix="/api/rooms", tags=["Rooms"])


@router.get("/{site_id}")
def list_site_rooms(
    site_id: str,
    include_empty: bool = Query(True, description="Include rooms with no items")
):
    """
    List all rooms for a site.

    Returns predefined rooms (Freezer, Walk In Cooler, etc.) and custom user-created rooms.
    """
    rooms = list_rooms(site_id, include_empty=include_empty)
    return {"rooms": rooms, "count": len(rooms)}


@router.get("/{site_id}/{room_name}")
def get_site_room(site_id: str, room_name: str):
    """Get details for a specific room."""
    room = get_room(site_id, room_name)
    if not room:
        raise HTTPException(status_code=404, detail=f"Room not found: {room_name}")
    return {"room": room}


@router.post("/{site_id}")
def create_room(site_id: str, request: CreateRoomRequest):
    """
    Create a new custom room.

    Room name cannot conflict with predefined rooms (Freezer, Walk In Cooler, etc.).
    """
    try:
        room = create_custom_room(
            site_id=site_id,
            name=request.name,
            display_name=request.display_name,
            sort_order=request.sort_order,
            color=request.color,
        )
        return {"success": True, "room": room}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(
                status_code=409,
                detail=f"Room '{request.name}' already exists"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{site_id}/{room_name}")
def update_room(site_id: str, room_name: str, request: UpdateRoomRequest):
    """
    Update a custom room.

    Cannot update predefined rooms (Freezer, Walk In Cooler, etc.).
    """
    existing = get_room(site_id, room_name)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Room not found: {room_name}")

    if existing.get("is_predefined"):
        raise HTTPException(
            status_code=400,
            detail="Cannot modify predefined rooms"
        )

    room = update_custom_room(
        site_id=site_id,
        name=room_name,
        display_name=request.display_name,
        sort_order=request.sort_order,
        color=request.color,
    )
    return {"success": True, "room": room}


@router.delete("/{site_id}/{room_name}")
def delete_room(
    site_id: str,
    room_name: str,
    move_items_to: str = Query("UNASSIGNED", description="Room to move items to")
):
    """
    Delete a custom room.

    Items in the room are moved to the specified destination room (default: UNASSIGNED).
    Cannot delete predefined rooms.
    """
    try:
        success = delete_custom_room(site_id, room_name, move_items_to=move_items_to)
        if not success:
            raise HTTPException(status_code=404, detail=f"Room not found: {room_name}")
        return {"success": True, "message": f"Deleted room '{room_name}'"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{site_id}/items/all")
def get_all_items_by_room(
    site_id: str,
    include_empty_rooms: bool = Query(True)
):
    """
    Get all items organized by room.

    Returns each room with its assigned items for drag-and-drop UI.
    """
    rooms = get_items_by_room(site_id, include_empty_rooms=include_empty_rooms)
    return {"rooms": rooms, "count": len(rooms)}


@router.put("/{site_id}/items/{sku}")
def move_item(site_id: str, sku: str, request: MoveItemRequest):
    """
    Move an item to a specific room.

    Creates or updates the item's room assignment.
    """
    try:
        result = move_item_to_room(
            site_id=site_id,
            sku=sku,
            room=request.room,
            sort_order=request.sort_order,
        )
        return {"success": True, "item_location": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{site_id}/items/bulk/move")
def bulk_move(site_id: str, request: BulkMoveItemsRequest):
    """
    Bulk move items between rooms.

    Each move should have: sku, room, and optionally sort_order.
    """
    result = bulk_move_items(site_id, request.moves)
    return {
        "success": True,
        "moved": result["moved"],
        "errors": result["errors"],
    }
