# TASKS.md — SPEC-007: Purchase Match Diagnostic

## Current Sprint: Purchase Match Diagnostic (Siloed Module)

**Constraint:** This module is completely independent. No imports from Unit Health, no shared state. Own directory, own config, own tests.

---

### Task 1: Create Module Structure

**Goal:** Establish isolated directory structure for purchase match diagnostic

**Why:** Clean separation prevents coupling. This module could be extracted or replaced without touching anything else.

**Inputs:** None
**Outputs:** Directory structure:
```
nebula/
└── purchase_match/
    ├── __init__.py
    ├── config.py          # Unit-vendor mappings, tolerances
    ├── canon_loader.py    # IPS file parser
    ├── matcher.py         # Core matching logic
    ├── report.py          # Output formatting
    ├── models.py          # Data classes
    └── tests/
        ├── __init__.py
        ├── test_canon_loader.py
        ├── test_matcher.py
        └── fixtures/
            └── sample_ips.xlsx
```

**Test:** `from nebula.purchase_match import *` succeeds with no import errors

---

### Task 2: Define Data Models

**Goal:** Create dataclasses for all internal structures

**Why:** Type hints catch bugs early. Dataclasses give us `__eq__`, `__repr__` for free.

**Inputs:** SPEC-007 data structure definitions
**Outputs:** `models.py` with:
- `PurchaseRecord` — single item from canon
- `InventoryRecord` — single item from inventory
- `MatchResult` — output of matcher with flag and suggestion
- `MatchFlag` — enum: CLEAN, SKU_MISMATCH, ORPHAN

**Test:** 
```python
from nebula.purchase_match.models import PurchaseRecord, MatchFlag
record = PurchaseRecord(sku="12345", vendor="sysco", ...)
assert record.sku == "12345"
assert MatchFlag.SKU_MISMATCH.value == "SKU_MISMATCH"
```

---

### Task 3: Build Unit-Vendor Config

**Goal:** Create config loader and sample configuration

**Why:** Declarative config means adding a new unit is editing JSON, not code. Vendor aliases handle the messy reality of inconsistent naming in source data.

**Inputs:** Vendor names from IPS files (see SPEC-007)
**Outputs:** 
- `config.py` with `load_unit_vendor_config()` function
- `unit_vendor_config.json` sample file
- Functions: `get_approved_vendors(unit)`, `normalize_vendor(raw_name)`

**Test:**
```python
config = load_unit_vendor_config("unit_vendor_config.json")
assert "sysco" in get_approved_vendors("PSEG_HQ", config)
assert normalize_vendor("Sysco Corporation", config) == "sysco"
assert normalize_vendor("Gordon Food Service US", config) == "gordon_food_service"
```

---

### Task 4: Build Canon Loader

**Goal:** Parse OrderMaestro IPS exports into PurchaseRecord list

**Why:** This is the "source of truth" we validate against. Loader handles the messy XLSX structure (headers on row 10, data starts row 11, encoded column names in some exports).

**Inputs:** XLSX file path(s)
**Outputs:** `List[PurchaseRecord]`

**Implementation notes:**
- Use `openpyxl` for XLSX parsing
- Handle both clean headers ("Item Number") and encoded ("Item_x0020_Number")
- Skip rows where Item Number is empty
- Normalize vendor names using config aliases
- Parse price as Decimal, not float (money precision)

**Test:**
```python
from nebula.purchase_match.canon_loader import load_canon
from decimal import Decimal

records = load_canon(["October_IPS.xlsx", "November_IPS.xlsx", "December_IPS.xlsx"], config)
assert len(records) > 0
assert all(isinstance(r.price, Decimal) for r in records)
assert all(r.vendor in config.vendor_aliases.keys() for r in records)

# Spot check known item from sample file
sysco_items = [r for r in records if r.vendor == "sysco"]
assert len(sysco_items) > 0
```

---

### Task 5: Build Canon Index

**Goal:** Create fast lookup structures for matching

**Why:** Linear search through 3000 purchase records per inventory item is O(n*m). Indexes make it O(n).

**Inputs:** `List[PurchaseRecord]`
**Outputs:** `CanonIndex` class with:
- `by_sku: Dict[str, PurchaseRecord]` — exact SKU lookup
- `by_vendor_price: Dict[tuple[str, Decimal], List[PurchaseRecord]]` — for price+vendor fallback

**Implementation notes:**
- SKU index is simple dict (last write wins if duplicates)
- Price index keys on (vendor, price) tuple
- Multiple items can have same vendor+price, so value is list

**Test:**
```python
from nebula.purchase_match.canon_loader import load_canon, build_index

records = load_canon(files, config)
index = build_index(records)

# Exact SKU lookup
assert index.by_sku.get("117377") is not None

# Price lookup returns list
matches = index.by_vendor_price.get(("sysco", Decimal("47.82")), [])
assert isinstance(matches, list)
```

---

### Task 6: Build Inventory Adapter Interface

**Goal:** Define abstract interface for inventory data access

**Why:** The actual inventory lives in ops dashboard. This adapter pattern lets us swap implementations (mock for testing, real for production) without changing matcher logic.

**Inputs:** None (interface definition)
**Outputs:** `InventoryAdapter` abstract base class with:
- `get_inventory_for_unit(unit: str) -> List[InventoryRecord]`

**Test:** N/A (interface only, tested via implementations)

---

### Task 7: Build Mock Inventory Adapter

**Goal:** Create test implementation that loads from CSV/JSON

**Why:** Can't test matcher without inventory data. Mock adapter lets us control test scenarios precisely.

**Inputs:** CSV or JSON file with inventory records
**Outputs:** `MockInventoryAdapter` class implementing `InventoryAdapter`

**Test:**
```python
adapter = MockInventoryAdapter("test_inventory.csv")
items = adapter.get_inventory_for_unit("PSEG_HQ")
assert len(items) > 0
assert all(item.unit == "PSEG_HQ" for item in items)
```

---

### Task 8: Build Core Matcher

**Goal:** Implement the matching algorithm

**Why:** This is the brain of the diagnostic. Clean separation from I/O means it's testable and portable.

**Inputs:** 
- `CanonIndex` — purchase history lookup
- `List[InventoryRecord]` — items to validate  
- `UnitVendorConfig` — approved vendors per unit

**Outputs:** `List[MatchResult]`

**Algorithm:**
```python
def match_inventory(inventory: List[InventoryRecord], 
                    index: CanonIndex,
                    config: UnitVendorConfig) -> List[MatchResult]:
    results = []
    for item in inventory:
        # Step 1: Exact SKU match
        if item.sku in index.by_sku:
            results.append(MatchResult(item, MatchFlag.CLEAN, None, "SKU found in purchase history"))
            continue
        
        # Step 2: Check vendor approval
        approved = get_approved_vendors(item.unit, config)
        if item.vendor and normalize_vendor(item.vendor, config) not in approved:
            results.append(MatchResult(item, MatchFlag.ORPHAN, None, 
                           f"Vendor {item.vendor} not approved for {item.unit}"))
            continue
        
        # Step 3: Price+vendor fallback
        if item.price:
            for vendor in approved:
                matches = index.by_vendor_price.get((vendor, item.price), [])
                if matches:
                    # Take first match as suggestion
                    results.append(MatchResult(item, MatchFlag.SKU_MISMATCH, matches[0],
                                   f"Price ${item.price} matches {matches[0].sku}"))
                    break
            else:
                results.append(MatchResult(item, MatchFlag.ORPHAN, None,
                               "No SKU or price match found"))
        else:
            results.append(MatchResult(item, MatchFlag.ORPHAN, None,
                           "No SKU match and no price to search"))
    
    return results
```

**Test:**
```python
# Setup
index = build_index([
    PurchaseRecord(sku="12345", vendor="sysco", price=Decimal("47.82"), ...),
    PurchaseRecord(sku="67890", vendor="sysco", price=Decimal("23.50"), ...),
])
config = load_test_config()  # PSEG_HQ approves sysco

# Test CLEAN
item_clean = InventoryRecord(sku="12345", unit="PSEG_HQ", ...)
results = match_inventory([item_clean], index, config)
assert results[0].flag == MatchFlag.CLEAN

# Test SKU_MISMATCH (wrong SKU, price matches)
item_mismatch = InventoryRecord(sku="99999", unit="PSEG_HQ", price=Decimal("47.82"), ...)
results = match_inventory([item_mismatch], index, config)
assert results[0].flag == MatchFlag.SKU_MISMATCH
assert results[0].suggested_match.sku == "12345"

# Test ORPHAN (wrong vendor)
item_wrong_vendor = InventoryRecord(sku="XXXXX", unit="PSEG_HQ", vendor="gordon_food_service", ...)
results = match_inventory([item_wrong_vendor], index, config)
assert results[0].flag == MatchFlag.ORPHAN
assert "not approved" in results[0].reason
```

---

### Task 9: Build Report Generator

**Goal:** Format MatchResults for human consumption

**Why:** Raw data isn't actionable. Good formatting makes triage fast.

**Inputs:** `List[MatchResult]`
**Outputs:** 
- Formatted console output (grouped by unit, then by flag type)
- CSV export

**Implementation notes:**
- Sort: SKU_MISMATCH first (quick wins), then ORPHAN
- Group by unit
- Console: use box-drawing characters for visual hierarchy
- CSV: flat structure for spreadsheet analysis

**Test:**
```python
from nebula.purchase_match.report import format_console, export_csv

results = [...]  # Mix of flags
console_output = format_console(results)
assert "SKU MISMATCHES" in console_output
assert "ORPHANS" in console_output

csv_output = export_csv(results)
assert "unit,flag,inventory_sku" in csv_output
```

---

### Task 10: Build CLI Entry Point

**Goal:** Command-line interface for running diagnostics

**Why:** Ops team needs to run this without touching code. CLI makes it scriptable.

**Inputs:** 
- IPS file paths (required)
- Unit to validate (required)
- Config path (optional, default)
- Output format (optional: console, csv, both)

**Outputs:** Formatted report to stdout or file

**Usage:**
```bash
# Basic usage
python -m nebula.purchase_match \
  --ips October_IPS.xlsx November_IPS.xlsx December_IPS.xlsx \
  --unit PSEG_HQ

# With CSV export
python -m nebula.purchase_match \
  --ips *.xlsx \
  --unit PSEG_HQ \
  --output-csv results.csv

# Custom config
python -m nebula.purchase_match \
  --ips *.xlsx \
  --unit LOCKHEED \
  --config custom_unit_vendors.json
```

**Test:** Manual CLI testing with sample files

---

### Task 11: Integration Test with Real Data

**Goal:** End-to-end test with actual IPS exports

**Why:** Unit tests prove components work. Integration test proves they work together with real-world messy data.

**Inputs:** October/November/December IPS files from uploads
**Outputs:** Passing test that loads all files, runs matcher, produces valid output

**Test:**
```python
def test_full_pipeline():
    config = load_unit_vendor_config("unit_vendor_config.json")
    
    # Load 3 months of purchases
    records = load_canon([
        "October_IPS.xlsx",
        "November_IPS.xlsx", 
        "December_IPS.xlsx"
    ], config)
    assert len(records) > 2000  # Sanity check
    
    index = build_index(records)
    
    # Create mock inventory with known scenarios
    inventory = [
        InventoryRecord(sku="117377", ...),  # Should be CLEAN (exists in canon)
        InventoryRecord(sku="FAKE123", price=Decimal("175.65"), ...),  # Should be SKU_MISMATCH
        InventoryRecord(sku="NOPE", price=Decimal("9999.99"), ...),  # Should be ORPHAN
    ]
    
    results = match_inventory(inventory, index, config)
    
    assert results[0].flag == MatchFlag.CLEAN
    assert results[1].flag == MatchFlag.SKU_MISMATCH
    assert results[2].flag == MatchFlag.ORPHAN
```

---

### Task 12: Connect to Ops Dashboard (Placeholder)

**Goal:** Stub out the real inventory adapter

**Why:** Mock adapter proves the logic. Real adapter needs ops dashboard interface details. Create the stub now, implement when integration point is clear.

**Inputs:** TBD — depends on ops dashboard query interface
**Outputs:** `OpsDashboardInventoryAdapter` class (stubbed)

**Implementation notes:**
- Raise `NotImplementedError` with clear message about what's needed
- Document expected interface in docstring

```python
class OpsDashboardInventoryAdapter(InventoryAdapter):
    """
    Production adapter for ops dashboard inventory.
    
    TODO: Implement once ops dashboard query interface is documented.
    Expected to query existing inventory valuations by unit.
    """
    
    def get_inventory_for_unit(self, unit: str) -> List[InventoryRecord]:
        raise NotImplementedError(
            "Ops dashboard integration pending. "
            "Need: query interface, field mapping, auth method."
        )
```

---

## Definition of Done

- [ ] All tasks complete with passing tests
- [ ] No imports from other Nebula modules (verify with `grep -r "from nebula\." purchase_match/`)
- [ ] CLI runs successfully with sample IPS files
- [ ] Config file documents all known units and vendors
- [ ] README in module directory explains usage

---

## Future Tasks (Post-MVP)

- **Task 13:** Real ops dashboard adapter implementation
- **Task 14:** Scheduled runs with email digest
- **Task 15:** Web UI tab in ops dashboard
- **Task 16:** Price tolerance configuration (handle price fluctuations)
- **Task 17:** Partial SKU matching (catch typos)

---

*TASKS.md | SPEC-007 | v1.0*
