# SPEC-007: Purchase Match Diagnostic

## Problem Statement

Inventory items get coded with wrong SKUs—stuff that's conceptually the same as what was purchased but entered differently. This creates two problems:

1. **Valuation drift:** Same item at different SKUs fragments cost tracking
2. **Ordering history gaps:** Can't see true consumption patterns when items scatter across SKUs

The core insight: **If it wasn't purchased in the last N months, it shouldn't be on the count without explanation.**

## Solution Approach

A diagnostic tab that compares inventory against purchase history (the "canon") and flags mismatches. No workflow, no resolution tracking—just surfaces the weird stuff so humans can investigate.

**Kitchen analogy:** This is like a receiving clerk who knows every invoice from the last 3 months. When they see something in the walk-in that doesn't match any delivery, they flag it: "Where did this come from?"

### Matching Logic

The matching uses SKU as primary key, with price + vendor as fallback signal:

| Condition | Flag | Meaning |
|-----------|------|---------|
| SKU exists in purchase history | CLEAN | No action needed |
| SKU missing, price AND vendor match a purchased item | SKU_MISMATCH | "Did you mean [suggested SKU]?" |
| SKU missing, vendor not in unit's approved list | ORPHAN | Wrong vendor entirely |
| SKU missing, no price match within approved vendors | ORPHAN | Needs investigation |

**Why price works:** Descriptions lie ("TOMATO DICED #10" vs "DICED TOMATOES #10 CAN"), but $47.82 matching $47.82 is a strong signal. Combined with vendor constraint, it's reliable enough for suggestions.

**Why vendor constraint matters:** Don't suggest a Sysco item to a unit that orders from Gordon Food Service. Even if prices match, cross-vendor suggestions create confusion.

## Components

### 1. Purchase Canon Loader
**Purpose:** Ingest OrderMaestro IPS exports into a queryable structure

**Why it exists:** The IPS export is the source of truth for "what was actually purchased." Multi-month files get merged into a single canon. This is the dataset we validate inventory against.

**Input:** XLSX files from OrderMaestro (structure documented below)
**Output:** Normalized purchase records with SKU, vendor, price as key fields

### 2. Unit-Vendor Config
**Purpose:** Declarative mapping of which vendors serve which units

**Why it exists:** Prevents cross-vendor suggestions and catches anomalies (Sysco item appearing at a Gordon-only site). Set once, referenced by all diagnostics.

```json
{
  "units": {
    "PSEG_HQ": {
      "name": "PSEG Headquarters",
      "vendors": ["sysco", "vistar", "pepsi", "coca_cola", "kegels_produce", "penn_del_baking"]
    },
    "LOCKHEED": {
      "name": "Lockheed Martin", 
      "vendors": ["gordon_food_service", "pepsi", "coca_cola", "farmer_brothers"]
    }
  },
  "vendor_aliases": {
    "sysco": ["Sysco Corporation", "SYSCO"],
    "gordon_food_service": ["Gordon Food Service US", "GFS"],
    "vistar": ["Vistar Corporation"],
    "pepsi": ["Pepsi", "PepsiCo"],
    "coca_cola": ["Coca Cola", "Coke"],
    "farmer_brothers": ["Farmer Brothers Co"],
    "kegels_produce": ["Kegel's Produce"],
    "penn_del_baking": ["Penn-Del Baking"]
  }
}
```

### 3. Inventory Adapter
**Purpose:** Bridge to existing ops dashboard inventory data

**Why it exists:** Inventory is already in Nebula with unit context. This adapter exposes it in the format the matcher needs. No new data import—just a query interface.

**Output:** Inventory records with SKU, unit, vendor (if available), price/value

### 4. Purchase Matcher
**Purpose:** Core comparison engine

**Why it exists:** This is the brain. Takes inventory items, checks against canon, applies vendor constraints, generates flags.

**Logic flow:**
```
For each inventory item:
  1. Look up SKU in purchase canon
     → Found? Mark CLEAN, done
  
  2. Check if item's vendor is in unit's approved list
     → Not approved? Mark ORPHAN (wrong vendor), done
  
  3. Search canon for price match within approved vendors
     → Found? Mark SKU_MISMATCH, attach suggestion
     → Not found? Mark ORPHAN (unknown item)
```

### 5. Diagnostic Report Generator
**Purpose:** Format results for human consumption

**Why it exists:** Raw flags aren't actionable. Group by unit, sort by flag type (SKU_MISMATCH first—quick wins), include enough context to investigate.

## Data Flow

```
┌─────────────────────┐     ┌─────────────────────┐
│  OrderMaestro IPS   │     │   Ops Dashboard     │
│  (XLSX exports)     │     │   (existing)        │
└─────────┬───────────┘     └──────────┬──────────┘
          │                            │
          ▼                            ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Purchase Canon     │     │  Inventory Adapter  │
│  Loader             │     │                     │
└─────────┬───────────┘     └──────────┬──────────┘
          │                            │
          │    ┌───────────────────┐   │
          │    │ Unit-Vendor       │   │
          │    │ Config            │   │
          │    └─────────┬─────────┘   │
          │              │             │
          ▼              ▼             ▼
       ┌──────────────────────────────────┐
       │       Purchase Matcher           │
       │  (SKU lookup → Price fallback)   │
       └───────────────┬──────────────────┘
                       │
                       ▼
       ┌──────────────────────────────────┐
       │    Diagnostic Report Generator   │
       └───────────────┬──────────────────┘
                       │
                       ▼
              Flags by Unit (CSV/Display)
```

## Data Structures

### OrderMaestro IPS Format (Input)
Source: `Purchasing Details Raw Data` sheet, row 10 = headers, data starts row 11

| Column | Field | Use |
|--------|-------|-----|
| B | Distributor | Vendor name (normalize via aliases) |
| D | Item Number | SKU (primary match key) |
| E | Description | Display only |
| H | Brand | Display context |
| I | Unit of Measure | Display context |
| J | Pack | Display context |
| N | Invoiced Item Price | Price signal for fuzzy match |

### Purchase Canon Record (Internal)
```python
@dataclass
class PurchaseRecord:
    sku: str                 # Item Number
    vendor: str              # Normalized vendor key
    vendor_raw: str          # Original distributor name
    price: Decimal           # Invoiced Item Price
    description: str         # For display
    brand: str | None
    uom: str | None
    pack: str | None
```

### Inventory Record (From Adapter)
```python
@dataclass  
class InventoryRecord:
    sku: str
    unit: str                # Which location
    vendor: str | None       # If known from inventory system
    price: Decimal | None    # Current valuation price
    description: str
    quantity: Decimal
```

### Match Result (Output)
```python
@dataclass
class MatchResult:
    inventory_item: InventoryRecord
    flag: Literal["CLEAN", "SKU_MISMATCH", "ORPHAN"]
    suggested_match: PurchaseRecord | None  # Only for SKU_MISMATCH
    reason: str                              # Human-readable explanation
```

## Configuration

### Price Match Tolerance
Default: Exact match (±$0.00)
Configurable: Allow small variance for price fluctuations

```json
{
  "price_match_tolerance_percent": 0,
  "price_match_tolerance_absolute": 0.00
}
```

**Rationale:** Start strict. Loosen if too many false negatives in practice.

### Lookback Period
Default: 3 months
Configurable: Per-run parameter

**Rationale:** Long enough to catch seasonal items, short enough that ancient purchases don't pollute suggestions.

## Output Format

### Console/Display
```
UNIT: PSEG HQ
══════════════════════════════════════════════════════════════════════

SKU MISMATCHES (3) - Quick fixes, likely just miscoded
──────────────────────────────────────────────────────────────────────
COUNT ITEM                    PRICE     SUGGESTED MATCH
TOMATO DICED 12345           $47.82    → TOMATO DICE #10 (SKU 67890)
MILK 2% 99999                 $4.29    → 2% MILK GAL (SKU 11111)
CHIX BRST BNLS 88888        $89.50    → CHICKEN BREAST B/S (SKU 22222)

ORPHANS (2) - Needs investigation
──────────────────────────────────────────────────────────────────────
COUNT ITEM                    PRICE     VENDOR          NOTES
MYSTERY SAUCE                $12.50    Unknown         No price match
SYSCO BEEF TENDER            $89.00    Sysco           Vendor not approved for unit
```

### CSV Export
```csv
unit,flag,inventory_sku,inventory_desc,inventory_price,suggested_sku,suggested_desc,suggested_price,reason
PSEG_HQ,SKU_MISMATCH,12345,TOMATO DICED,47.82,67890,TOMATO DICE #10,47.82,Price match found
PSEG_HQ,ORPHAN,99999,MYSTERY SAUCE,12.50,,,No price match in approved vendors
```

## Success Criteria

| Criteria | Target |
|----------|--------|
| Parse 3-month IPS export | < 5 seconds |
| Match 500 inventory items | < 2 seconds |
| False positive rate (bad suggestions) | < 10% |
| Coverage (items that should flag, do flag) | > 95% |
| Zero cross-vendor suggestions | 100% |

## Constraints

- **Completely siloed from Unit Health** — own module, own config, no shared dependencies
- **No workflow** — surfaces problems, doesn't track resolution
- **No persistence** — runs on-demand, results are ephemeral
- **Offline capable** — once canon is loaded, no network needed

## Open Questions

1. **Inventory adapter interface:** What's the current query pattern for inventory in ops dashboard? Need exact field names and access method.

2. **Multi-price scenarios:** If same SKU was purchased at different prices across the period (price increases), which price do we use for matching? Options:
   - Most recent price
   - Average price
   - Any price in range (loosest)

3. **Partial SKU matches:** Should we flag when inventory SKU is a substring of purchase SKU (or vice versa)? Could catch typos like "1234" vs "12345".

4. **Report delivery:** In-app tab only, or also scheduled email digest?

---

*SPEC-007 | Purchase Match Diagnostic | v1.0 | January 2026*
