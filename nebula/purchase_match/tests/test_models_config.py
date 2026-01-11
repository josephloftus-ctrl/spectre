"""
Tests for models and config (Chunk 1).

Run with: pytest nebula/purchase_match/tests/test_models_config.py -v
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
from nebula.purchase_match.config import (
    load_config,
    get_approved_vendors,
    normalize_vendor,
)


# Path to test config
CONFIG_PATH = Path(__file__).parent.parent / "unit_vendor_config.json"


class TestMatchFlag:
    """Test MatchFlag enum."""

    def test_flag_values(self):
        assert MatchFlag.CLEAN.value == "CLEAN"
        assert MatchFlag.LIKELY_TYPO.value == "LIKELY_TYPO"
        assert MatchFlag.UNKNOWN.value == "UNKNOWN"
        assert MatchFlag.ORDERABLE.value == "ORDERABLE"
        # Legacy aliases point to new values
        assert MatchFlag.SKU_MISMATCH.value == "LIKELY_TYPO"
        assert MatchFlag.ORPHAN.value == "UNKNOWN"

    def test_flag_comparison(self):
        assert MatchFlag.CLEAN == MatchFlag.CLEAN
        assert MatchFlag.CLEAN != MatchFlag.ORPHAN


class TestPurchaseRecord:
    """Test PurchaseRecord dataclass."""

    def test_creation(self):
        record = PurchaseRecord(
            sku="12345",
            vendor="sysco",
            vendor_raw="Sysco Corporation",
            price=Decimal("47.82"),
            description="TOMATO DICED #10",
        )
        assert record.sku == "12345"
        assert record.vendor == "sysco"
        assert record.price == Decimal("47.82")

    def test_optional_fields(self):
        record = PurchaseRecord(
            sku="12345",
            vendor="sysco",
            vendor_raw="Sysco Corporation",
            price=Decimal("47.82"),
            description="TOMATO DICED #10",
            brand="Del Monte",
            uom="CS",
            pack="6/#10",
        )
        assert record.brand == "Del Monte"
        assert record.uom == "CS"
        assert record.pack == "6/#10"

    def test_equality(self):
        r1 = PurchaseRecord(
            sku="12345", vendor="sysco", vendor_raw="Sysco",
            price=Decimal("47.82"), description="Test"
        )
        r2 = PurchaseRecord(
            sku="12345", vendor="sysco", vendor_raw="Sysco",
            price=Decimal("47.82"), description="Test"
        )
        assert r1 == r2


class TestInventoryRecord:
    """Test InventoryRecord dataclass."""

    def test_creation(self):
        record = InventoryRecord(
            sku="99999",
            unit="PSEG_HQ",
            description="MYSTERY ITEM",
            quantity=Decimal("5"),
        )
        assert record.sku == "99999"
        assert record.unit == "PSEG_HQ"
        assert record.quantity == Decimal("5")
        assert record.vendor is None
        assert record.price is None

    def test_with_optional_fields(self):
        record = InventoryRecord(
            sku="99999",
            unit="PSEG_HQ",
            description="MYSTERY ITEM",
            quantity=Decimal("5"),
            vendor="sysco",
            price=Decimal("47.82"),
        )
        assert record.vendor == "sysco"
        assert record.price == Decimal("47.82")


class TestMatchResult:
    """Test MatchResult dataclass."""

    def test_clean_result(self):
        inv = InventoryRecord(
            sku="12345", unit="PSEG_HQ",
            description="Test", quantity=Decimal("1")
        )
        result = MatchResult(
            inventory_item=inv,
            flag=MatchFlag.CLEAN,
            reason="SKU found in purchase history"
        )
        assert result.flag == MatchFlag.CLEAN
        assert result.suggested_match is None

    def test_mismatch_result(self):
        inv = InventoryRecord(
            sku="99999", unit="PSEG_HQ",
            description="Test", quantity=Decimal("1"),
            price=Decimal("47.82")
        )
        purchase = PurchaseRecord(
            sku="12345", vendor="sysco", vendor_raw="Sysco",
            price=Decimal("47.82"), description="TOMATO DICED"
        )
        result = MatchResult(
            inventory_item=inv,
            flag=MatchFlag.LIKELY_TYPO,
            ips_match=purchase,
            reason="Price $47.82 matches SKU 12345"
        )
        assert result.flag == MatchFlag.LIKELY_TYPO
        assert result.suggested_match.sku == "12345"  # suggested_match is property alias for ips_match


class TestConfig:
    """Test config loading and functions."""

    @pytest.fixture
    def config(self):
        return load_config(CONFIG_PATH)

    def test_load_config(self, config):
        assert "PSEG_HQ" in config.units
        assert "LOCKHEED" in config.units
        assert "sysco" in config.vendor_aliases

    def test_unit_vendors(self, config):
        pseg = config.units["PSEG_HQ"]
        assert pseg.name == "PSEG Headquarters"
        assert "sysco" in pseg.vendors
        assert "vistar" in pseg.vendors

    def test_settings(self, config):
        assert config.settings.price_match_tolerance_percent == Decimal("0")
        assert config.settings.default_lookback_months == 3

    def test_get_approved_vendors(self, config):
        vendors = get_approved_vendors("PSEG_HQ", config)
        assert "sysco" in vendors
        assert "vistar" in vendors
        # Gordon should NOT be approved for PSEG
        assert "gordon_food_service" not in vendors

    def test_get_approved_vendors_lockheed(self, config):
        vendors = get_approved_vendors("LOCKHEED", config)
        assert "gordon_food_service" in vendors
        # Sysco should NOT be approved for Lockheed
        assert "sysco" not in vendors

    def test_get_approved_vendors_unknown_unit(self, config):
        vendors = get_approved_vendors("UNKNOWN_UNIT", config)
        assert vendors == []

    def test_normalize_vendor_exact(self, config):
        assert normalize_vendor("Sysco Corporation", config) == "sysco"
        assert normalize_vendor("Gordon Food Service US", config) == "gordon_food_service"

    def test_normalize_vendor_case_insensitive(self, config):
        assert normalize_vendor("SYSCO", config) == "sysco"
        assert normalize_vendor("sysco corporation", config) == "sysco"

    def test_normalize_vendor_aliases(self, config):
        assert normalize_vendor("GFS", config) == "gordon_food_service"
        assert normalize_vendor("Coke", config) == "coca_cola"
        assert normalize_vendor("PepsiCo", config) == "pepsi"

    def test_normalize_vendor_unknown(self, config):
        assert normalize_vendor("Unknown Vendor Inc", config) is None
        assert normalize_vendor("", config) is None


class TestImports:
    """Test that module imports work correctly."""

    def test_import_from_module(self):
        from nebula.purchase_match import (
            PurchaseRecord,
            InventoryRecord,
            MatchResult,
            MatchFlag,
            load_config,
            get_approved_vendors,
            normalize_vendor,
        )
        assert MatchFlag.CLEAN.value == "CLEAN"
