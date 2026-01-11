"""
Flag Checker Module - Unit Health Scoring System

Scoring rules:
- Item-level flags:
  - UOM Error (High Case Count): Qty >= 10 AND UOM = "CS" → 3 pts
  - Big Dollar: Total Price > $250 → 1 pt

Higher score = worse health. Units sorted worst-first.
"""

import re
from typing import Optional


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

    return {
        "score": total_score,
        "status": get_status_from_score(total_score),
        "item_flags": item_flags,
        "summary": {
            "total_value": round(total_value, 2),
            "item_count": len(rows),
            "flagged_items": len(item_flags)
        }
    }
