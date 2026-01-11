"""
Integration tests for Purchase Match Diagnostic (Chunk 6).

These tests verify the full pipeline works end-to-end.
Run with: pytest nebula/purchase_match/tests/test_integration.py -v
"""

import pytest
from decimal import Decimal
from pathlib import Path

from nebula.purchase_match.config import load_config
from nebula.purchase_match.canon_loader import load_canon
from nebula.purchase_match.index import build_index
from nebula.purchase_match.adapters import InMemoryInventoryAdapter
from nebula.purchase_match.matcher import match_inventory, summarize_results
from nebula.purchase_match.report import format_console, export_csv
from nebula.purchase_match.models import InventoryRecord, MatchFlag
from nebula.purchase_match.ops_adapter import OpsDashboardInventoryAdapter


# Paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
CONFIG_PATH = Path(__file__).parent.parent / "unit_vendor_config.json"
SAMPLE_IPS = FIXTURES_DIR / "sample_ips.xlsx"


class TestFullPipeline:
    """Test complete pipeline from IPS load to report generation."""

    @pytest.fixture
    def config(self):
        return load_config(CONFIG_PATH)

    @pytest.fixture
    def index(self, config):
        records = load_canon([SAMPLE_IPS], config)
        return build_index(records)

    def test_pipeline_with_known_scenarios(self, index, config):
        """
        Test full pipeline with controlled inventory data.

        Simple logic:
        - CLEAN: SKU exists in IPS
        - ORPHAN: SKU not in IPS
        """
        inventory = [
            # Should be CLEAN - exact SKU match
            InventoryRecord(
                sku="117377", unit="PSEG_HQ",
                description="TOMATO", quantity=Decimal("5")
            ),
            # Should be ORPHAN - SKU not in IPS (regardless of price)
            InventoryRecord(
                sku="FAKE123", unit="PSEG_HQ",
                description="UNKNOWN ITEM", quantity=Decimal("3"),
                price=Decimal("47.82")
            ),
            # Should be ORPHAN - SKU not in IPS
            InventoryRecord(
                sku="NOPE", unit="PSEG_HQ",
                description="ANOTHER UNKNOWN", quantity=Decimal("1"),
                price=Decimal("9999.99")
            ),
        ]

        adapter = InMemoryInventoryAdapter(inventory)
        items = adapter.get_inventory_for_unit("PSEG_HQ")
        results = match_inventory(items, index, config)

        # Verify counts
        summary = summarize_results(results)
        assert summary["total"] == 3
        assert summary["clean"] == 1
        assert summary["sku_mismatch"] == 0  # No more SKU_MISMATCH
        assert summary["orphan"] == 2

        # Verify specific flags
        by_sku = {r.inventory_item.sku: r for r in results}
        assert by_sku["117377"].flag == MatchFlag.CLEAN
        assert by_sku["FAKE123"].flag == MatchFlag.ORPHAN
        assert by_sku["NOPE"].flag == MatchFlag.ORPHAN

    def test_pipeline_generates_report(self, index, config):
        """Test that pipeline produces valid console and CSV reports."""
        inventory = [
            InventoryRecord(
                sku="117377", unit="PSEG_HQ",
                description="TOMATO", quantity=Decimal("5")
            ),
            InventoryRecord(
                sku="FAKE", unit="PSEG_HQ",
                description="FAKE ITEM", quantity=Decimal("1"),
                price=Decimal("47.82")
            ),
        ]

        adapter = InMemoryInventoryAdapter(inventory)
        results = match_inventory(adapter.get_inventory_for_unit("PSEG_HQ"), index, config)

        # Console report
        console = format_console(results)
        assert "PSEG_HQ" in console
        assert "SUMMARY" in console

        # CSV export
        csv = export_csv(results)
        assert "unit,flag,inventory_sku" in csv
        assert "PSEG_HQ" in csv

    def test_vendor_constraint_enforced(self, index, config):
        """Test that vendor constraints prevent cross-vendor suggestions."""
        inventory = [
            # LOCKHEED uses Gordon, not Sysco
            # Price $47.82 matches sysco 117377, but should NOT suggest it
            InventoryRecord(
                sku="FAKE", unit="LOCKHEED",
                description="SYSCO PRICE ITEM", quantity=Decimal("1"),
                price=Decimal("47.82")
            ),
        ]

        adapter = InMemoryInventoryAdapter(inventory)
        results = match_inventory(adapter.get_inventory_for_unit("LOCKHEED"), index, config)

        # Should be ORPHAN, not SKU_MISMATCH
        # Because $47.82 is sysco, and LOCKHEED doesn't use sysco
        assert results[0].flag == MatchFlag.ORPHAN
        assert results[0].suggested_match is None

    def test_multi_unit_processing(self, index, config):
        """Test processing inventory from multiple units."""
        inventory = [
            InventoryRecord(
                sku="117377", unit="PSEG_HQ",
                description="PSEG TOMATO", quantity=Decimal("5")
            ),
            InventoryRecord(
                sku="567890", unit="LOCKHEED",
                description="LOCKHEED BEEF", quantity=Decimal("3")
            ),
        ]

        adapter = InMemoryInventoryAdapter(inventory)

        # Process each unit separately
        pseg_results = match_inventory(
            adapter.get_inventory_for_unit("PSEG_HQ"), index, config
        )
        lockheed_results = match_inventory(
            adapter.get_inventory_for_unit("LOCKHEED"), index, config
        )

        assert len(pseg_results) == 1
        assert len(lockheed_results) == 1
        assert pseg_results[0].flag == MatchFlag.CLEAN
        assert lockheed_results[0].flag == MatchFlag.CLEAN


class TestOpsDashboardAdapter:
    """Test ops dashboard adapter stub."""

    def test_raises_not_implemented(self):
        """Verify adapter correctly raises NotImplementedError."""
        adapter = OpsDashboardInventoryAdapter()

        with pytest.raises(NotImplementedError) as exc_info:
            adapter.get_inventory_for_unit("PSEG_HQ")
        assert "pending" in str(exc_info.value).lower()

        with pytest.raises(NotImplementedError) as exc_info:
            adapter.get_all_units()
        assert "pending" in str(exc_info.value).lower()


class TestModuleImports:
    """Verify module is properly siloed - no external Nebula imports."""

    def test_no_external_nebula_imports(self):
        """Ensure purchase_match has no imports from other Nebula modules."""
        import nebula.purchase_match as pm

        # Get all module files
        module_dir = Path(pm.__file__).parent
        py_files = list(module_dir.glob("*.py"))

        for py_file in py_files:
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text()

            # Check for imports from other nebula modules
            # (should only import from nebula.purchase_match)
            lines = content.split("\n")
            for line in lines:
                if "from nebula" in line or "import nebula" in line:
                    # Should only be from nebula.purchase_match
                    assert "purchase_match" in line, (
                        f"Found external nebula import in {py_file.name}: {line}"
                    )
