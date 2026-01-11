# SPEC: Ops-dash Unit Scoring System

## Context

Joseph is Area Support Chef for CulinArt (Compass Group B&I). He's been tasked by his District Manager Ken to review inventory valuations across multiple units weekly. The Ops-dash already exists and can:

- Watch a folder for incoming OrderMaestro valuation exports
- Ingest and parse xlsx files
- Display inventory data
- Compare valuations across time

What's missing is a **unit health scoring system** that lets Joseph see at a glance which units have problems and which are clean—sorted from worst to best.

---

## The Scoring System

### Purpose

Generate a numerical score per unit where **higher = worse**. Units display in descending order (worst at top, cleanest at bottom).

---

## Flag Types & Weights

### Item-Level Flags

These are applied per line item in a valuation:

| Flag | Condition | Points | Rationale |
|------|-----------|--------|-----------|
| **UOM Error (High Case Count)** | Quantity ≥ 10 AND UOM = "CS" | **3** | High confidence error. Nobody has 14 cases of sausage patties. Almost always eaches entered as cases. |
| **Big Dollar** | Total Price > $250 | **1** | Needs a look but might be legit. Proteins, dairy, beverages can legitimately hit this. |

If an item triggers BOTH flags (10+ CS AND >$250), it scores **4 points** (3+1).

### Room-Level Flags

These are applied per storage location within a unit:

| Flag | Condition | Points | Rationale |
|------|-----------|--------|-----------|
| **Low Room - Dedicated Storage** | Room total < $1,000 AND room is a dedicated storage area | **2** | Walk-ins, freezers, dry storage should have significant inventory. Under $1k is suspiciously low—either bad count or empty shelves. |
| **Low Room - Other** | Room total < $200 AND room is NOT dedicated storage | **2** | Front of house, line storage, etc. Should have at least some inventory. Under $200 suggests incomplete count. |

### Dedicated Storage Areas (match these strings, case-insensitive)

- Walk-in Cooler / Walk In Cooler
- Freezer
- Dry Storage (Food or Supplies)
- Beverage Room
- Chemical Locker

### Non-Dedicated Storage Areas (everything else)

- Front of House
- Line
- Any other location name not matching above

---

## Score Calculation

```
Unit Score = Σ(item flag points) + Σ(room flag points)
```

### Example

**Unit A - PSEG NHQ**

Item flags:
- CELIUS: 22 CS, $564.96 → 10+ CS (3) + >$250 (1) = 4 pts
- PEPSI 20OZ: 44 CASE, $1,239.92 → >$250 only = 1 pt
- BEEF CORNED: 18 CS, $146.92 → 10+ CS only = 3 pts

Room flags:
- Front of House total: $180 → Low Room (2 pts)

**Total Score: 10**

---

## Display Requirements

### Unit List View

Show all units sorted by score, descending (worst first):

```
UNIT                    SCORE    FLAGS
-----------------------------------------
Phoenix Contact         14       5 items, 1 room
PSEG Salem              10       4 items, 0 rooms
Lockheed Bldg 100        6       2 items, 1 room
P&G Greensboro           2       0 items, 1 room
PSEG Hope Creek          0       Clean
```

### Unit Detail View (click to expand or separate view)

When Joseph drills into a unit, show:

1. **Flagged Items** (sorted by points descending)
   - Item description
   - Quantity
   - UOM
   - Total $
   - Flag type(s)
   - Location/GL Code

2. **Flagged Rooms** (if any)
   - Room name
   - Room total
   - Why flagged (under $1k or under $200)

3. **Summary Stats**
   - Total inventory value
   - Item count
   - Date of valuation

---

## Data Source

OrderMaestro valuation exports in xlsx format. Structure:

- Multiple sheets per workbook; data is in the sheet with the most rows
- Header row contains: "Item Description", "Quantity", "UOM", "Total Price", "GL Codes" (or similar)
- Header row is usually around row 8-9 (not row 1)
- GL Codes column contains location info like "GL Codes->Beverages 411054" or "Locations->Walk In Cooler"

The existing flag_checker.py already handles:
- Auto-detecting the data sheet
- Finding the header row
- Extracting the relevant columns
- Applying item-level flags

Room-level logic needs to be added.

---

## Room Aggregation Logic

To calculate room totals:

1. Parse the GL Code / Location column
2. Group items by location
3. Sum Total Price per location
4. Apply room-level flag rules based on location name and total

Location strings vary. Examples:
- "GL Codes->Beverages 411054"
- "GL Codes->Meat/ Poultry 411037"
- "Locations->Walk In Cooler"
- "Locations->Freezer"
- "Unassigned"

Extract the location name after the arrow (->). If no arrow, use the full string.

---

## Future Considerations (not for v1)

These came up in discussion but are NOT part of this spec:

- Week-over-week variance analysis
- Usage vs sales reconciliation
- Unassigned item count as a flag
- "Didn't close out" status
- Ken-facing dashboard view

Focus on the scoring system first. Get units ranked by health. Everything else is downstream.

---

## Implementation Notes

This is for the existing Ops-dash (React/TypeScript). The scoring logic can be:

1. **Backend** — Process on ingest, store score in data model
2. **Frontend** — Calculate on render from raw data

Recommend backend so scores persist and can be compared over time.

---

## Acceptance Criteria

- [ ] Each unit displays with a numerical health score
- [ ] Units are sorted descending (worst first)
- [ ] Item-level flags scored: 10+ CS = 3 pts, >$250 = 1 pt
- [ ] Room-level flags scored: Low dedicated storage (<$1k) = 2 pts, Low other (<$200) = 2 pts
- [ ] Clicking a unit shows flagged items and rooms
- [ ] Clean units (score 0) clearly marked

---

## Joseph's Sites (for reference)

- PSEG NHQ
- PSEG Hope Creek
- PSEG Salem
- Lockheed Martin Building 100
- Lockheed Martin Building D
- P&G Greensboro
- Phoenix Contact
- CSC HQ
