"""
Tests for inventory adapters (Chunk 3).

Run with: pytest nebula/purchase_match/tests/test_adapters.py -v
"""

import pytest
from decimal import Decimal
from pathlib import Path

from nebula.purchase_match.adapters import (
    MockInventoryAdapter,
    InMemoryInventoryAdapter,
)
from nebula.purchase_match.models import InventoryRecord


# Paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_INVENTORY_CSV = FIXTURES_DIR / "test_inventory.csv"


class TestMockInventoryAdapter:
    """Test CSV-based mock adapter."""

    @pytest.fixture
    def adapter(self):
        return MockInventoryAdapter(TEST_INVENTORY_CSV)

    def test_load_csv(self, adapter):
        # Should have records from CSV
        units = adapter.get_all_units()
        assert "PSEG_HQ" in units
        assert "LOCKHEED" in units

    def test_get_inventory_for_unit(self, adapter):
        pseg_items = adapter.get_inventory_for_unit("PSEG_HQ")
        assert len(pseg_items) > 0

        # All items should be for PSEG_HQ
        for item in pseg_items:
            assert item.unit == "PSEG_HQ"

    def test_get_inventory_lockheed(self, adapter):
        lockheed_items = adapter.get_inventory_for_unit("LOCKHEED")
        assert len(lockheed_items) == 2  # Per CSV fixture

    def test_get_inventory_unknown_unit(self, adapter):
        items = adapter.get_inventory_for_unit("UNKNOWN")
        assert items == []

    def test_record_fields(self, adapter):
        items = adapter.get_inventory_for_unit("PSEG_HQ")

        # Find tomato record
        tomato = next((i for i in items if i.sku == "12345"), None)
        assert tomato is not None
        assert tomato.description == "TOMATO DICED #10"
        assert tomato.quantity == Decimal("5")
        assert tomato.vendor == "sysco"
        assert tomato.price == Decimal("47.82")

    def test_optional_fields(self, adapter):
        items = adapter.get_inventory_for_unit("PSEG_HQ")

        # Mystery item has no vendor
        mystery = next((i for i in items if i.sku == "99999"), None)
        assert mystery is not None
        assert mystery.vendor is None

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            MockInventoryAdapter("nonexistent.csv")


class TestInMemoryAdapter:
    """Test in-memory adapter for unit tests."""

    def test_empty_adapter(self):
        adapter = InMemoryInventoryAdapter()
        assert adapter.get_all_units() == []
        assert adapter.get_inventory_for_unit("ANY") == []

    def test_add_record(self):
        adapter = InMemoryInventoryAdapter()
        record = InventoryRecord(
            sku="123",
            unit="TEST",
            description="Test Item",
            quantity=Decimal("1"),
        )
        adapter.add_record(record)

        items = adapter.get_inventory_for_unit("TEST")
        assert len(items) == 1
        assert items[0].sku == "123"

    def test_add_records(self):
        adapter = InMemoryInventoryAdapter()
        records = [
            InventoryRecord(sku="A", unit="U1", description="A", quantity=Decimal("1")),
            InventoryRecord(sku="B", unit="U1", description="B", quantity=Decimal("2")),
            InventoryRecord(sku="C", unit="U2", description="C", quantity=Decimal("3")),
        ]
        adapter.add_records(records)

        assert len(adapter.get_inventory_for_unit("U1")) == 2
        assert len(adapter.get_inventory_for_unit("U2")) == 1
        assert sorted(adapter.get_all_units()) == ["U1", "U2"]

    def test_init_with_records(self):
        records = [
            InventoryRecord(sku="X", unit="INIT", description="X", quantity=Decimal("1")),
        ]
        adapter = InMemoryInventoryAdapter(records)

        items = adapter.get_inventory_for_unit("INIT")
        assert len(items) == 1

    def test_clear(self):
        adapter = InMemoryInventoryAdapter()
        adapter.add_record(
            InventoryRecord(sku="X", unit="U", description="X", quantity=Decimal("1"))
        )
        assert len(adapter.get_all_units()) == 1

        adapter.clear()
        assert len(adapter.get_all_units()) == 0


class TestAdapterInterfaceCompliance:
    """Verify both adapters implement the interface correctly."""

    @pytest.fixture(params=["mock", "inmemory"])
    def adapter(self, request):
        if request.param == "mock":
            return MockInventoryAdapter(TEST_INVENTORY_CSV)
        else:
            records = [
                InventoryRecord(
                    sku="TEST1", unit="PSEG_HQ",
                    description="Test", quantity=Decimal("1")
                ),
            ]
            return InMemoryInventoryAdapter(records)

    def test_has_get_inventory_for_unit(self, adapter):
        assert hasattr(adapter, "get_inventory_for_unit")
        result = adapter.get_inventory_for_unit("PSEG_HQ")
        assert isinstance(result, list)

    def test_has_get_all_units(self, adapter):
        assert hasattr(adapter, "get_all_units")
        result = adapter.get_all_units()
        assert isinstance(result, list)

    def test_returns_inventory_records(self, adapter):
        items = adapter.get_inventory_for_unit("PSEG_HQ")
        for item in items:
            assert isinstance(item, InventoryRecord)
