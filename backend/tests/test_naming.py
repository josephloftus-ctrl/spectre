"""
Unit tests for the naming module — site ID extraction and normalization.

Tests cover:
- slugify (text → URL-safe slug)
- extract_site_from_filename (filename → site_id)
- match_known_site (fuzzy matching against known patterns)
- format_display_name (site_id → human-readable display)
- normalize_site_id (standardization)
- generate_standard_filename (site_id + date → filename)
"""
from backend.core.naming import (
    slugify,
    extract_site_from_filename,
    match_known_site,
    format_display_name,
    normalize_site_id,
    generate_standard_filename,
)


# ============================================================================
# slugify
# ============================================================================

class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello_world"

    def test_with_special_chars(self):
        assert slugify("PSEG - NHQ (673)") == "pseg_nhq_673"

    def test_hyphens_to_underscores(self):
        assert slugify("lockheed-martin") == "lockheed_martin"

    def test_multiple_spaces(self):
        assert slugify("too   many   spaces") == "too_many_spaces"

    def test_leading_trailing(self):
        assert slugify("  test  ") == "test"

    def test_empty(self):
        assert slugify("") == ""

    def test_max_length(self):
        result = slugify("a" * 100, max_length=10)
        assert len(result) == 10

    def test_collapses_underscores(self):
        assert slugify("foo___bar") == "foo_bar"

    def test_removes_parens(self):
        assert slugify("Test (123)") == "test_123"


# ============================================================================
# extract_site_from_filename
# ============================================================================

class TestExtractSiteFromFilename:
    def test_simple_name(self):
        assert extract_site_from_filename("PSEG NHQ.xlsx") == "pseg_nhq"

    def test_name_with_date_suffix(self):
        assert extract_site_from_filename("PSEG NHQ 1_8.xlsx") == "pseg_nhq"

    def test_date_prefix(self):
        result = extract_site_from_filename("01.15.25 - PSEG NHQ.xlsx")
        assert result == "pseg_nhq"

    def test_standard_filename_format(self):
        """Handles the standardized {SITE}_{N}_{DATE} format."""
        result = extract_site_from_filename("NHQ_1_2026-01-18.xlsx")
        assert result == "pseg_nhq"

    def test_lockheed_bldg_100(self):
        result = extract_site_from_filename("Lockheed Martin Bldg 100.xlsx")
        assert result == "lockheed_martin_bldg_100"

    def test_lockheed_typo(self):
        """Handles common 'Lockhead' typo."""
        result = extract_site_from_filename("Lockhead Martin, Bldg 100.xlsx")
        assert result == "lockheed_martin_bldg_100"

    def test_hope_creek(self):
        result = extract_site_from_filename("Hope Creek.xlsx")
        assert result == "pseg_hope_creek"

    def test_salem(self):
        result = extract_site_from_filename("PSEG Salem 1_29.xlsx")
        assert result == "pseg_salem"

    def test_empty(self):
        assert extract_site_from_filename("") is None

    def test_none(self):
        assert extract_site_from_filename(None) is None

    def test_just_numbers(self):
        """Filenames with only numbers/special chars return None."""
        assert extract_site_from_filename("123456.xlsx") is None


# ============================================================================
# match_known_site
# ============================================================================

class TestMatchKnownSite:
    def test_exact_pattern(self):
        assert match_known_site("pseg nhq") == "pseg_nhq"

    def test_partial_match(self):
        assert match_known_site("PSEG NHQ building 5") == "pseg_nhq"

    def test_lockheed_100(self):
        assert match_known_site("lockheed 100") == "lockheed_martin_bldg_100"

    def test_bldg_d(self):
        assert match_known_site("lockheed d") == "lockheed_martin_bldg_d"

    def test_nhq_abbreviation(self):
        assert match_known_site("nhq") == "pseg_nhq"

    def test_no_match(self):
        assert match_known_site("completely unknown site") is None

    def test_case_insensitive(self):
        assert match_known_site("PSEG NHQ") == "pseg_nhq"


# ============================================================================
# format_display_name
# ============================================================================

class TestFormatDisplayName:
    def test_pseg_nhq(self):
        assert format_display_name("pseg_nhq") == "PSEG NHQ"

    def test_lockheed(self):
        result = format_display_name("lockheed_martin_bldg_100")
        assert result == "Lockheed Martin Bldg 100"

    def test_pseg_hq(self):
        assert format_display_name("pseg_hq") == "PSEG HQ"

    def test_empty(self):
        assert format_display_name("") == "Unknown"

    def test_none(self):
        assert format_display_name(None) == "Unknown"

    def test_unknown_site(self):
        """Non-acronym words get title case."""
        assert format_display_name("some_new_site") == "Some New Site"


# ============================================================================
# normalize_site_id
# ============================================================================

class TestNormalizeSiteId:
    def test_already_normalized(self):
        assert normalize_site_id("pseg_nhq") == "pseg_nhq"

    def test_uppercase(self):
        assert normalize_site_id("PSEG NHQ") == "pseg_nhq"

    def test_hyphens(self):
        assert normalize_site_id("pseg-nhq") == "pseg_nhq"

    def test_none_with_filename(self):
        result = normalize_site_id(None, filename="PSEG NHQ.xlsx")
        assert result == "pseg_nhq"

    def test_none_no_filename(self):
        assert normalize_site_id(None) == "unknown"

    def test_empty_string(self):
        """Empty string falls through to filename or 'unknown'."""
        result = normalize_site_id("", filename="")
        assert result == "unknown"


# ============================================================================
# generate_standard_filename
# ============================================================================

class TestGenerateStandardFilename:
    def test_basic(self):
        result = generate_standard_filename("pseg_nhq", "report.xlsx", "2026-01-15")
        assert result == "PSEG_NHQ_2026-01-15.xlsx"

    def test_preserves_extension(self):
        result = generate_standard_filename("pseg_nhq", "data.csv", "2026-01-15")
        assert result.endswith(".csv")

    def test_uppercase_site(self):
        result = generate_standard_filename("lockheed_100", "test.xlsx", "2026-02-01")
        assert result == "LOCKHEED_100_2026-02-01.xlsx"

    def test_default_date(self):
        """Without date_str, uses current date."""
        result = generate_standard_filename("pseg_nhq", "test.xlsx")
        assert result.startswith("PSEG_NHQ_")
        assert result.endswith(".xlsx")
        # Should have a date in the middle
        assert len(result.split("_")) >= 3
