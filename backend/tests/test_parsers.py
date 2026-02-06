"""
Unit tests for the parsers module — file parsing utilities.

Tests cover:
- CSV parsing (header detection, dialect sniffing)
- Utility functions (to_float, normalize_text, sha256, date extraction)
- Excel internal helpers (_col_index)
- parse_file routing
- Error handling for missing/invalid files
"""
import csv
import tempfile
from pathlib import Path

import pytest

from backend.core.parsers import (
    _col_index,
    date_from_filename_or_mtime,
    normalize_text,
    parse_csv,
    parse_file,
    to_float,
)


# ============================================================================
# to_float
# ============================================================================

class TestToFloat:
    def test_integer(self):
        assert to_float(42) == 42.0

    def test_float(self):
        assert to_float(3.14) == 3.14

    def test_string_number(self):
        assert to_float("123.45") == 123.45

    def test_currency(self):
        assert to_float("$1,234.56") == 1234.56

    def test_empty_string(self):
        assert to_float("") is None

    def test_none(self):
        assert to_float(None) is None

    def test_invalid_string(self):
        assert to_float("not a number") is None

    def test_comma_separated(self):
        assert to_float("1,000") == 1000.0

    def test_dollar_no_comma(self):
        assert to_float("$50.00") == 50.0


# ============================================================================
# normalize_text
# ============================================================================

class TestNormalizeText:
    def test_lowercase(self):
        assert normalize_text("HELLO WORLD") == "hello world"

    def test_strips_whitespace(self):
        assert normalize_text("  test  ") == "test"

    def test_removes_special_chars(self):
        assert normalize_text("Hello! @World #123") == "hello world 123"

    def test_collapses_spaces(self):
        assert normalize_text("too   many   spaces") == "too many spaces"

    def test_empty(self):
        assert normalize_text("") == ""

    def test_none(self):
        assert normalize_text(None) == ""


# ============================================================================
# _col_index
# ============================================================================

class TestColIndex:
    def test_column_a(self):
        assert _col_index("A1") == 1

    def test_column_b(self):
        assert _col_index("B5") == 2

    def test_column_z(self):
        assert _col_index("Z1") == 26

    def test_column_aa(self):
        assert _col_index("AA1") == 27

    def test_column_az(self):
        assert _col_index("AZ1") == 52

    def test_column_ba(self):
        assert _col_index("BA1") == 53


# ============================================================================
# date_from_filename_or_mtime
# ============================================================================

class TestDateFromFilename:
    def test_date_pattern_mm_dd_yyyy(self):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", prefix="report_12.31.2024_") as f:
            dt = date_from_filename_or_mtime(Path(f.name))
            assert dt.year == 2024
            assert dt.month == 12
            assert dt.day == 31

    def test_date_pattern_short_year(self):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", prefix="report_1.5.24_") as f:
            dt = date_from_filename_or_mtime(Path(f.name))
            assert dt.year == 2024
            assert dt.month == 1
            assert dt.day == 5

    def test_no_date_falls_back_to_mtime(self):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", prefix="no_date_here_") as f:
            dt = date_from_filename_or_mtime(Path(f.name))
            # Should fall back to mtime, which is recent
            assert dt.year >= 2024


# ============================================================================
# parse_csv
# ============================================================================

class TestParseCSV:
    def _write_csv(self, rows, headers=None, delimiter=","):
        """Write a temporary CSV file and return its path."""
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        )
        writer = csv.writer(tmp, delimiter=delimiter)
        if headers:
            writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        tmp.close()
        return Path(tmp.name)

    def test_basic_csv(self):
        path = self._write_csv(
            [["Chicken Breast", "5", "CS", "$120.00"]],
            headers=["Item Description", "Quantity", "UOM", "Total Price"],
        )
        result = parse_csv(path)
        assert result["headers"] == ["Item Description", "Quantity", "UOM", "Total Price"]
        assert len(result["rows"]) == 1
        assert result["rows"][0]["Item Description"] == "Chicken Breast"
        assert result["metadata"]["file_type"] == "csv"
        path.unlink()

    def test_multiple_rows(self):
        path = self._write_csv(
            [
                ["Item A", "10", "EA"],
                ["Item B", "5", "CS"],
                ["Item C", "1", "LB"],
            ],
            headers=["Description", "Qty", "UOM"],
        )
        result = parse_csv(path)
        assert len(result["rows"]) == 3
        assert result["metadata"]["row_count"] == 3
        path.unlink()

    def test_empty_csv(self):
        path = self._write_csv([], headers=["A", "B", "C"])
        result = parse_csv(path)
        assert result["rows"] == []
        assert result["metadata"]["row_count"] == 0
        path.unlink()

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_csv("/nonexistent/file.csv")


# ============================================================================
# parse_file routing
# ============================================================================

class TestParseFileRouting:
    def test_csv_routing(self):
        """parse_file routes .csv to parse_csv."""
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        )
        writer = csv.writer(tmp)
        writer.writerow(["A", "B"])
        writer.writerow(["1", "2"])
        tmp.close()
        path = Path(tmp.name)

        result = parse_file(path)
        assert result["metadata"]["file_type"] == "csv"
        path.unlink()

    def test_unsupported_extension(self):
        """parse_file raises ValueError for unknown extensions."""
        tmp = tempfile.NamedTemporaryFile(suffix=".xyz", delete=False)
        tmp.close()
        path = Path(tmp.name)

        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_file(path)
        path.unlink()
