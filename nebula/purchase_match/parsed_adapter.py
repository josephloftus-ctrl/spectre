"""
Parsed File Inventory Adapter - Reads inventory from Spectre's parsed JSON files.

This adapter connects the Purchase Match Diagnostic to the existing
Spectre data pipeline. It reads the parsed inventory valuations from
the data/processed/{site}/ directories.
"""

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from .adapters import InventoryAdapter
from .models import InventoryRecord
from .config import normalize_vendor, Config


class ParsedFileInventoryAdapter(InventoryAdapter):
    """
    Adapter that reads inventory from Spectre's parsed JSON files.

    Expected file structure:
        data/processed/{site_id}/{date}/{uuid}_parsed.json

    Each parsed.json contains:
        {
            "headers": [...],
            "rows": [
                {
                    "Dist #": "SKU",
                    "Item Description": "...",
                    "Quantity": "5.0",
                    "UOM": "CS",
                    "Unit Price": "47.82",
                    "Total Price": "...",
                    "Distributor": "Sysco Corporation",
                    ...
                }
            ]
        }
    """

    # Field mappings from parsed JSON to InventoryRecord
    FIELD_MAP = {
        "sku": ["Dist #", "Item Number", "Item_Number", "SKU"],
        "description": ["Item Description", "Description", "Item_Description"],
        "quantity": ["Quantity", "Qty"],
        "price": ["Unit Price", "Price", "Unit_Price"],
        "vendor": ["Distributor", "Vendor"],
        "uom": ["UOM", "Unit of Measure"],
    }

    def __init__(self, data_dir: str | Path, config: Optional[Config] = None):
        """
        Initialize adapter with data directory.

        Args:
            data_dir: Path to data/processed directory
            config: Optional config for vendor normalization
        """
        self._data_dir = Path(data_dir)
        self._config = config
        self._units: dict[str, list[InventoryRecord]] = {}
        self._load_all_sites()

    def _load_all_sites(self):
        """Scan processed directory and load all sites."""
        if not self._data_dir.exists():
            return

        for site_dir in self._data_dir.iterdir():
            if not site_dir.is_dir():
                continue
            site_id = site_dir.name
            # Skip unknown - these are files without proper site detection
            if site_id.lower() == "unknown":
                continue
            self._units[site_id] = self._load_site(site_id)

    def _load_site(self, site_id: str) -> list[InventoryRecord]:
        """Load inventory records for a single site."""
        site_dir = self._data_dir / site_id
        records = []

        # Find all parsed.json files (get most recent by date folder)
        date_dirs = sorted(site_dir.iterdir(), reverse=True)
        for date_dir in date_dirs:
            if not date_dir.is_dir():
                continue

            # Find parsed JSON files
            for json_file in date_dir.glob("*_parsed.json"):
                site_records = self._parse_file(json_file, site_id)
                records.extend(site_records)

            # Only use most recent date
            if records:
                break

        return records

    def _parse_file(self, json_path: Path, site_id: str) -> list[InventoryRecord]:
        """Parse a single JSON file into InventoryRecords."""
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

        rows = data.get("rows", [])
        records = []

        for row in rows:
            record = self._parse_row(row, site_id)
            if record:
                records.append(record)

        return records

    def _get_field(self, row: dict, field_type: str) -> Optional[str]:
        """Get a field value trying multiple possible column names."""
        for field_name in self.FIELD_MAP.get(field_type, []):
            if field_name in row and row[field_name]:
                return str(row[field_name]).strip()
        return None

    def _parse_row(self, row: dict, site_id: str) -> Optional[InventoryRecord]:
        """Parse a single row into an InventoryRecord."""
        sku = self._get_field(row, "sku")
        if not sku:
            return None

        description = self._get_field(row, "description") or ""

        # Parse quantity
        qty_str = self._get_field(row, "quantity")
        try:
            quantity = Decimal(qty_str) if qty_str else Decimal("0")
        except InvalidOperation:
            quantity = Decimal("0")

        # Parse price
        price_str = self._get_field(row, "price")
        price = None
        if price_str:
            try:
                price = Decimal(price_str).quantize(Decimal("0.01"))
            except InvalidOperation:
                pass

        # Get vendor (normalize if config available)
        vendor_raw = self._get_field(row, "vendor")
        vendor = None
        if vendor_raw:
            if self._config:
                vendor = normalize_vendor(vendor_raw, self._config)
            else:
                vendor = vendor_raw.lower().replace(" ", "_")

        return InventoryRecord(
            sku=sku,
            unit=self._normalize_site_id(site_id),
            description=description,
            quantity=quantity,
            vendor=vendor,
            price=price,
        )

    def _normalize_site_id(self, site_id: str) -> str:
        """Normalize site_id to match config format (e.g., pseg_nhq -> PSEG_HQ)."""
        # Map from filesystem names to config names
        site_map = {
            "pseg_nhq": "PSEG_HQ",
            "pseg_hope_creek": "PSEG_HOPE_CREEK",
            "pseg_salem": "PSEG_SALEM",
            "lockhead_martin_bldg_100": "LOCKHEED",
            "lockheed_martin_bldg_100": "LOCKHEED",
            "lockheed_martin_bldg_d": "LOCKHEED_BLDG_D",
        }
        return site_map.get(site_id.lower(), site_id.upper())

    def get_inventory_for_unit(self, unit: str) -> list[InventoryRecord]:
        """Get inventory records for a unit."""
        # Try exact match first
        if unit in self._units:
            return self._units[unit]

        # Try normalized lookup
        for site_id, records in self._units.items():
            if self._normalize_site_id(site_id) == unit:
                return records

        return []

    def get_all_units(self) -> list[str]:
        """Get list of all units with inventory data."""
        return [self._normalize_site_id(s) for s in self._units.keys()]

    def reload(self):
        """Reload all inventory data from disk."""
        self._units.clear()
        self._load_all_sites()
