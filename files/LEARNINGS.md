# LEARNINGS.md — Nebula Project

## January 2026 - SPEC-007: Purchase Match Diagnostic

### Patterns Used

**1. Adapter Pattern for Data Sources**
The inventory data lives in the ops dashboard, but we don't want the matcher to know or care about that. The `InventoryAdapter` abstract class defines what the matcher needs; implementations handle the messy reality of where data actually lives.

```python
# Matcher doesn't know if inventory comes from CSV, database, or API
results = match_inventory(adapter.get_inventory_for_unit("PSEG_HQ"), index, config)
```

**Why it matters:** When the ops dashboard integration is ready, we write one new class. Matcher code doesn't change. Tests keep passing.

---

**2. Index-Based Lookup for Performance**
Instead of searching 3000 purchase records for every inventory item, we build lookup dictionaries once:
- `by_sku` — O(1) exact match
- `by_vendor_price` — O(1) fallback lookup

**Why it matters:** 500 inventory items × 3000 purchases = 1.5M comparisons with naive approach. With indexes: 500 inventory items × 2 lookups = 1000 operations.

---

**3. Declarative Configuration for Business Rules**
Unit-vendor relationships are data, not code:

```json
{
  "PSEG_HQ": { "vendors": ["sysco", "vistar"] },
  "LOCKHEED": { "vendors": ["gordon_food_service"] }
}
```

**Why it matters:** When a unit switches vendors (happens yearly sometimes), edit JSON. No code review, no deployment risk, no developer needed.

---

**4. Vendor Alias Normalization**
Source data says "Sysco Corporation" or "SYSCO" or "Sysco Corp". Config maps all variations to canonical key:

```json
{
  "vendor_aliases": {
    "sysco": ["Sysco Corporation", "SYSCO", "Sysco Corp"]
  }
}
```

**Why it matters:** Matching logic doesn't care about string variations. One normalization step, then everything uses clean keys.

---

**5. Siloed Module Architecture**
This module has zero imports from other Nebula components. Own directory, own models, own tests.

**Why it matters:** 
- Can test without standing up the rest of Nebula
- Can extract to separate service later if needed
- Bug in this module can't break Unit Health (or vice versa)
- Clear ownership boundary

---

### Kitchen Analogy

**Purchase Match = Receiving Clerk with Perfect Memory**

Imagine a receiving clerk who remembers every delivery from the last 3 months. When doing inventory, they walk through the walk-in and check each item:

- "Sysco tomatoes, SKU 12345? Yep, I signed for those October 15th." → **CLEAN**
- "These tomatoes say SKU 99999... but the price tag says $47.82, and I remember signing for tomatoes at exactly that price. Let me check..." → **SKU_MISMATCH** (suggests the right SKU)
- "Gordon foodservice item at a Sysco-only account? That shouldn't be here." → **ORPHAN** (wrong vendor)
- "Never seen this before, price doesn't match anything..." → **ORPHAN** (investigate)

The tool is that clerk's perfect memory, working at computer speed.

---

### Things to Remember

**1. Price is a Better Signal Than Description**
"TOMATO DICED #10" vs "DICED TOMATOES #10 CAN" — fuzzy text matching is a rabbit hole. But $47.82 is $47.82. Use the strong signal.

**2. Constraints Prevent Bad Suggestions**
Without vendor constraint, a $4.29 Sysco milk could match a $4.29 Gordon milk. Technically same price, totally wrong suggestion. Constraints narrow the search space to useful answers.

**3. Start Strict, Loosen Later**
Price tolerance starts at 0%. If we get too many false negatives (legit matches rejected because price changed by a penny), we can add tolerance. Easier to loosen than to tighten.

**4. Diagnostic, Not Workflow**
This tool surfaces problems. It doesn't track whether someone fixed them. That's a different tool (maybe future). Keeping scope tight means shipping faster and maintaining less.

**5. Mock Adapters Enable Testing**
Can't wait for ops dashboard integration to test the matcher. Mock adapter with controlled data proves the logic works. Real adapter is just a different implementation of the same interface.

---

### Questions Answered During Design

**Q: Why not fuzzy match on description?**
A: Too many false positives. "MILK 2%" would match "BUTTERMILK" on token overlap. Price is unambiguous.

**Q: Why group by unit in output?**
A: Different units have different people responsible. Output needs to route to the right human.

**Q: Why SKU_MISMATCH before ORPHAN in report?**
A: SKU_MISMATCH items are quick wins — here's the suggested fix, go correct it. ORPHANs need investigation. Triage order matters.

**Q: Why not store results in database?**
A: No workflow means no need for persistence. Run the diagnostic, look at output, act on it. Next run is fresh. Simpler.

---

*LEARNINGS.md | Append-only log of patterns and insights*
