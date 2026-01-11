"""
Data models for Purchase Match Diagnostic.

All structured data uses dataclasses for type hints, __eq__, and __repr__.
Money values use Decimal for precision.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional
from datetime import date


class MatchFlag(Enum):
    """
    Result flags for inventory matching.

    Combines 3 data sources:
    - IPS: Invoice Purchasing Summaries (what was bought)
    - MOG: Master Order Guides (what's available to order)
    - Inventory: What's being counted
    """
    CLEAN = "CLEAN"              # SKU found in IPS - confirmed purchase
    ORDERABLE = "ORDERABLE"      # SKU not in IPS but IS in MOG - valid, just not ordered
    LIKELY_TYPO = "LIKELY_TYPO"  # SKU not in IPS/MOG, but similar description found
    UNKNOWN = "UNKNOWN"          # SKU not in IPS/MOG, no similar items - needs investigation
    IGNORED = "IGNORED"          # On site ignore list (house-made, transfer, etc.)

    # Legacy aliases for backwards compatibility
    SKU_MISMATCH = "LIKELY_TYPO"
    ORPHAN = "UNKNOWN"


@dataclass
class PurchaseRecord:
    """
    A single item from the purchase canon (IPS export).

    This represents what was actually purchased according to OrderMaestro.
    """
    sku: str                    # Item Number from IPS
    vendor: str                 # Normalized vendor key (e.g., "sysco")
    vendor_raw: str             # Original distributor name from file
    price: Decimal              # Invoiced Item Price
    description: str            # Item description for display
    brand: Optional[str] = None
    uom: Optional[str] = None   # Unit of measure
    pack: Optional[str] = None
    purchase_date: Optional[date] = None  # For tie-breaking multi-price matches


@dataclass
class InventoryRecord:
    """
    A single item from inventory (via adapter).

    This represents what's currently counted/valued in the ops dashboard.
    """
    sku: str
    unit: str                   # Which location (e.g., "PSEG_HQ")
    description: str
    quantity: Decimal
    vendor: Optional[str] = None  # If known from inventory system
    price: Optional[Decimal] = None  # Current valuation price


@dataclass
class MOGMatch:
    """Reference to a MOG catalog item."""
    sku: str
    description: str
    vendor: str
    price: Optional[Decimal] = None
    similarity: float = 0.0  # 0-1 score for description match


@dataclass
class MatchResult:
    """
    Output of the matching algorithm for a single inventory item.

    Contains the original item, its flag, and context from all data sources.
    """
    inventory_item: InventoryRecord
    flag: MatchFlag
    reason: str = ""  # Human-readable explanation

    # For CLEAN items - the IPS purchase record
    ips_match: Optional[PurchaseRecord] = None

    # For ORDERABLE items - the MOG catalog entry
    mog_match: Optional[MOGMatch] = None

    # For LIKELY_TYPO items - suggested correction from MOG
    suggested_sku: Optional[MOGMatch] = None

    # Legacy alias
    @property
    def suggested_match(self) -> Optional[PurchaseRecord]:
        """Backwards compatibility."""
        return self.ips_match
