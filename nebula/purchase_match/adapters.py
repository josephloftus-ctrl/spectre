"""
Inventory Adapters - Bridge to inventory data sources.

The adapter pattern lets us swap implementations (mock for testing,
real for production) without changing matcher logic.
"""

import csv
import json
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import InventoryRecord


class InventoryAdapter(ABC):
    """
    Abstract interface for inventory data access.

    Implementations fetch inventory items for a given unit.
    The matcher doesn't know or care where the data actually lives.
    """

    @abstractmethod
    def get_inventory_for_unit(self, unit: str) -> list[InventoryRecord]:
        """
        Fetch inventory records for a unit.

        Args:
            unit: Unit identifier (e.g., "PSEG_HQ")

        Returns:
            List of InventoryRecord for that unit
        """
        pass

    @abstractmethod
    def get_all_units(self) -> list[str]:
        """Get list of all available unit identifiers."""
        pass


class MockInventoryAdapter(InventoryAdapter):
    """
    Test implementation that loads inventory from CSV or JSON file.

    CSV format expected:
        sku,unit,description,quantity,vendor,price
        12345,PSEG_HQ,TOMATO DICED,5,sysco,47.82

    JSON format expected:
        [{"sku": "12345", "unit": "PSEG_HQ", ...}, ...]
    """

    def __init__(self, data_path: str | Path):
        """
        Initialize mock adapter with data file.

        Args:
            data_path: Path to CSV or JSON file with inventory data
        """
        self._data_path = Path(data_path)
        self._records: list[InventoryRecord] = []
        self._units: set[str] = set()
        self._load_data()

    def _load_data(self):
        """Load inventory records from file."""
        if not self._data_path.exists():
            raise FileNotFoundError(f"Inventory data file not found: {self._data_path}")

        suffix = self._data_path.suffix.lower()
        if suffix == ".csv":
            self._load_csv()
        elif suffix == ".json":
            self._load_json()
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def _load_csv(self):
        """Load from CSV file."""
        with open(self._data_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                record = self._parse_row(row)
                if record:
                    self._records.append(record)
                    self._units.add(record.unit)

    def _load_json(self):
        """Load from JSON file."""
        with open(self._data_path, "r") as f:
            data = json.load(f)

        for row in data:
            record = self._parse_row(row)
            if record:
                self._records.append(record)
                self._units.add(record.unit)

    def _parse_row(self, row: dict) -> InventoryRecord | None:
        """Parse a row dict into InventoryRecord."""
        sku = row.get("sku")
        unit = row.get("unit")
        description = row.get("description", "")

        if not sku or not unit:
            return None

        # Parse quantity
        quantity_val = row.get("quantity", 0)
        try:
            quantity = Decimal(str(quantity_val))
        except InvalidOperation:
            quantity = Decimal("0")

        # Parse optional price
        price_val = row.get("price")
        price = None
        if price_val is not None and price_val != "":
            try:
                price = Decimal(str(price_val)).quantize(Decimal("0.01"))
            except InvalidOperation:
                pass

        # Get optional vendor
        vendor = row.get("vendor") or None

        return InventoryRecord(
            sku=str(sku).strip(),
            unit=str(unit).strip(),
            description=str(description).strip(),
            quantity=quantity,
            vendor=vendor,
            price=price,
        )

    def get_inventory_for_unit(self, unit: str) -> list[InventoryRecord]:
        """Get all inventory records for a specific unit."""
        return [r for r in self._records if r.unit == unit]

    def get_all_units(self) -> list[str]:
        """Get list of all units in the mock data."""
        return sorted(self._units)


class InMemoryInventoryAdapter(InventoryAdapter):
    """
    In-memory adapter for programmatic test setup.

    Useful for unit tests where you want to control exact records.
    """

    def __init__(self, records: list[InventoryRecord] | None = None):
        self._records = records or []
        self._units = {r.unit for r in self._records}

    def add_record(self, record: InventoryRecord):
        """Add a single record."""
        self._records.append(record)
        self._units.add(record.unit)

    def add_records(self, records: list[InventoryRecord]):
        """Add multiple records."""
        for record in records:
            self.add_record(record)

    def clear(self):
        """Remove all records."""
        self._records = []
        self._units = set()

    def get_inventory_for_unit(self, unit: str) -> list[InventoryRecord]:
        """Get all inventory records for a specific unit."""
        return [r for r in self._records if r.unit == unit]

    def get_all_units(self) -> list[str]:
        """Get list of all units."""
        return sorted(self._units)
