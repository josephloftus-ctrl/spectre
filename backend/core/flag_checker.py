"""
Flag Checker Module - Unit Health Scoring System

Scoring rules:
- Item-level flags:
  - UOM Error (High Case Count): Qty >= 10 AND UOM = "CS" → 3 pts
  - Big Dollar: Total Price > $250 → 1 pt
  - SKU Mismatch (from purchase match): LIKELY_TYPO → 2 pts
  - Unknown SKU (from purchase match): UNKNOWN → 1 pt

- Room-level flags:
  - Low Dedicated Storage: Walk-in/Freezer/Dry Storage < $1,000 → 2 pts
  - Low Other Room: Front of house/Line < $200 → 2 pts

Higher score = worse health. Units sorted worst-first.
"""

import re
from typing import Optional, List, Dict, Any
from collections import defaultdict


# Dedicated storage areas (should have significant inventory)
DEDICATED_STORAGE = [
    "walk-in cooler", "walk in cooler", "walkin cooler",
    "freezer", "walk-in freezer", "walk in freezer",
    "dry storage", "dry storage food", "dry storage supplies",
    "beverage room", "beverage",
    "chemical locker", "chemical storage"
]

# Threshold for dedicated storage (should be at least $1,000)
DEDICATED_STORAGE_THRESHOLD = 1000.0

# Threshold for other rooms (should be at least $200)
OTHER_ROOM_THRESHOLD = 200.0


def parse_location(gl_code: str) -> str:
    """
    Extract location from GL Code column.

    Examples:
        'GL Codes->Bakery 411072' → 'Bakery'
        'GL Codes->Meat/ Poultry 411037' → 'Meat/ Poultry'
        'Locations->Walk In Cooler' → 'Walk In Cooler'
        'Unassigned' → 'Unassigned'
    """
    if not gl_code or not isinstance(gl_code, str):
        return "Unknown"

    gl_code = gl_code.strip()

    # Check for arrow separator
    if "->" in gl_code:
        after_arrow = gl_code.split("->", 1)[1].strip()
        # Remove trailing GL code numbers (6 digits)
        location = re.sub(r"\s+\d{6}$", "", after_arrow).strip()
        return location if location else "Unknown"

    return gl_code if gl_code else "Unknown"


def is_beverage(item_desc: str, location: str = "") -> bool:
    """Check if an item is a beverage (excluded from case count flags)."""
    if not item_desc:
        return False
    desc_lower = item_desc.lower()
    loc_lower = location.lower() if location else ""

    # Check if location is Beverages
    if "beverage" in loc_lower:
        return True

    beverage_keywords = [
        # Generic terms
        "soda", "cola", "juice", "water", "tea", "coffee", "lemonade",
        "milk", "cream", "beverage", "drink", "bottle", "can ",
        # Brand names
        "coke", "coca-cola", "pepsi", "sprite", "fanta", "dr pepper",
        "gatorade", "powerade", "red bull", "monster", "rockstar",
        "celsius", "celius", "bang", "reign", "prime",
        "snapple", "lipton", "arizona", "pure leaf", "brisk",
        "mountain dew", "mtn dew", "7up", "7-up", "sierra mist",
        "dasani", "aquafina", "evian", "fiji", "smartwater",
        "starbucks", "dunkin", "nespresso"
    ]
    return any(kw in desc_lower for kw in beverage_keywords)


def score_item(row: dict) -> tuple[int, list[str]]:
    """
    Score a single inventory item and return flags.

    Args:
        row: Dict with keys like 'Quantity', 'UOM', 'Total Price', 'Item Description'

    Returns:
        tuple of (points, [flag_names])
    """
    points = 0
    flags = []

    # Normalize keys (handle different casing)
    qty = None
    uom = None
    total = None
    item_desc = ""

    for key, value in row.items():
        key_lower = key.lower() if isinstance(key, str) else ""
        if "quantity" in key_lower or key_lower == "qty":
            try:
                qty = float(value) if value else 0
            except (ValueError, TypeError):
                qty = 0
        elif key_lower == "uom" or "unit" in key_lower:
            uom = str(value).upper().strip() if value else ""
        elif "total" in key_lower and "price" in key_lower:
            try:
                # Handle currency formatting
                val_str = str(value).replace("$", "").replace(",", "").strip()
                total = float(val_str) if val_str else 0
            except (ValueError, TypeError):
                total = 0
        elif "description" in key_lower or "item" in key_lower:
            item_desc = str(value) if value else ""

    # UOM Error: Qty >= 10 AND UOM contains "CS" or "CASE"
    # Skip beverages - high case counts are expected
    if qty is not None and qty >= 10 and uom in ("CS", "CASE", "CSE"):
        if not is_beverage(item_desc):
            points += 3
            flags.append("uom_error")

    # Big Dollar: Total > $250
    # Skip beverages
    if total is not None and total > 250:
        if not is_beverage(item_desc):
            points += 1
            flags.append("big_dollar")

    return points, flags


def get_status_from_score(score: int) -> str:
    """
    Convert numerical score to status category.

    - critical: score > 10
    - warning: score 5-10
    - healthy: score 1-4
    - clean: score 0
    """
    if score > 10:
        return "critical"
    elif score >= 5:
        return "warning"
    elif score >= 1:
        return "healthy"
    else:
        return "clean"


def calculate_unit_score(rows: list[dict], gl_code_key: str = None) -> dict:
    """
    Calculate the health score for an entire unit/site.

    Args:
        rows: List of inventory row dicts
        gl_code_key: Optional key name for GL Code column (auto-detected if not provided)

    Returns:
        {
            "score": int,
            "status": str,  # critical/warning/healthy/clean
            "item_flags": [{item, qty, uom, total, flags, points, location}],
            "summary": {
                "total_value": float,
                "item_count": int,
                "flagged_items": int
            }
        }
    """
    total_score = 0
    item_flags = []
    total_value = 0.0

    # Auto-detect GL Code column key
    if not gl_code_key and rows:
        for key in rows[0].keys():
            key_lower = key.lower() if isinstance(key, str) else ""
            if "gl" in key_lower or "location" in key_lower:
                gl_code_key = key
                break

    # Process each item
    for row in rows:
        # Get item details
        item_desc = ""
        qty = 0
        uom = ""
        total = 0.0
        gl_code = ""

        for key, value in row.items():
            key_lower = key.lower() if isinstance(key, str) else ""

            if "description" in key_lower or "item" in key_lower:
                item_desc = str(value) if value else ""
            elif "quantity" in key_lower or key_lower == "qty":
                try:
                    qty = float(value) if value else 0
                except (ValueError, TypeError):
                    qty = 0
            elif key_lower == "uom" or "unit" in key_lower:
                uom = str(value).strip() if value else ""
            elif "total" in key_lower and "price" in key_lower:
                try:
                    val_str = str(value).replace("$", "").replace(",", "").strip()
                    total = float(val_str) if val_str else 0
                except (ValueError, TypeError):
                    total = 0
            elif gl_code_key and key == gl_code_key:
                gl_code = str(value) if value else ""
            elif "gl" in key_lower or "location" in key_lower:
                gl_code = str(value) if value else ""

        # Parse location from GL code
        location = parse_location(gl_code)
        total_value += total

        # Skip scoring for beverages
        if is_beverage(item_desc, location):
            continue

        # Score this item
        points, flags = score_item(row)

        if points > 0:
            total_score += points
            item_flags.append({
                "item": item_desc,
                "qty": qty,
                "uom": uom,
                "total": total,
                "flags": flags,
                "points": points,
                "location": location
            })

    # Sort flagged items by points (worst first)
    item_flags.sort(key=lambda x: x["points"], reverse=True)

    # Calculate room-level metrics
    room_data = calculate_room_metrics(rows, item_flags, gl_code_key)

    return {
        "score": total_score + room_data["room_score"],
        "status": get_status_from_score(total_score + room_data["room_score"]),
        "item_flags": item_flags,
        "room_flags": room_data["room_flags"],
        "room_totals": room_data["room_totals"],
        "summary": {
            "total_value": round(total_value, 2),
            "item_count": len(rows),
            "flagged_items": len(item_flags),
            "flagged_rooms": len(room_data["room_flags"])
        }
    }


def is_dedicated_storage(location: str) -> bool:
    """Check if a location is a dedicated storage area."""
    if not location:
        return False
    loc_lower = location.lower().strip()
    return any(storage in loc_lower for storage in DEDICATED_STORAGE)


def calculate_room_metrics(
    rows: List[Dict],
    item_flags: List[Dict],
    gl_code_key: str = None
) -> Dict[str, Any]:
    """
    Calculate room-level metrics and flags.

    Args:
        rows: All inventory rows
        item_flags: Already-calculated item flags
        gl_code_key: Key for GL Code column

    Returns:
        {
            "room_score": int,
            "room_flags": [{location, total_value, item_count, flagged_count, flag_type, points}],
            "room_totals": {location: {total_value, item_count, flagged_count}}
        }
    """
    room_totals: Dict[str, Dict] = defaultdict(lambda: {
        "total_value": 0.0,
        "item_count": 0,
        "flagged_count": 0,
        "flagged_items": []
    })

    # Aggregate items by location
    for row in rows:
        gl_code = ""
        total = 0.0

        for key, value in row.items():
            key_lower = key.lower() if isinstance(key, str) else ""
            if gl_code_key and key == gl_code_key:
                gl_code = str(value) if value else ""
            elif "gl" in key_lower or "location" in key_lower:
                gl_code = str(value) if value else ""
            elif "total" in key_lower and "price" in key_lower:
                try:
                    val_str = str(value).replace("$", "").replace(",", "").strip()
                    total = float(val_str) if val_str else 0
                except (ValueError, TypeError):
                    total = 0

        location = parse_location(gl_code)
        room_totals[location]["total_value"] += total
        room_totals[location]["item_count"] += 1

    # Add flagged item counts per room
    for flag in item_flags:
        location = flag.get("location", "Unknown")
        room_totals[location]["flagged_count"] += 1
        room_totals[location]["flagged_items"].append({
            "item": flag["item"],
            "flags": flag["flags"],
            "points": flag["points"]
        })

    # Calculate room-level flags
    room_flags = []
    room_score = 0

    for location, data in room_totals.items():
        if location in ("Unknown", "Unassigned"):
            continue

        is_dedicated = is_dedicated_storage(location)
        threshold = DEDICATED_STORAGE_THRESHOLD if is_dedicated else OTHER_ROOM_THRESHOLD

        # Flag low-value rooms
        if data["total_value"] < threshold and data["item_count"] > 0:
            points = 2
            room_score += points
            room_flags.append({
                "location": location,
                "total_value": round(data["total_value"], 2),
                "item_count": data["item_count"],
                "flagged_count": data["flagged_count"],
                "flag_type": "low_dedicated" if is_dedicated else "low_other",
                "threshold": threshold,
                "points": points
            })

        # Flag rooms with high concentration of flagged items
        if data["flagged_count"] >= 3:
            points = 1
            room_score += points
            # Check if not already flagged
            existing = next((r for r in room_flags if r["location"] == location), None)
            if existing:
                existing["points"] += points
                existing["flag_type"] += ",high_flags"
            else:
                room_flags.append({
                    "location": location,
                    "total_value": round(data["total_value"], 2),
                    "item_count": data["item_count"],
                    "flagged_count": data["flagged_count"],
                    "flag_type": "high_flags",
                    "points": points
                })

    # Sort room flags by points (worst first)
    room_flags.sort(key=lambda x: x["points"], reverse=True)

    # Convert room_totals for JSON serialization
    room_totals_clean = {
        loc: {
            "total_value": round(data["total_value"], 2),
            "item_count": data["item_count"],
            "flagged_count": data["flagged_count"]
        }
        for loc, data in room_totals.items()
    }

    return {
        "room_score": room_score,
        "room_flags": room_flags,
        "room_totals": room_totals_clean
    }


def calculate_comprehensive_score(
    rows: List[Dict],
    purchase_match_results: List[Dict] = None,
    gl_code_key: str = None
) -> Dict[str, Any]:
    """
    Calculate comprehensive unit score combining health + purchase match flags.

    Args:
        rows: Inventory row dicts
        purchase_match_results: Optional results from purchase match system
            Each result should have: {sku, flag, reason}
            where flag is: CLEAN, LIKELY_TYPO, UNKNOWN, ORDERABLE, IGNORED
        gl_code_key: Optional GL Code column key

    Returns:
        Full scoring result with item flags, room flags, and combined metrics
    """
    # Start with basic health scoring
    result = calculate_unit_score(rows, gl_code_key)

    # If we have purchase match results, integrate them
    if purchase_match_results:
        # Create lookup by SKU
        pm_lookup = {}
        for pm in purchase_match_results:
            sku = pm.get("sku", "").upper().strip()
            if sku:
                pm_lookup[sku] = pm

        # Add purchase match flags to items
        additional_score = 0
        for row in rows:
            # Find SKU in row
            sku = ""
            item_desc = ""
            for key, value in row.items():
                key_lower = key.lower() if isinstance(key, str) else ""
                if "dist" in key_lower or "sku" in key_lower or key_lower == "item #":
                    sku = str(value).upper().strip() if value else ""
                elif "description" in key_lower:
                    item_desc = str(value) if value else ""

            if not sku:
                continue

            pm = pm_lookup.get(sku)
            if not pm:
                continue

            flag = pm.get("flag", "")

            # Score based on purchase match flag
            if flag == "LIKELY_TYPO":
                additional_score += 2
                result["item_flags"].append({
                    "item": item_desc or sku,
                    "qty": 0,
                    "uom": "",
                    "total": 0,
                    "flags": ["sku_mismatch"],
                    "points": 2,
                    "location": "Unknown",
                    "purchase_match": {
                        "flag": flag,
                        "reason": pm.get("reason", ""),
                        "suggestion": pm.get("suggestion")
                    }
                })
            elif flag == "UNKNOWN":
                additional_score += 1
                result["item_flags"].append({
                    "item": item_desc or sku,
                    "qty": 0,
                    "uom": "",
                    "total": 0,
                    "flags": ["unknown_sku"],
                    "points": 1,
                    "location": "Unknown",
                    "purchase_match": {
                        "flag": flag,
                        "reason": pm.get("reason", "")
                    }
                })

        # Update totals
        result["score"] += additional_score
        result["status"] = get_status_from_score(result["score"])
        result["summary"]["flagged_items"] = len(result["item_flags"])

        # Re-sort by points
        result["item_flags"].sort(key=lambda x: x["points"], reverse=True)

    return result
