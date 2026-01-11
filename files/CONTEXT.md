# CONTEXT.md — Purchase Match Diagnostic

## Project State

This is a new module being added to the Nebula Kitchen Operations Platform. Nebula already has:
- Inventory valuations in an ops dashboard
- Temperature logging (SPEC-003, frozen)
- Vendor profile queries (SPEC-006)
- Declarative file routing (SPEC-005)

The Purchase Match Diagnostic is **completely siloed** — it shares nothing with existing modules. This is intentional. Build it as if it could be extracted into its own repo tomorrow.

## Current Sprint

**SPEC-007: Purchase Match Diagnostic**

Building a diagnostic tool that compares inventory items against purchase history to flag:
1. **SKU_MISMATCH** — Item exists but coded with wrong SKU (price+vendor match suggests correction)
2. **ORPHAN** — Item has no match in purchase history (needs investigation)

## Architecture Decisions

### Why Siloed?
Joseph explicitly requested no shared dependencies with Unit Health or other modules. This diagnostic has a single job: compare two datasets and surface discrepancies. It doesn't need Nebula's other capabilities, and coupling would make both harder to maintain.

### Why SKU + Price + Vendor?
- **SKU** is the primary key — if it matches, item is clean
- **Price** is a strong signal — $47.82 is specific enough to suggest matches
- **Vendor constraint** prevents bad suggestions — don't suggest Sysco items to Gordon-only sites

### Why Declarative Config for Unit-Vendor Mapping?
- Units change vendors occasionally (contract switches)
- New units get added
- Editing JSON is safer than editing code
- Config file serves as documentation of current state

### Why No Workflow/Resolution Tracking?
- Scope control — this is a diagnostic lens, not a task manager
- The output feeds human investigation, not automated fixes
- Adding workflow would couple this to task management systems

## Files to Reference

### Sample Data (in uploads)
- `October_IPS.xlsx` — OrderMaestro purchase export
- `November_IPS.xlsx` — OrderMaestro purchase export  
- `December_IPS.xlsx` — OrderMaestro purchase export

### IPS File Structure
- Sheet: `Purchasing Details Raw Data`
- Headers on row 10
- Data starts row 11
- Key columns: B (Distributor), D (Item Number), E (Description), N (Invoiced Item Price)
- Some files have encoded headers (`Item_x0020_Number` instead of `Item Number`)

### Known Vendors (from December file)
```
Farmer Brothers Co
Gordon Food Service US
Kegel's Produce
Penn-Del Baking
Sysco Corporation
Vistar Corporation
```

## Don't Touch

- **Unit Health module** — completely separate, no shared code
- **SPEC-003/004** — temperature logging is frozen
- **nebula_engine.py** — this module doesn't integrate with the central facade
- **Existing ops dashboard** — adapter is a stub until integration point is defined

## Tech Stack for This Module

- **Python 3.10+**
- **openpyxl** — XLSX parsing
- **dataclasses** — structured data
- **Decimal** — money precision (not float)
- **pytest** — testing
- **argparse** — CLI

No FastAPI, no SQLite, no Docker for this module. It's a pure Python diagnostic tool.

## Testing Strategy

1. **Unit tests** for each component (loader, matcher, report)
2. **Fixtures** using sample IPS data
3. **Mock inventory adapter** for controlled test scenarios
4. **Integration test** proving full pipeline with real files

## Key Constraints

- Must work offline after files are loaded
- Must handle 3000+ purchase records efficiently
- Must never suggest cross-vendor matches
- Output must be human-readable for non-technical users

## Communication Style

Joseph learns through understanding WHY, not just WHAT. When making implementation decisions:
- Explain the reasoning
- Use kitchen analogies when helpful
- Flag when something seems like unnecessary complexity
- Ask before adding scope

---

*CONTEXT.md | SPEC-007 | v1.0*
