# Spectre UI Redesign - Design Document

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete UI overhaul - sharper modern look, better navigation, consolidated data views.

**Philosophy:** Stay in one place. Context comes to you. Single source of truth for each metric.

---

## Visual Design System

### Color Palette
- **Background**: Off-white/light gray (#FAFAFA)
- **Surface**: White cards with subtle shadows
- **Accent**: One vibrant primary (electric blue/teal) for actions and highlights
- **Status**: Red (critical), Amber (warning), Green (good) - used sparingly

### Typography
- Modern sans-serif (Inter)
- Clear hierarchy: bold headings, regular body, muted secondary
- Generous spacing

### Components
- Minimal borders, use whitespace and shadows
- Rounded corners (4-8px radius)
- Subtle hover states with accent color
- Clean data tables, highlight on hover

### Data Visualization
- 2-3 colors max per chart
- Sparklines for inline trends
- Big numbers for key metrics
- Bar/line charts only (no pie charts)

---

## Layout Structure

### Three-Zone Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo]    Inbox | Issues | Inventory    [⌘K Search] [⚙]   │  ← Top Nav
├─────────────────────────────────────────────┬───────────────┤
│                                             │               │
│                                             │   Context     │
│              Main Workspace                 │    Panel      │
│                                             │  (details)    │
│                                             │               │
│                                             │               │
└─────────────────────────────────────────────┴───────────────┘
```

### Navigation
- Three main tabs: Inbox, Issues, Inventory
- Command Bar (Cmd+K) for search and actions
- Context Panel (right) for details without page jumping
- Settings behind gear icon

---

## View 1: Inbox

**Purpose:** File ingestion with date validation

### Layout
- Left: File queue (draggable priority)
- Right: Preview pane with extracted data

### Date Validation
- Detected dates shown prominently
- Visual diff if dates seem off
- One-click override dropdown
- Confidence indicator

### Status Badges
- Pending, Processing, Needs Review, Complete

### Flow
1. File lands in queue
2. System parses, shows preview with dates
3. User confirms or corrects dates
4. Accept → data flows to Inventory
5. Issues auto-flag in Issues view

### Batch Operations
- Multi-select
- Accept all (high confidence)
- Bulk date override

---

## View 2: Issues

**Purpose:** Flags ranked by importance

### Prioritization
1. Dollar impact (primary)
2. Pattern frequency (secondary)
3. Recency weighting

### Issue Card Contents
- Item/category name
- Issue type
- **$XXX impact** (prominent)
- Pattern indicator ("3rd occurrence this month")
- Trend sparkline

### Filtering
- Date range
- Site/location
- Issue type
- Status: Open, Acknowledged, Resolved

### Actions
- Mark acknowledged
- Drill into inventory record
- Link to source file

---

## View 3: Inventory

**Purpose:** Single unified data view

### Replaces These Pages
- Dashboard, Rooms, Collections, Scores, Cart, Catalog, History, etc.

### Filter Bar
- Date range, site, category, room, flags only
- Group by: None, Category, Room, Vendor
- Saved filter presets

### Table Columns
- Item name
- Current count
- Last count date
- Variance (color-coded)
- Cost/value
- Flags (icons)
- Trend sparkline

### Context Panel Integration
- Click row → details slide in
- History, files, notes in panel
- Inline editing

---

## Command Bar

### Trigger
- Cmd+K from anywhere

### Features
- Search everything: files, items, issues
- Quick actions: Upload, New count, Export
- Recent items
- Fuzzy matching

### Keyboard Shortcuts
- Cmd+K: Command Bar
- Cmd+1/2/3: Switch tabs
- Arrow keys: Navigate lists
- Enter: Open Context Panel
- Escape: Close panel

---

## Page Consolidation Map

| Old Page | New Location |
|----------|--------------|
| Dashboard | Summary stats in Issues view |
| Inbox | Inbox tab |
| Inventory | Inventory tab |
| Rooms | Filter/group in Inventory |
| Collections | Filter in Inventory |
| Scores | Column in Inventory |
| Cart | Command Bar / Context Panel |
| Catalog | Command Bar / Context Panel |
| History | Context Panel |
| Notes | Context Panel |
| AI/Assistant | Floating action / Command Bar |
| Search | Command Bar |
| Settings | Settings gear |
| All others | Command Bar accessible |

---

## Tech Stack

- React + TypeScript (existing)
- Tailwind CSS (existing)
- shadcn/ui components (existing, restyle)
- Possibly add: cmdk for Command Bar

---

## Implementation Priority

1. **Phase 1**: Layout shell (three-zone structure, new nav)
2. **Phase 2**: Command Bar
3. **Phase 3**: Inbox view with date validation
4. **Phase 4**: Issues view with prioritization
5. **Phase 5**: Inventory view consolidation
6. **Phase 6**: Context Panel integration
7. **Phase 7**: Visual polish and animations
