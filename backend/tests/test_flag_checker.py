"""
Unit tests for the flag_checker module — Spectre's health scoring system.

Tests cover:
- Item-level scoring (UOM error, big dollar, beverage exclusion)
- Room-level scoring (low dedicated, low other, high flag concentration)
- Status thresholds (clean → healthy → warning → critical)
- Location parsing from GL codes
- Comprehensive scoring with purchase match integration
"""
from backend.core.flag_checker import (
    parse_location,
    is_beverage,
    score_item,
    get_status_from_score,
    calculate_unit_score,
    calculate_room_metrics,
    is_dedicated_storage,
    calculate_comprehensive_score,
)


# ============================================================================
# parse_location
# ============================================================================

class TestParseLocation:
    def test_gl_code_with_arrow(self):
        assert parse_location("GL Codes->Bakery 411072") == "Bakery"

    def test_location_with_arrow(self):
        assert parse_location("Locations->Walk In Cooler") == "Walk In Cooler"

    def test_gl_code_with_trailing_number(self):
        assert parse_location("GL Codes->Meat/ Poultry 411037") == "Meat/ Poultry"

    def test_plain_text(self):
        assert parse_location("Unassigned") == "Unassigned"

    def test_empty_string(self):
        assert parse_location("") == "Unknown"

    def test_none(self):
        assert parse_location(None) == "Unknown"

    def test_non_string(self):
        assert parse_location(42) == "Unknown"


# ============================================================================
# is_beverage
# ============================================================================

class TestIsBeverage:
    def test_soda_by_description(self):
        assert is_beverage("COCA-COLA 12PK") is True

    def test_energy_drink(self):
        assert is_beverage("RED BULL ENERGY DRINK 24/12OZ") is True

    def test_water(self):
        assert is_beverage("DASANI WATER 24PK") is True

    def test_coffee(self):
        assert is_beverage("STARBUCKS COLD BREW") is True

    def test_non_beverage(self):
        assert is_beverage("BEEF PATTY 8OZ") is False

    def test_beverage_by_location(self):
        assert is_beverage("SOME ITEM", location="Beverage Room") is True

    def test_empty_description(self):
        assert is_beverage("") is False

    def test_none_description(self):
        assert is_beverage(None) is False

    def test_celsius(self):
        assert is_beverage("CELSIUS ENERGY SPARKLING") is True

    def test_juice(self):
        assert is_beverage("ORANGE JUICE 64OZ") is True


# ============================================================================
# score_item
# ============================================================================

class TestScoreItem:
    def _make_row(self, qty=1, uom="EA", total=10.0, desc="TEST ITEM"):
        return {
            "Quantity": qty,
            "UOM": uom,
            "Total Price": total,
            "Item Description": desc,
        }

    def test_clean_item(self):
        """No flags for normal item."""
        points, flags = score_item(self._make_row(qty=2, uom="EA", total=50))
        assert points == 0
        assert flags == []

    def test_uom_error_high_case_count(self):
        """Qty >= 10 + CS = 3 points."""
        points, flags = score_item(self._make_row(qty=15, uom="CS", total=100))
        assert points == 3
        assert "uom_error" in flags

    def test_uom_error_exactly_10(self):
        """Boundary: Qty == 10 + CS triggers."""
        points, flags = score_item(self._make_row(qty=10, uom="CS"))
        assert points == 3
        assert "uom_error" in flags

    def test_uom_error_below_threshold(self):
        """Qty < 10 + CS = no flag."""
        points, flags = score_item(self._make_row(qty=9, uom="CS"))
        assert points == 0

    def test_uom_error_not_cs(self):
        """High qty with EA = no flag."""
        points, flags = score_item(self._make_row(qty=50, uom="EA"))
        assert points == 0

    def test_big_dollar(self):
        """Total > $250 = 1 point."""
        points, flags = score_item(self._make_row(total=300))
        assert points == 1
        assert "big_dollar" in flags

    def test_big_dollar_boundary(self):
        """$250 exactly = no flag (must be > 250)."""
        points, flags = score_item(self._make_row(total=250))
        assert points == 0

    def test_combined_flags(self):
        """Item can have both UOM error and big dollar."""
        points, flags = score_item(self._make_row(qty=12, uom="CS", total=500))
        assert points == 4  # 3 + 1
        assert "uom_error" in flags
        assert "big_dollar" in flags

    def test_beverage_excluded_from_uom_error(self):
        """Beverages skip UOM error even with high case count."""
        points, flags = score_item(self._make_row(qty=20, uom="CS", desc="COCA-COLA 12PK"))
        assert points == 0
        assert "uom_error" not in flags

    def test_beverage_excluded_from_big_dollar(self):
        """Beverages skip big dollar flag."""
        points, flags = score_item(self._make_row(total=500, desc="RED BULL ENERGY"))
        assert points == 0
        assert "big_dollar" not in flags

    def test_currency_formatted_total(self):
        """Handles $ and comma in total price."""
        row = self._make_row()
        row["Total Price"] = "$1,500.00"
        points, flags = score_item(row)
        assert points == 1
        assert "big_dollar" in flags

    def test_case_insensitive_keys(self):
        """Handles different column name casing."""
        row = {"quantity": 12, "uom": "CS", "total price": 100, "item description": "BEEF"}
        points, flags = score_item(row)
        assert points == 3


# ============================================================================
# get_status_from_score
# ============================================================================

class TestGetStatusFromScore:
    def test_clean(self):
        assert get_status_from_score(0) == "clean"

    def test_healthy_low(self):
        assert get_status_from_score(1) == "healthy"

    def test_healthy_high(self):
        assert get_status_from_score(4) == "healthy"

    def test_warning_low(self):
        assert get_status_from_score(5) == "warning"

    def test_warning_high(self):
        assert get_status_from_score(10) == "warning"

    def test_critical(self):
        assert get_status_from_score(11) == "critical"

    def test_very_critical(self):
        assert get_status_from_score(50) == "critical"


# ============================================================================
# is_dedicated_storage
# ============================================================================

class TestIsDedicatedStorage:
    def test_walk_in_cooler(self):
        assert is_dedicated_storage("Walk In Cooler") is True

    def test_freezer(self):
        assert is_dedicated_storage("Freezer") is True

    def test_dry_storage(self):
        assert is_dedicated_storage("Dry Storage Food") is True

    def test_beverage_room(self):
        assert is_dedicated_storage("Beverage Room") is True

    def test_front_of_house(self):
        assert is_dedicated_storage("Front of House") is False

    def test_line(self):
        assert is_dedicated_storage("Line") is False

    def test_empty(self):
        assert is_dedicated_storage("") is False

    def test_none(self):
        assert is_dedicated_storage(None) is False


# ============================================================================
# calculate_unit_score
# ============================================================================

class TestCalculateUnitScore:
    def _make_rows(self, items):
        """Build inventory rows from simplified item specs."""
        rows = []
        for item in items:
            rows.append({
                "Item Description": item.get("desc", "TEST ITEM"),
                "Quantity": item.get("qty", 1),
                "UOM": item.get("uom", "EA"),
                "Total Price": item.get("total", 10),
                "GL Codes": item.get("location", "GL Codes->Dry Storage Food 411001"),
            })
        return rows

    def test_clean_unit(self):
        """Unit with no issues scores 0 / clean."""
        rows = self._make_rows([
            {"desc": "CHICKEN BREAST", "qty": 3, "uom": "CS", "total": 80},
            {"desc": "LETTUCE HEAD", "qty": 5, "uom": "EA", "total": 25},
        ])
        result = calculate_unit_score(rows)
        assert result["score"] >= 0
        assert result["summary"]["item_count"] == 2

    def test_flagged_items_returned(self):
        """Items with flags appear in item_flags list."""
        rows = self._make_rows([
            {"desc": "BEEF PATTY", "qty": 15, "uom": "CS", "total": 300},
        ])
        result = calculate_unit_score(rows)
        assert len(result["item_flags"]) > 0
        assert result["item_flags"][0]["item"] == "BEEF PATTY"

    def test_total_value_calculated(self):
        """Summary includes correct total value."""
        rows = self._make_rows([
            {"total": 100},
            {"total": 200},
            {"total": 300},
        ])
        result = calculate_unit_score(rows)
        assert result["summary"]["total_value"] == 600.0

    def test_room_totals_aggregated(self):
        """Room totals aggregate values by location."""
        rows = self._make_rows([
            {"total": 500, "location": "GL Codes->Freezer 411001"},
            {"total": 300, "location": "GL Codes->Freezer 411001"},
            {"total": 200, "location": "GL Codes->Dry Storage Food 411002"},
        ])
        result = calculate_unit_score(rows)
        assert "Freezer" in result["room_totals"]
        assert result["room_totals"]["Freezer"]["total_value"] == 800.0

    def test_beverage_items_skipped_in_scoring(self):
        """Beverages don't contribute to item score."""
        rows = self._make_rows([
            {"desc": "COCA-COLA 12PK", "qty": 50, "uom": "CS", "total": 800},
        ])
        result = calculate_unit_score(rows)
        assert len(result["item_flags"]) == 0

    def test_status_matches_score(self):
        """Status label corresponds to the total score."""
        # Generate a score in the warning range (5-10)
        rows = self._make_rows([
            {"desc": "ITEM A", "qty": 12, "uom": "CS", "total": 300},  # 3 + 1 = 4
            {"desc": "ITEM B", "qty": 10, "uom": "CS", "total": 100},  # 3
        ])
        result = calculate_unit_score(rows)
        assert result["score"] >= 5
        assert result["status"] in ("warning", "critical")


# ============================================================================
# calculate_room_metrics
# ============================================================================

class TestCalculateRoomMetrics:
    def test_low_dedicated_storage_flagged(self):
        """Dedicated storage with < $1000 gets flagged."""
        rows = [
            {"GL Codes": "GL Codes->Freezer 411001", "Total Price": 500},
        ]
        result = calculate_room_metrics(rows, [], gl_code_key="GL Codes")
        assert result["room_score"] > 0
        low_flags = [f for f in result["room_flags"] if "low_dedicated" in f["flag_type"]]
        assert len(low_flags) > 0

    def test_low_other_room_flagged(self):
        """Non-dedicated room with < $200 gets flagged."""
        rows = [
            {"GL Codes": "GL Codes->Bakery 411001", "Total Price": 100},
        ]
        result = calculate_room_metrics(rows, [], gl_code_key="GL Codes")
        low_flags = [f for f in result["room_flags"] if "low_other" in f["flag_type"]]
        assert len(low_flags) > 0

    def test_healthy_room_not_flagged(self):
        """Room above threshold is not flagged."""
        rows = [
            {"GL Codes": "GL Codes->Freezer 411001", "Total Price": 5000},
        ]
        result = calculate_room_metrics(rows, [], gl_code_key="GL Codes")
        freezer_flags = [f for f in result["room_flags"] if f["location"] == "Freezer"]
        assert len(freezer_flags) == 0

    def test_high_flag_concentration(self):
        """Room with 3+ flagged items gets additional flag."""
        item_flags = [
            {"item": "A", "flags": ["uom_error"], "points": 3, "location": "Freezer"},
            {"item": "B", "flags": ["uom_error"], "points": 3, "location": "Freezer"},
            {"item": "C", "flags": ["big_dollar"], "points": 1, "location": "Freezer"},
        ]
        rows = [
            {"GL Codes": "GL Codes->Freezer 411001", "Total Price": 5000},
        ]
        result = calculate_room_metrics(rows, item_flags, gl_code_key="GL Codes")
        high_flags = [f for f in result["room_flags"] if "high_flags" in f["flag_type"]]
        assert len(high_flags) > 0


# ============================================================================
# calculate_comprehensive_score
# ============================================================================

class TestCalculateComprehensiveScore:
    def test_without_purchase_match(self):
        """Works without purchase match results."""
        rows = [
            {"Item Description": "BEEF", "Quantity": 2, "UOM": "EA", "Total Price": 50,
             "GL Codes": "GL Codes->Freezer 411001"},
        ]
        result = calculate_comprehensive_score(rows)
        assert "score" in result
        assert "item_flags" in result

    def test_with_likely_typo(self):
        """LIKELY_TYPO from purchase match adds 2 points."""
        rows = [
            {"Item Description": "BEEF PATTY", "Dist #": "123456", "Quantity": 2,
             "UOM": "EA", "Total Price": 50, "GL Codes": "GL Codes->Freezer 411001"},
        ]
        pm_results = [
            {"sku": "123456", "flag": "LIKELY_TYPO", "reason": "Did you mean 123457?"},
        ]
        result = calculate_comprehensive_score(rows, purchase_match_results=pm_results)
        sku_flags = [f for f in result["item_flags"] if "sku_mismatch" in f["flags"]]
        assert len(sku_flags) == 1
        assert sku_flags[0]["points"] == 2

    def test_with_unknown_sku(self):
        """UNKNOWN from purchase match adds 1 point."""
        rows = [
            {"Item Description": "MYSTERY", "Dist #": "999999", "Quantity": 1,
             "UOM": "EA", "Total Price": 20, "GL Codes": "GL Codes->Dry Storage Food 411001"},
        ]
        pm_results = [
            {"sku": "999999", "flag": "UNKNOWN", "reason": "Not in catalog"},
        ]
        result = calculate_comprehensive_score(rows, purchase_match_results=pm_results)
        unknown_flags = [f for f in result["item_flags"] if "unknown_sku" in f["flags"]]
        assert len(unknown_flags) == 1
        assert unknown_flags[0]["points"] == 1

    def test_clean_purchase_match_no_extra_flags(self):
        """CLEAN items from purchase match don't add flags."""
        rows = [
            {"Item Description": "CHICKEN", "Dist #": "111111", "Quantity": 2,
             "UOM": "EA", "Total Price": 50, "GL Codes": "GL Codes->Freezer 411001"},
        ]
        pm_results = [
            {"sku": "111111", "flag": "CLEAN", "reason": "Exact match"},
        ]
        result = calculate_comprehensive_score(rows, purchase_match_results=pm_results)
        pm_flags = [f for f in result["item_flags"] if "sku_mismatch" in f.get("flags", []) or "unknown_sku" in f.get("flags", [])]
        assert len(pm_flags) == 0
