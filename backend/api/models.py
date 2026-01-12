"""
Pydantic request/response models for the API.
"""
from pydantic import BaseModel
from typing import Any, Dict, List, Optional


# ============== Ignore List ==============

class IgnoreItemRequest(BaseModel):
    sku: str
    reason: Optional[str] = None
    notes: Optional[str] = None


# ============== Shopping Cart ==============

class CartItemRequest(BaseModel):
    sku: str
    description: str
    quantity: float = 1
    unit_price: Optional[float] = None
    uom: Optional[str] = None
    vendor: Optional[str] = None
    notes: Optional[str] = None
    source: str = "manual"


class CartBulkRequest(BaseModel):
    items: List[Dict[str, Any]]
    source: str = "bulk"


# ============== Off-Catalog Items ==============

class OffCatalogItemRequest(BaseModel):
    """Request model for creating/updating off-catalog items."""
    dist_num: str
    cust_num: Optional[str] = None  # If not provided, auto-generate
    description: Optional[str] = ""
    pack: Optional[str] = ""
    uom: Optional[str] = ""
    break_uom: Optional[str] = None
    unit_price: Optional[float] = None
    break_price: Optional[float] = None
    distributor: Optional[str] = ""
    distribution_center: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    manufacturer_num: Optional[str] = None
    gtin: Optional[str] = None
    upc: Optional[str] = None
    catch_weight: Optional[int] = 0
    average_weight: Optional[float] = None
    units_per_case: Optional[int] = None
    location: Optional[str] = None
    area: Optional[str] = None
    place: Optional[str] = None
    notes: Optional[str] = None


# ============== Count Sessions ==============

class CountItemRequest(BaseModel):
    sku: str
    description: str
    counted_qty: float
    expected_qty: Optional[float] = None
    unit_price: Optional[float] = None
    uom: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class BulkCountItemsRequest(BaseModel):
    items: List[Dict[str, Any]]
