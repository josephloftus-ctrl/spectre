# Spectre Counter MVP Design

## Overview

A single-purpose iOS app that fills OrderMaestro (MOG) inventory worksheets. Import a template, count offline, export ready for upload.

## Problem

Getting inventory counts into MOG is tedious:
- Download worksheet → print or view on laptop → walk around → write/type counts → re-enter into MOG

This app puts the worksheet on your phone with rock-solid offline input.

## Core Flow

```
MOG "Download Inventory Worksheet" (.xlsx)
    → Import to app (Files / share sheet)
    → Count items offline
    → Export completed .xlsx (share sheet)
    → Upload to MOG
```

## What It Is NOT

- Not a full inventory management system
- Not connected to Spectre backend
- No zones, canon system, or site profiles
- No cloud sync or accounts

---

## Data Model

### Imported from MOG Worksheet

| Field | Used For |
|-------|----------|
| Item Description | Display name |
| Dist # | Item identifier |
| Location / Area / Place | Grouping & sorting |
| UOM | Display next to count |
| Quantity (if present) | Starting value |

### Tracked During Counting

| Field | Purpose |
|-------|---------|
| Current count | User-entered value |
| Counted flag | Has user touched this item? |
| Timestamp | When count was entered |

### Exported

Same MOG template structure with Quantity column populated. Template format preserved exactly for MOG acceptance.

### Local Storage

- One session at a time (import overwrites previous)
- Persists on device until next import or manual clear
- No account, no login, no sync

---

## User Interface

### Import Screen

```
┌─────────────────────────────────┐
│                                 │
│     📁 Spectre Counter          │
│                                 │
│   No inventory loaded           │
│                                 │
│   ┌───────────────────────┐     │
│   │   Import Worksheet    │     │
│   └───────────────────────┘     │
│                                 │
│   Accepts .xlsx files from      │
│   OrderMaestro inventory        │
│   worksheet export              │
│                                 │
└─────────────────────────────────┘
```

- Opens iOS file picker (.xlsx only)
- Also accepts files via share sheet ("Open in Spectre Counter")
- Invalid file shows clear error

### Counting Screen

```
┌─────────────────────────────────┐
│ ┌─────────────────────────────┐ │
│ │ 🔍 Search items...          │ │
│ └─────────────────────────────┘ │
│                                 │
│ 47 of 156 counted    [Uncounted]│
│                                 │
│ ▼ Walk-In Cooler (12 items)     │
│ ┌─────────────────────────────┐ │
│ │ Chicken Breast 10lb   CS    │ │
│ │                 ← 3 →       │ │
│ │                       ✓     │ │
│ └─────────────────────────────┘ │
│ ┌─────────────────────────────┐ │
│ │ Heavy Cream Qt        EA    │ │
│ │                 ← 0 →       │ │
│ │                             │ │
│ └─────────────────────────────┘ │
│                                 │
│ ▶ Dry Storage (28 items)        │
│ ▶ Freezer (14 items)            │
│                                 │
└─────────────────────────────────┘
        [Export]
```

**Layout:**
- Search bar always visible at top
- Progress indicator with uncounted filter toggle
- Items grouped by Location > Area > Place (collapsible)
- Uncounted items visually prominent, counted items fade back
- Export button at bottom

**Interactions:**
- **Swipe right** on row: +1
- **Swipe left** on row: -1
- **Tap count number**: Opens numpad for direct entry
- **Search**: Filters across all locations, results still grouped
- **Uncounted filter**: Shows only items not yet touched

### Export Screen

```
┌─────────────────────────────────┐
│                                 │
│   Ready to export               │
│                                 │
│   147 of 156 items counted      │
│   9 items uncounted             │
│                                 │
│   ┌───────────────────────────┐ │
│   │   Export Anyway       │     │
│   └───────────────────────────┘ │
│   ┌───────────────────────────┐ │
│   │   Review Uncounted    │     │
│   └───────────────────────────┘ │
│                                 │
└─────────────────────────────────┘
```

- Shows summary before export
- Share sheet for AirDrop, Files, email, etc.
- Filename: `Inventory_YYYY-MM-DD_HHMM.xlsx`

---

## Technical Approach

### Platform

iOS (iPhone primary, iPad supported)

### Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| UI | SwiftUI | Modern, fast to build, good gesture support |
| XLSX parsing/writing | CoreXLSX | Pure Swift, no dependencies, offline |
| Local storage | SwiftData or JSON | Persists session between launches |
| Min iOS | 17 | SwiftUI improvements |

### Offline-First

- Zero network calls
- All XLSX operations on device
- No analytics, crash reporting, or telemetry
- Works in airplane mode, freezers, basements

### Project Structure

```
SpectreCounter/
├── Models/
│   ├── InventoryItem.swift
│   └── CountSession.swift
├── Views/
│   ├── ImportView.swift
│   ├── CountingView.swift
│   └── ExportView.swift
├── Services/
│   ├── XLSXParser.swift
│   └── XLSXWriter.swift
└── App/
    └── SpectreCounterApp.swift
```

---

## MVP Scope

### In Scope

- Import MOG inventory worksheet (.xlsx)
- Display items grouped by Location > Area > Place
- Search across all items without breaking flow
- Swipe +1/-1, tap for numpad entry
- Visual distinction: uncounted vs counted
- Progress tracking with uncounted filter
- Export MOG-compatible .xlsx via share sheet
- Fully offline operation

### Out of Scope (Future)

- Multiple sessions / saved inventories
- Spectre backend integration
- Zone scanning / QR codes
- Canon system / templates
- Cloud sync
- Barcode scanning
- Break quantity / split UOM entry

---

## App Identity

**Name:** Spectre Counter
**Home screen:** "Counter"

---

*Design finalized: 2026-01-28*
