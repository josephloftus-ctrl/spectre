"""
Tests for canon loader and index (Chunk 2).

Run with: pytest nebula/purchase_match/tests/test_canon_index.py -v
"""

import pytest
from decimal import Decimal
from pathlib import Path

from nebula.purchase_match.canon_loader import load_canon
from nebula.purchase_match.index import build_index, CanonIndex
from nebula.purchase_match.config import load_config


# Paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
CONFIG_PATH = Path(__file__).parent.parent / "unit_vendor_config.json"
SAMPLE_IPS = FIXTURES_DIR / "sample_ips.xlsx"


class TestCanonLoader:
    """Test IPS file loading."""

    @pytest.fixture
    def config(self):
        return load_config(CONFIG_PATH)

    def test_load_single_file(self, config):
        records = load_canon([SAMPLE_IPS], config)
        assert len(records) == 7  # 7 rows of data

    def test_record_fields(self, config):
        records = load_canon([SAMPLE_IPS], config)

        # Find the tomato record
        tomato = next(r for r in records if r.sku == "117377")
        assert tomato.vendor == "sysco"
        assert tomato.vendor_raw == "Sysco Corporation"
        assert tomato.price == Decimal("47.82")
        assert tomato.description == "TOMATO DICED #10"
        assert tomato.brand == "Del Monte"
        assert tomato.uom == "CS"

    def test_vendor_normalization(self, config):
        records = load_canon([SAMPLE_IPS], config)

        vendors = {r.vendor for r in records}
        assert "sysco" in vendors
        assert "vistar" in vendors
        assert "gordon_food_service" in vendors
        assert "farmer_brothers" in vendors

        # Should NOT have raw vendor names
        assert "Sysco Corporation" not in vendors

    def test_price_as_decimal(self, config):
        records = load_canon([SAMPLE_IPS], config)

        for record in records:
            assert isinstance(record.price, Decimal)
            # Check precision
            assert record.price == record.price.quantize(Decimal("0.01"))

    def test_file_not_found(self, config):
        with pytest.raises(FileNotFoundError):
            load_canon(["nonexistent.xlsx"], config)


class TestCanonIndex:
    """Test index building and lookups."""

    @pytest.fixture
    def config(self):
        return load_config(CONFIG_PATH)

    @pytest.fixture
    def index(self, config):
        records = load_canon([SAMPLE_IPS], config)
        return build_index(records)

    def test_build_index(self, index):
        assert index.record_count == 7
        assert len(index.by_sku) == 7

    def test_sku_lookup(self, index):
        # Exact SKU lookup
        record = index.lookup_sku("117377")
        assert record is not None
        assert record.description == "TOMATO DICED #10"
        assert record.price == Decimal("47.82")

    def test_sku_lookup_missing(self, index):
        record = index.lookup_sku("NONEXISTENT")
        assert record is None

    def test_vendor_price_lookup(self, index):
        # Look up by sysco + $47.82
        matches = index.lookup_vendor_price("sysco", Decimal("47.82"))
        assert len(matches) == 1
        assert matches[0].sku == "117377"

    def test_vendor_price_lookup_empty(self, index):
        # No match for this combination
        matches = index.lookup_vendor_price("sysco", Decimal("9999.99"))
        assert matches == []

    def test_vendor_price_multiple_matches(self, config):
        """Test when multiple items have same vendor+price."""
        # Create records with duplicate vendor+price
        from nebula.purchase_match.models import PurchaseRecord

        records = [
            PurchaseRecord(
                sku="AAA", vendor="sysco", vendor_raw="Sysco",
                price=Decimal("10.00"), description="Item A"
            ),
            PurchaseRecord(
                sku="BBB", vendor="sysco", vendor_raw="Sysco",
                price=Decimal("10.00"), description="Item B"
            ),
        ]
        index = build_index(records)

        matches = index.lookup_vendor_price("sysco", Decimal("10.00"))
        assert len(matches) == 2
        skus = {m.sku for m in matches}
        assert skus == {"AAA", "BBB"}


class TestCanonIndexEdgeCases:
    """Test edge cases for index."""

    def test_empty_records(self):
        index = build_index([])
        assert index.record_count == 0
        assert index.lookup_sku("anything") is None
        assert index.lookup_vendor_price("any", Decimal("0")) == []

    def test_duplicate_skus(self):
        """Last write wins for duplicate SKUs."""
        from nebula.purchase_match.models import PurchaseRecord

        records = [
            PurchaseRecord(
                sku="DUP", vendor="sysco", vendor_raw="Sysco",
                price=Decimal("10.00"), description="First"
            ),
            PurchaseRecord(
                sku="DUP", vendor="sysco", vendor_raw="Sysco",
                price=Decimal("20.00"), description="Second"
            ),
        ]
        index = build_index(records)

        # Should get the second (last) record
        record = index.lookup_sku("DUP")
        assert record.price == Decimal("20.00")
        assert record.description == "Second"
