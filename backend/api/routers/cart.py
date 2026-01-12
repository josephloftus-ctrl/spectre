"""
Shopping cart API router.
"""
from fastapi import APIRouter, HTTPException, Form

from backend.core.database import (
    add_cart_item, update_cart_item_quantity,
    remove_cart_item, list_cart_items, get_cart_summary, clear_cart,
    bulk_add_cart_items
)
from backend.api.models import CartItemRequest, CartBulkRequest

router = APIRouter(prefix="/api/cart", tags=["Shopping Cart"])


@router.get("/{site_id}")
def get_cart(site_id: str):
    """Get all items in a site's shopping cart."""
    items = list_cart_items(site_id)
    summary = get_cart_summary(site_id)
    return {
        "site_id": site_id,
        "items": items,
        "summary": summary
    }


@router.post("/{site_id}/add")
def add_to_cart(site_id: str, request: CartItemRequest):
    """Add an item to the shopping cart."""
    item = add_cart_item(
        site_id=site_id,
        sku=request.sku,
        description=request.description,
        quantity=request.quantity,
        unit_price=request.unit_price,
        uom=request.uom,
        vendor=request.vendor,
        notes=request.notes,
        source=request.source
    )
    return {"success": True, "item": item}


@router.post("/{site_id}/bulk")
def bulk_add_to_cart(site_id: str, request: CartBulkRequest):
    """Add multiple items to cart at once."""
    count = bulk_add_cart_items(site_id, request.items, request.source)
    return {
        "success": True,
        "added_count": count,
        "summary": get_cart_summary(site_id)
    }


@router.put("/{site_id}/{sku}")
def update_cart_item(
    site_id: str,
    sku: str,
    quantity: float = Form(...)
):
    """Update quantity of a cart item."""
    item = update_cart_item_quantity(site_id, sku, quantity)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    return {"success": True, "item": item}


@router.delete("/{site_id}/{sku}")
def remove_from_cart(site_id: str, sku: str):
    """Remove an item from the cart."""
    removed = remove_cart_item(site_id, sku)
    if not removed:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    return {"success": True, "message": f"Removed {sku} from cart"}


@router.delete("/{site_id}")
def clear_site_cart(site_id: str):
    """Clear all items from a site's cart."""
    count = clear_cart(site_id)
    return {"success": True, "cleared_count": count}
