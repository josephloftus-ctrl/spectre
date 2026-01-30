# Excel Metadata Extraction Design

**Date:** 2026-01-30
**Status:** Draft
**Author:** Joseph + Claude

---

## Problem

Files are uploaded with arbitrary names (`Copy of final_v2 (1).xlsx`) and the system relies on filename parsing or manual assignment for site and date. This is error-prone and requires cleanup.

The Excel files themselves contain the authoritative metadata in their headers - we should use that as the source of truth.

---

## Solution

Extract `inventory_date` and `site_name` directly from Excel content, then auto-rename and sort files. User drops any file, system handles the rest.

---

## Excel Structure

Sheet: **"Data for Inventory Locations"**

| Row | Column A | Contains |
|-----|----------|----------|
| 1 | `Inventory Valuation Report from Inventory Input - 01/29/2026` | Date |
| 2 | `PSEG - NHQ (673) (COMPASS)` | Site name |

---

## Extraction Rules

### Date (Row 1)
- Split on ` - `, take last segment
- Parse `MM/DD/YYYY` format
- Convert to ISO: `2026-01-29`

### Site Name (Row 2)
- Take text before first `(`
- Trim whitespace
- Result: `PSEG - NHQ`

### Site ID
- Slugify site name: lowercase, replace ` - ` and spaces with `_`
- Result: `pseg_nhq`

---

## Auto-Rename & Sort

### File Naming
Pattern: `{SITE_NAME}_{YYYY-MM-DD}.xlsx`

Example: `PSEG - NHQ_2026-01-29.xlsx`

### Folder Structure
```
data/processed/
└── PSEG - NHQ/
    ├── 2026-01/
    │   ├── PSEG - NHQ_2026-01-15.xlsx
    │   └── PSEG - NHQ_2026-01-29.xlsx
    └── 2026-02/
        └── PSEG - NHQ_2026-02-05.xlsx
```

### Duplicates
Same site + date → append counter: `PSEG - NHQ_2026-01-29_2.xlsx`

---

## Processing Flow

```
User drops file (any name)
       ↓
    Parse Excel
       ↓
  Extract Row 1 → date: 2026-01-29
  Extract Row 2 → site: "PSEG - NHQ"
       ↓
  Rename: "PSEG - NHQ_2026-01-29.xlsx"
       ↓
  Move to: data/processed/PSEG - NHQ/2026-01/
       ↓
  Update DB: inventory_date, site_id, filename, current_path
       ↓
  Continue scoring/embedding as normal
       ↓
    Done ✓
```

---

## Edge Cases

| Case | Handling |
|------|----------|
| Duplicate file (same site + date) | Append counter: `_2`, `_3`, etc. |
| Missing header rows | Fall back to filename extraction, flag for review |
| Wrong sheet name | Search all sheets for header pattern |
| Unparseable date | Log warning, use file modification time |

---

## Code Changes

| File | Change |
|------|--------|
| `backend/core/parsers.py` | Add `extract_header_metadata(file_path)` function |
| `backend/core/files.py` | Add `rename_and_sort_file(file_id, site_name, date)` function |
| `backend/core/worker.py` | Call extraction in `process_parse_job()` after parsing |
| `backend/core/db/files.py` | Ensure `update_file()` handles `inventory_date`, `site_id`, `filename`, `current_path` |

---

## Database Fields

Fields updated on file record:

| Field | Source | Example |
|-------|--------|---------|
| `inventory_date` | Excel Row 1 | `2026-01-29` |
| `site_id` | Slugified Row 2 | `pseg_nhq` |
| `filename` | Generated | `PSEG - NHQ_2026-01-29.xlsx` |
| `current_path` | New location | `data/processed/PSEG - NHQ/2026-01/...` |

---

## User Experience

**Before:** Upload → manually fix site → manually fix date → hope filename is right

**After:** Upload → done

No frontend changes required. Files appear organized automatically.

---

## Future Enhancements

- Batch re-process existing files to rename/sort them
- Support other report formats (CSV, PDF) with different header patterns
- Validate extracted site against known sites list
