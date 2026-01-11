"""
Canon Index - Fast lookup structures for purchase matching.

Instead of searching 3000 records for every inventory item, we build
lookup dictionaries once:
- by_sku: O(1) exact SKU match
- by_vendor_price: O(1) fallback lookup by (vendor, price)
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from .models import PurchaseRecord


@dataclass
class CanonIndex:
    """
    Indexed purchase canon for fast lookups.

    Attributes:
        by_sku: Dict mapping SKU -> PurchaseRecord (last write wins for dupes)
        by_vendor_price: Dict mapping (vendor, price) -> list of PurchaseRecords
        record_count: Total number of records indexed
    """
    by_sku: dict[str, PurchaseRecord] = field(default_factory=dict)
    by_vendor_price: dict[tuple[str, Decimal], list[PurchaseRecord]] = field(default_factory=dict)
    record_count: int = 0

    def lookup_sku(self, sku: str) -> Optional[PurchaseRecord]:
        """Look up a record by exact SKU match."""
        return self.by_sku.get(sku)

    def lookup_vendor_price(self, vendor: str, price: Decimal) -> list[PurchaseRecord]:
        """Look up records by vendor and price combination."""
        return self.by_vendor_price.get((vendor, price), [])


def build_index(records: list[PurchaseRecord]) -> CanonIndex:
    """
    Build lookup index from purchase records.

    Args:
        records: List of PurchaseRecord from canon loader

    Returns:
        CanonIndex with SKU and vendor+price lookups
    """
    index = CanonIndex()

    for record in records:
        # SKU index - simple dict, last write wins for duplicates
        index.by_sku[record.sku] = record

        # Vendor+Price index - keyed on (normalized_vendor, price) tuple
        # Value is list because multiple items can have same vendor+price
        key = (record.vendor, record.price)
        if key not in index.by_vendor_price:
            index.by_vendor_price[key] = []
        index.by_vendor_price[key].append(record)

    index.record_count = len(records)
    return index
