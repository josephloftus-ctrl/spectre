"""
Tests for report generator (Chunk 5).

Run with: pytest nebula/purchase_match/tests/test_report.py -v
"""

import pytest
from decimal import Decimal
from pathlib import Path
import io

from nebula.purchase_match.models import (
    PurchaseRecord,
    InventoryRecord,
    MatchResult,
    MatchFlag,
)
from nebula.purchase_match.report import (
    format_console,
    export_csv,
    generate_report_filename,
)


@pytest.fixture
def sample_results():
    """Sample match results for testing."""
    return [
        MatchResult(
            inventory_item=InventoryRecord(
                sku="12345", unit="PSEG_HQ",
                description="TOMATO DICED", quantity=Decimal("5"),
                price=Decimal("47.82")
            ),
            flag=MatchFlag.CLEAN,
            ips_match=PurchaseRecord(
                sku="12345", vendor="sysco", vendor_raw="Sysco",
                price=Decimal("47.82"), description="TOMATO DICED #10"
            ),
            reason="SKU found in purchase history"
        ),
        MatchResult(
            inventory_item=InventoryRecord(
                sku="99999", unit="PSEG_HQ",
                description="MISLABELED", quantity=Decimal("3"),
                price=Decimal("47.82")
            ),
            flag=MatchFlag.LIKELY_TYPO,
            ips_match=PurchaseRecord(
                sku="12345", vendor="sysco", vendor_raw="Sysco",
                price=Decimal("47.82"), description="TOMATO DICED #10"
            ),
            reason="Price $47.82 matches 12345"
        ),
        MatchResult(
            inventory_item=InventoryRecord(
                sku="NOPE", unit="PSEG_HQ",
                description="MYSTERY", quantity=Decimal("1"),
                price=Decimal("9999.99")
            ),
            flag=MatchFlag.UNKNOWN,
            reason="No match found"
        ),
        MatchResult(
            inventory_item=InventoryRecord(
                sku="55555", unit="LOCKHEED",
                description="LOCKHEED ITEM", quantity=Decimal("2"),
                price=Decimal("25.00")
            ),
            flag=MatchFlag.UNKNOWN,
            reason="No match found"
        ),
    ]


class TestFormatConsole:
    """Test console report formatting."""

    def test_empty_results(self):
        report = format_console([])
        assert "No inventory items" in report

    def test_groups_by_unit(self, sample_results):
        report = format_console(sample_results)
        assert "UNIT: PSEG_HQ" in report
        assert "UNIT: LOCKHEED" in report

    def test_shows_mismatches_first(self, sample_results):
        report = format_console(sample_results)
        # Within PSEG_HQ section, SKU MISMATCHES should appear before ORPHANS
        pseg_section = report[report.find("UNIT: PSEG_HQ"):]
        mismatch_pos = pseg_section.find("SKU MISMATCHES")
        orphan_pos = pseg_section.find("ORPHANS")
        assert mismatch_pos < orphan_pos

    def test_hides_clean_by_default(self, sample_results):
        report = format_console(sample_results, show_clean=False)
        # Should not show CLEAN section
        assert "CLEAN (1)" not in report

    def test_shows_clean_when_requested(self, sample_results):
        report = format_console(sample_results, show_clean=True)
        assert "CLEAN" in report

    def test_includes_summary(self, sample_results):
        report = format_console(sample_results)
        assert "SUMMARY" in report
        assert "Total items:" in report
        assert "Actionable:" in report

    def test_shows_suggested_sku(self, sample_results):
        report = format_console(sample_results)
        # Should show the suggestion
        assert "12345" in report  # The suggested SKU


class TestExportCSV:
    """Test CSV export functionality."""

    def test_empty_results(self):
        csv = export_csv([])
        lines = csv.strip().split("\n")
        assert len(lines) == 1  # Header only

    def test_csv_header(self, sample_results):
        csv = export_csv(sample_results)
        header = csv.split("\n")[0]
        assert "unit" in header
        assert "flag" in header
        assert "inventory_sku" in header
        assert "suggested_sku" in header

    def test_csv_data_rows(self, sample_results):
        csv = export_csv(sample_results)
        lines = csv.strip().split("\n")
        # Header + 4 data rows
        assert len(lines) == 5

    def test_csv_excludes_clean(self, sample_results):
        csv = export_csv(sample_results, include_clean=False)
        assert "CLEAN" not in csv

    def test_csv_includes_all_fields(self, sample_results):
        csv = export_csv(sample_results)
        # Check that a mismatch row has expected data
        assert "PSEG_HQ" in csv
        assert "LIKELY_TYPO" in csv  # Updated flag value
        assert "99999" in csv
        assert "47.82" in csv

    def test_csv_to_file(self, sample_results):
        buffer = io.StringIO()
        export_csv(sample_results, output=buffer)
        buffer.seek(0)
        content = buffer.read()
        assert "unit,flag,inventory_sku" in content


class TestGenerateFilename:
    """Test report filename generation."""

    def test_without_unit(self):
        filename = generate_report_filename()
        assert filename.startswith("purchase_match_")
        assert filename.endswith(".csv")
        assert "20" in filename  # Year

    def test_with_unit(self):
        filename = generate_report_filename(unit="PSEG_HQ")
        assert "PSEG_HQ" in filename
        assert filename.endswith(".csv")

    def test_custom_extension(self):
        filename = generate_report_filename(extension="txt")
        assert filename.endswith(".txt")
