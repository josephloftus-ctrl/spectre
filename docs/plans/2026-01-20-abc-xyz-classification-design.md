# ABC-XYZ Classification Design

**Date:** 2026-01-20
**Status:** Approved
**Scope:** Spectre (backend) + Steady (iOS)

---

## Overview

Add ABC-XYZ inventory classification to categorize items by value (ABC) and demand variability (XYZ). Classifications are computed in Spectre and synced to Steady for display during counts.

### Goals

1. Classify items by value contribution (ABC) and demand stability (XYZ)
2. Weight health scores by ABC class (A errors matter more than C errors)
3. Display ABC badges in Steady during counts
4. Sort count lists by ABC priority (A items first)

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Where classifications live | Both Spectre + Steady | Spectre computes, Steady displays during counts |
| ABC calculation | Total inventory value | Simple, uses existing snapshot data |
| XYZ calculation | Coefficient of variation on weekly quantities | Directly measures demand unpredictability |
| Minimum data requirement | 4 weeks | Enough for meaningful stats, not too slow for new items |
| Steady display | Badge + sort priority | A items appear first, simple "A/B/C" badge |
| Health score integration | Weight flags by ABC | 1.5x for A, 1.0x for B, 0.5x for C |
| Storage | New `item_classifications` table | Persist independently from snapshots |
| Refresh trigger | On every inventory upload | Always current, not expensive to compute |

---

## Data Model

### New Table: `item_classifications`

```sql
CREATE TABLE item_classifications (
    id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    abc_class TEXT,           -- 'A', 'B', 'C', or NULL (unclassified)
    xyz_class TEXT,           -- 'X', 'Y', 'Z', or NULL
    combined_class TEXT,      -- 'AX', 'BY', 'CZ', etc. (for queries)
    total_value REAL,         -- latest inventory value (ABC input)
    avg_quantity REAL,        -- average qty over period
    cv_score REAL,            -- coefficient of variation (XYZ input)
    weeks_of_data INTEGER,    -- how many weeks used in calculation
    last_calculated TEXT,     -- ISO timestamp
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, sku)
);

CREATE INDEX idx_classifications_site ON item_classifications(site_id);
CREATE INDEX idx_classifications_abc ON item_classifications(abc_class);
CREATE INDEX idx_classifications_combined ON item_classifications(combined_class);
```

### Classification Thresholds

```python
# ABC thresholds (cumulative % of total value)
ABC_THRESHOLDS = {
    'A': 0.80,  # Top 80% of value
    'B': 0.95,  # Next 15% of value
    'C': 1.00   # Bottom 5% of value
}

# XYZ thresholds (coefficient of variation)
XYZ_THRESHOLDS = {
    'X': 0.25,  # CV < 0.25 (stable)
    'Y': 0.50,  # CV 0.25-0.50 (moderate)
    'Z': 1.00   # CV > 0.50 (unpredictable)
}

MIN_WEEKS_FOR_CLASSIFICATION = 4
```

---

## Classification Algorithm

### ABC Calculation

```python
def calculate_abc_classification(site_id: str) -> dict[str, str]:
    """
    Calculate ABC class for all items at a site.

    Algorithm:
    1. Get latest inventory snapshot for site
    2. Sort items by total_value descending
    3. Calculate cumulative % of total value
    4. Assign A/B/C based on cumulative thresholds

    Returns: {sku: 'A'|'B'|'C'}
    """
    items = get_latest_item_values(site_id)
    sorted_items = sorted(items, key=lambda x: x['total_value'], reverse=True)

    total = sum(i['total_value'] for i in sorted_items)
    if total == 0:
        return {}

    cumulative = 0
    classifications = {}

    for item in sorted_items:
        cumulative += item['total_value']
        pct = cumulative / total

        if pct <= ABC_THRESHOLDS['A']:
            classifications[item['sku']] = 'A'
        elif pct <= ABC_THRESHOLDS['B']:
            classifications[item['sku']] = 'B'
        else:
            classifications[item['sku']] = 'C'

    return classifications
```

### XYZ Calculation

```python
def calculate_xyz_classification(site_id: str) -> dict[str, tuple[str, float]]:
    """
    Calculate XYZ class for all items at a site.

    Algorithm:
    1. Get weekly quantities from inventory_item_history
    2. For items with >= 4 weeks of data:
       - Calculate mean and std dev of quantities
       - CV = std_dev / mean (coefficient of variation)
    3. Assign X/Y/Z based on CV thresholds

    Returns: {sku: ('X'|'Y'|'Z', cv_score)} or {sku: (None, None)} if insufficient data
    """
    history = get_item_quantity_history(site_id, weeks=12)
    classifications = {}

    for sku, weekly_quantities in history.items():
        if len(weekly_quantities) < MIN_WEEKS_FOR_CLASSIFICATION:
            classifications[sku] = (None, None)
            continue

        mean = statistics.mean(weekly_quantities)
        if mean == 0:
            classifications[sku] = ('Z', 1.0)
            continue

        std_dev = statistics.stdev(weekly_quantities)
        cv = std_dev / mean

        if cv < XYZ_THRESHOLDS['X']:
            classifications[sku] = ('X', cv)
        elif cv < XYZ_THRESHOLDS['Y']:
            classifications[sku] = ('Y', cv)
        else:
            classifications[sku] = ('Z', cv)

    return classifications
```

### Refresh Function

```python
def refresh_classifications(site_id: str) -> int:
    """
    Recalculate and store all classifications for a site.
    Called after inventory upload completes.

    Returns: number of items classified
    """
    abc = calculate_abc_classification(site_id)
    xyz = calculate_xyz_classification(site_id)

    all_skus = set(abc.keys()) | set(xyz.keys())
    count = 0

    for sku in all_skus:
        abc_class = abc.get(sku)
        xyz_class, cv_score = xyz.get(sku, (None, None))
        combined = f"{abc_class or ''}{xyz_class or ''}" or None

        upsert_classification(
            site_id=site_id,
            sku=sku,
            abc_class=abc_class,
            xyz_class=xyz_class,
            combined_class=combined,
            cv_score=cv_score
        )
        count += 1

    return count
```

---

## Health Score Integration

### ABC Multipliers

```python
ABC_SCORE_MULTIPLIERS = {
    'A': 1.5,  # A items: flags count 50% more
    'B': 1.0,  # B items: unchanged
    'C': 0.5,  # C items: flags count 50% less
    None: 1.0  # Unclassified: unchanged
}
```

### Modified Scoring

```python
def score_item(row: dict, abc_multiplier: float = 1.0) -> tuple[int, list[str]]:
    """
    Score a single inventory item and return flags.
    NOW ACCEPTS abc_multiplier to weight the score.
    """
    points = 0
    flags = []

    # ... existing key extraction ...

    # UOM Error: Qty >= 10 AND UOM contains "CS"
    if qty is not None and qty >= 10 and uom in ("CS", "CASE", "CSE"):
        if not is_beverage(item_desc):
            base_points = 3
            points += int(base_points * abc_multiplier)
            flags.append("uom_error")

    # Big Dollar: Total > $250
    if total is not None and total > 250:
        if not is_beverage(item_desc):
            base_points = 1
            points += int(base_points * abc_multiplier)
            flags.append("big_dollar")

    return points, flags
```

### Scoring Examples

| Item | Base Points | ABC Class | Multiplier | Final Points |
|------|-------------|-----------|------------|--------------|
| Chicken breast (10 CS, $400) | 4 | A | 1.5x | 6 |
| Paper towels (12 CS, $180) | 3 | C | 0.5x | 1 |
| Olive oil (8 CS, $300) | 1 | B | 1.0x | 1 |

---

## API Endpoints

### New Router: `/api/classifications`

```python
@router.get("/{site_id}")
def get_site_classifications(site_id: str):
    """Get all item classifications for a site (used by Steady sync)."""
    return {
        "site_id": site_id,
        "items": [
            {"sku": "12345", "abc_class": "A", "xyz_class": "X", ...},
        ],
        "summary": {"a_count": 45, "b_count": 120, "c_count": 380},
        "last_calculated": "2026-01-20T15:30:00Z"
    }

@router.get("/{site_id}/summary")
def get_classification_summary(site_id: str):
    """Get classification distribution for dashboard display."""
    return {
        "abc_distribution": {...},
        "xyz_distribution": {...},
        "nine_box": {"AX": 30, "AY": 10, ...}
    }

@router.post("/{site_id}/refresh")
def refresh_site_classifications(site_id: str):
    """Manually trigger classification recalculation."""

@router.get("/{site_id}/items")
def get_classified_items(site_id: str, abc_class: str = None, ...):
    """Get items with optional filtering by classification."""
```

---

## Steady Integration

### API Model

```swift
struct ItemClassification: Codable {
    let sku: String
    let abcClass: String?
    let xyzClass: String?
    let combinedClass: String?
    let weeksOfData: Int
}
```

### Local Storage

```swift
@Model
class ZCItemClassification {
    var sku: String
    var siteId: String
    var abcClass: String?
    var lastSynced: Date
}
```

### Sync Triggers

- On app launch (if stale > 1 hour)
- When entering a site's zone list
- After completing a count session

### UI Display

**Badge Component:**
```swift
struct ABCBadge: View {
    let classification: String

    var backgroundColor: Color {
        switch classification {
        case "A": return .red.opacity(0.8)
        case "B": return .orange.opacity(0.8)
        case "C": return .gray.opacity(0.6)
        default: return .clear
        }
    }
}
```

**Sort Order:** A items first, then B, then C, then unclassified. Alphabetical within each class.

---

## Implementation Plan

### Files to Create

| File | Purpose |
|------|---------|
| `backend/core/classifier.py` | ABC-XYZ calculation engine |
| `backend/api/routers/classifications.py` | REST API endpoints |
| `Steady/Models/API/ClassificationResponse.swift` | API response model |
| `Steady/Models/ZCItemClassification.swift` | Local SwiftData model |
| `Steady/Features/ZoneCount/Components/ABCBadge.swift` | Badge UI component |

### Files to Modify

| File | Changes |
|------|---------|
| `backend/core/db/base.py` | Add `item_classifications` table |
| `backend/core/database.py` | Add CRUD functions for classifications |
| `backend/core/flag_checker.py` | Add ABC multiplier to scoring |
| `backend/core/worker.py` | Trigger classification refresh after file processing |
| `backend/api/main.py` | Register classifications router |
| `Steady/Services/SteadyAPI.swift` | Add `syncClassifications()` |
| `Steady/Features/ZoneCount/ZoneCountView.swift` | Sort by ABC, display badges |
| `Steady/Features/ZoneCount/Components/CountItemRow.swift` | Add badge display |

### Execution Order

1. Add database table and migration
2. Create classifier.py with calculation logic
3. Add database CRUD functions
4. Create API router
5. Integrate with flag_checker.py scoring
6. Add trigger in worker.py after file processing
7. Implement Steady API model and sync
8. Add Steady UI components
9. Test end-to-end

---

## Code Quality Notes (from review)

Issues identified during design that should be addressed:

1. **flag_checker.py** - Duplicated key extraction logic in `score_item()` and `calculate_unit_score()` (lines 109-131 vs 204-229). Consider extracting to helper.

2. **flag_checker.py** - `calculate_comprehensive_score()` loses location info for purchase match items (hardcodes "Unknown" at line 467).

3. **history.py** - `get_items()` helper duplicated between `/movers` and `/anomalies` endpoints (lines 86-106 vs 160-182). Should extract to shared function.

4. **flag_checker.py** - Hardcoded thresholds ($250, $1000, $200) could be moved to config.
