"""
Tests for core matcher - simplified version.

The matcher now has simple logic:
- SKU in IPS = CLEAN
- SKU not in IPS = ORPHAN (FLAG)

Run with: pytest nebula/purchase_match/tests/test_matcher.py -v
"""

import pytest
from decimal import Decimal
from pathlib import Path

from nebula.purchase_match.models import (
    PurchaseRecord,
    InventoryRecord,
    MatchResult,
    MatchFlag,
)
from nebula.purchase_match.index import build_index
from nebula.purchase_match.config import load_config
from nebula.purchase_match.matcher import (
    match_inventory,
    group_results_by_unit,
    sort_results_for_report,
    filter_actionable,
    summarize_results,
)


CONFIG_PATH = Path(__file__).parent.parent / "unit_vendor_config.json"


@pytest.fixture
def config():
    return load_config(CONFIG_PATH)


@pytest.fixture
def sample_canon():
    """Sample purchase records for testing."""
    return [
        PurchaseRecord(
            sku="12345", vendor="sysco", vendor_raw="Sysco Corporation",
            price=Decimal("47.82"), description="TOMATO DICED #10"
        ),
        PurchaseRecord(
            sku="67890", vendor="sysco", vendor_raw="Sysco Corporation",
            price=Decimal("4.29"), description="MILK 2% GAL"
        ),
        PurchaseRecord(
            sku="11111", vendor="sysco", vendor_raw="Sysco Corporation",
            price=Decimal("89.50"), description="CHICKEN BREAST B/S"
        ),
        PurchaseRecord(
            sku="22222", vendor="gordon_food_service", vendor_raw="Gordon Food Service US",
            price=Decimal("65.00"), description="BEEF PATTY 4OZ"
        ),
        PurchaseRecord(
            sku="33333", vendor="vistar", vendor_raw="Vistar Corporation",
            price=Decimal("28.99"), description="PEPSI 20OZ"
        ),
    ]


@pytest.fixture
def index(sample_canon):
    return build_index(sample_canon)


class TestMatchInventoryClean:
    """Test CLEAN flag - SKU found in IPS."""

    def test_exact_sku_match(self, index, config):
        inventory = [
            InventoryRecord(
                sku="12345", unit="PSEG_HQ",
                description="TOMATO", quantity=Decimal("5")
            ),
        ]
        results = match_inventory(inventory, index, config)

        assert len(results) == 1
        assert results[0].flag == MatchFlag.CLEAN
        assert "found in purchase history" in results[0].reason

    def test_multiple_clean_matches(self, index, config):
        inventory = [
            InventoryRecord(sku="12345", unit="PSEG_HQ", description="A", quantity=Decimal("1")),
            InventoryRecord(sku="67890", unit="PSEG_HQ", description="B", quantity=Decimal("1")),
        ]
        results = match_inventory(inventory, index, config)

        assert all(r.flag == MatchFlag.CLEAN for r in results)


class TestMatchInventoryOrphan:
    """Test ORPHAN flag - SKU not found in IPS."""

    def test_sku_not_in_canon(self, index, config):
        inventory = [
            InventoryRecord(
                sku="NOPE", unit="PSEG_HQ",
                description="MYSTERY", quantity=Decimal("1"),
                price=Decimal("47.82")  # Same price but wrong SKU
            ),
        ]
        results = match_inventory(inventory, index, config)

        assert results[0].flag == MatchFlag.ORPHAN
        assert "not found" in results[0].reason

    def test_unknown_sku_any_unit(self, index, config):
        """SKU not in IPS should be ORPHAN regardless of unit."""
        inventory = [
            InventoryRecord(
                sku="FAKE123", unit="LOCKHEED",
                description="UNKNOWN ITEM", quantity=Decimal("1"),
            ),
        ]
        results = match_inventory(inventory, index, config)

        assert results[0].flag == MatchFlag.ORPHAN

    def test_sku_not_found_no_price(self, index, config):
        inventory = [
            InventoryRecord(
                sku="NOPE", unit="PSEG_HQ",
                description="NO PRICE", quantity=Decimal("1"),
                price=None
            ),
        ]
        results = match_inventory(inventory, index, config)

        assert results[0].flag == MatchFlag.ORPHAN
        assert "not found" in results[0].reason


class TestHelperFunctions:
    """Test helper functions for result processing."""

    def test_group_results_by_unit(self, index, config):
        inventory = [
            InventoryRecord(sku="12345", unit="PSEG_HQ", description="A", quantity=Decimal("1")),
            InventoryRecord(sku="22222", unit="LOCKHEED", description="B", quantity=Decimal("1")),
            InventoryRecord(sku="67890", unit="PSEG_HQ", description="C", quantity=Decimal("1")),
        ]
        results = match_inventory(inventory, index, config)
        grouped = group_results_by_unit(results)

        assert "PSEG_HQ" in grouped
        assert "LOCKHEED" in grouped
        assert len(grouped["PSEG_HQ"]) == 2
        assert len(grouped["LOCKHEED"]) == 1

    def test_sort_results_for_report(self, index, config):
        inventory = [
            InventoryRecord(sku="12345", unit="PSEG_HQ", description="CLEAN", quantity=Decimal("1")),
            InventoryRecord(sku="NOPE", unit="PSEG_HQ", description="ORPHAN", quantity=Decimal("1")),
        ]
        results = match_inventory(inventory, index, config)
        sorted_results = sort_results_for_report(results)

        # ORPHAN first, then CLEAN (sorted by actionability)
        assert sorted_results[0].flag == MatchFlag.ORPHAN
        assert sorted_results[1].flag == MatchFlag.CLEAN

    def test_filter_actionable(self, index, config):
        inventory = [
            InventoryRecord(sku="12345", unit="PSEG_HQ", description="CLEAN", quantity=Decimal("1")),
            InventoryRecord(sku="NOPE", unit="PSEG_HQ", description="ORPHAN", quantity=Decimal("1")),
        ]
        results = match_inventory(inventory, index, config)
        actionable = filter_actionable(results)

        assert len(actionable) == 1
        assert actionable[0].flag == MatchFlag.ORPHAN

    def test_summarize_results(self, index, config):
        inventory = [
            InventoryRecord(sku="12345", unit="PSEG_HQ", description="CLEAN", quantity=Decimal("1")),
            InventoryRecord(sku="67890", unit="PSEG_HQ", description="CLEAN2", quantity=Decimal("1")),
            InventoryRecord(sku="FAKE", unit="PSEG_HQ", description="ORPHAN1", quantity=Decimal("1")),
            InventoryRecord(sku="NOPE", unit="PSEG_HQ", description="ORPHAN2", quantity=Decimal("1")),
        ]
        results = match_inventory(inventory, index, config)
        summary = summarize_results(results)

        assert summary["total"] == 4
        assert summary["clean"] == 2
        assert summary["sku_mismatch"] == 0  # No more SKU_MISMATCH
        assert summary["orphan"] == 2
        assert summary["actionable"] == 2
