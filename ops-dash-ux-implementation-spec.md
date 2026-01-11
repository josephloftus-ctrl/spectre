# Ops Dash UX Implementation Spec

**Version:** 1.0  
**Date:** January 6, 2026  
**Spec ID:** SPEC-007.2  
**Status:** Ready for Implementation

---

## Executive Summary

This spec defines two interconnected UX improvements for Ops Dash:

1. **Navigation Architecture Overhaul** - Replace side drawer hamburger menu with bottom tab bar + FAB + bottom sheet pattern
2. **Notes Module Redesign** - Transform flat capture list into "manager's notebook" with tags and lifecycle

Both changes share a new color system and design language.

---

## Part 1: Design System

### 1.1 Color Palette

**Brand Color: Calm Steel Blue**

| Token | Hex | Usage |
|-------|-----|-------|
| `--accent-primary` | `#5C7C9A` | FAB, active nav, primary buttons, links |
| `--accent-light` | `#7A9BB8` | Hover states, secondary interactive |
| `--accent-dark` | `#3D5A73` | Pressed states, emphasis text, dark theme links |

**Semantic Colors (unchanged purpose, refined values)**

| Token | Dark Theme | Light Theme | Usage |
|-------|------------|-------------|-------|
| `--color-success` | `#4ADE80` | `#22C55E` | Operational status, positive indicators |
| `--color-warning` | `#FBBF24` | `#D97706` | Caution states, stale indicators |
| `--color-error` | `#F87171` | `#EF4444` | Issues, alerts, critical actions |
| `--color-info` | `#60A5FA` | `#3B82F6` | Informational badges |

**Surface Colors**

| Token | Dark Theme | Light Theme |
|-------|------------|-------------|
| `--bg-base` | `#0D1117` | `#F4F6F8` |
| `--bg-surface` | `#161B22` | `#FFFFFF` |
| `--bg-elevated` | `#1C2128` | `#FFFFFF` |
| `--bg-overlay` | `rgba(13, 17, 23, 0.8)` | `rgba(244, 246, 248, 0.9)` |

**Text Colors**

| Token | Dark Theme | Light Theme |
|-------|------------|-------------|
| `--text-primary` | `#E8EAED` | `#1A1D21` |
| `--text-secondary` | `#9BA3AF` | `#6B7280` |
| `--text-muted` | `#6B7280` | `#9BA3AF` |
| `--text-inverse` | `#1A1D21` | `#E8EAED` |

**Border Colors**

| Token | Dark Theme | Light Theme |
|-------|------------|-------------|
| `--border-default` | `#30363D` | `#D1D5DB` |
| `--border-emphasis` | `#484F58` | `#9CA3AF` |

### 1.2 Typography

Use system font stack for performance:

```css
--font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
```

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Display | 24px | 600 | 1.2 |
| Title | 18px | 600 | 1.3 |
| Body | 16px | 400 | 1.5 |
| Caption | 14px | 400 | 1.4 |
| Label | 12px | 500 | 1.3 |
| Tab Label | 10px | 500 | 1.2 |

### 1.3 Spacing Scale

```css
--space-xs: 4px;
--space-sm: 8px;
--space-md: 16px;
--space-lg: 24px;
--space-xl: 32px;
--space-2xl: 48px;
```

### 1.4 Touch Targets

Kitchen environment requires generous targets:

| Element | Minimum Size | Recommended |
|---------|--------------|-------------|
| Buttons | 44px | 48px |
| Tab items | 48px height | 56px |
| List items | 48px | 56px |
| FAB | 56px | 56px |
| FAB menu items | 48px | 48px |

### 1.5 Elevation / Shadows

```css
/* Dark theme - use opacity, minimal shadows */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
--shadow-md: 0 4px 8px rgba(0, 0, 0, 0.4);
--shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.5);
--shadow-fab: 0 4px 12px rgba(92, 124, 154, 0.3);

/* Light theme - traditional shadows */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 8px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.15);
--shadow-fab: 0 4px 12px rgba(61, 90, 115, 0.25);
```

### 1.6 Border Radius

```css
--radius-sm: 4px;
--radius-md: 8px;
--radius-lg: 12px;
--radius-xl: 20px;
--radius-full: 9999px;
```

### 1.7 App Icon

**Status:** Placeholder - icon not yet designed

Implementation should:
- Use a simple geometric placeholder (rounded square with "OD" text)
- Ensure icon container supports easy swap once final icon is ready
- Icon dimensions: 192x192 (PWA), 512x512 (splash), favicon variants

---

## Part 2: Navigation Architecture

### 2.1 Current State (Remove)

- Side drawer hamburger menu (60% viewport coverage)
- 7 navigation items + Settings in drawer
- X close button in top-right (impossible thumb zone)
- Gesture conflicts with system back navigation

### 2.2 Target State

**Bottom Tab Bar (5 items)**

| Position | Icon | Label | Destination |
|----------|------|-------|-------------|
| 1 | 🏠 (home) | Home | Dashboard |
| 2 | ⚠️ (alert-triangle) | Health | Unit Health |
| 3 | 📥 (inbox) | Inbox | Inbox |
| 4 | 🔍 (search) | Search | Semantic Search |
| 5 | ••• (more-horizontal) | More | Opens bottom sheet |

**"More" Bottom Sheet Contents**

| Icon | Label | Destination |
|------|-------|-------------|
| 📄 (file-text) | Documents | Documents list |
| 📝 (edit-3) | Notes | Notes module (manager's notebook) |
| 🤖 (bot) | AI Assistant | AI Assistant |
| ⚙️ (settings) | Settings | Settings |
| 🟢 (circle) | Systems Operational | Status indicator (not tappable) |

**FAB (Floating Action Button)**

- Position: Bottom-right, 20px from edge, 16px above tab bar
- Color: `--accent-primary` (#5C7C9A)
- Icon: Plus (+)
- Expands to speed dial on tap

**FAB Speed Dial Actions**

| Icon | Label | Action |
|------|-------|--------|
| 📝 (edit-3) | Add Note | Opens new note creation |
| ⚠️ (alert-circle) | Report Issue | Opens issue report flow |
| 📋 (clipboard) | Quick Count | Opens quick inventory count |

### 2.3 Component Specifications

#### Bottom Tab Bar

```css
.tab-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 56px;
  padding-bottom: env(safe-area-inset-bottom);
  background: var(--bg-surface);
  border-top: 1px solid var(--border-default);
  display: flex;
  justify-content: space-around;
  align-items: center;
  z-index: 1000;
}

.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 64px;
  height: 100%;
  padding: 8px 12px;
  color: var(--text-secondary);
  transition: color 0.15s ease;
}

.tab-item.active {
  color: var(--accent-primary);
}

.tab-icon {
  width: 24px;
  height: 24px;
  margin-bottom: 4px;
}

.tab-label {
  font-size: 10px;
  font-weight: 500;
  line-height: 1.2;
}

/* Badge for counts */
.tab-badge {
  position: absolute;
  top: 4px;
  right: 50%;
  transform: translateX(12px);
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  background: var(--color-error);
  color: white;
  font-size: 10px;
  font-weight: 600;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
}
```

#### Bottom Sheet (More Menu)

```css
.bottom-sheet-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1001;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.bottom-sheet-overlay.visible {
  opacity: 1;
}

.bottom-sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--bg-surface);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  padding: 12px 20px;
  padding-bottom: calc(20px + env(safe-area-inset-bottom));
  transform: translateY(100%);
  transition: transform 0.3s cubic-bezier(0.32, 0.72, 0, 1);
  z-index: 1002;
  max-height: 70vh;
  overflow-y: auto;
}

.bottom-sheet.open {
  transform: translateY(0);
}

.sheet-handle {
  width: 36px;
  height: 4px;
  background: var(--border-emphasis);
  border-radius: var(--radius-full);
  margin: 0 auto 20px;
}

.sheet-item {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 56px;
  padding: 0 8px;
  color: var(--text-primary);
  font-size: 16px;
  border-radius: var(--radius-md);
  transition: background 0.15s ease;
}

.sheet-item:active {
  background: var(--bg-elevated);
}

.sheet-item-icon {
  width: 24px;
  height: 24px;
  color: var(--text-secondary);
}

.sheet-divider {
  height: 1px;
  background: var(--border-default);
  margin: 8px 0;
}

.sheet-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 8px;
  color: var(--text-muted);
  font-size: 14px;
}

.sheet-status-dot {
  width: 8px;
  height: 8px;
  background: var(--color-success);
  border-radius: var(--radius-full);
}
```

#### FAB and Speed Dial

```css
.fab-container {
  position: fixed;
  bottom: calc(72px + env(safe-area-inset-bottom));
  right: 20px;
  z-index: 999;
}

.fab {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-full);
  background: var(--accent-primary);
  color: white;
  border: none;
  box-shadow: var(--shadow-fab);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s ease, background 0.15s ease;
}

.fab:active {
  transform: scale(0.95);
  background: var(--accent-dark);
}

.fab-icon {
  width: 24px;
  height: 24px;
  transition: transform 0.2s ease;
}

.fab.expanded .fab-icon {
  transform: rotate(45deg);
}

.fab-menu {
  position: absolute;
  bottom: 64px;
  right: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  opacity: 0;
  transform: scale(0.8) translateY(20px);
  pointer-events: none;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fab.expanded + .fab-menu,
.fab-menu.open {
  opacity: 1;
  transform: scale(1) translateY(0);
  pointer-events: auto;
}

.fab-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-surface);
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-md);
  white-space: nowrap;
}

.fab-menu-item-icon {
  width: 20px;
  height: 20px;
  color: var(--accent-primary);
}

.fab-menu-item-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}
```

### 2.4 Interaction Behaviors

**Tab Bar:**
- Tap tab → Navigate to destination, update active state
- Active tab shows `--accent-primary` color
- Badge appears when items need attention (e.g., Inbox count, Health issues count)

**More Sheet:**
- Tap "More" tab → Sheet slides up with overlay
- Tap overlay or swipe down → Dismisses sheet
- Tap item → Navigate and dismiss
- Sheet supports drag-to-dismiss gesture

**FAB:**
- Tap FAB → Expands to show speed dial menu
- Tap expanded FAB (X) → Collapses menu
- Tap outside expanded menu → Collapses menu
- Tap menu item → Execute action, collapse menu

### 2.5 Page Content Adjustment

All page content must account for fixed bottom navigation:

```css
.page-content {
  padding-bottom: calc(72px + env(safe-area-inset-bottom));
}
```

---

## Part 3: Notes Module (Manager's Notebook)

### 3.1 Concept

Transform the current flat capture list into a "manager's notebook" that matches how food service managers actually organize information. Notes are grouped by purpose using tags, with lifecycle management to encourage hygiene without blocking workflow.

### 3.2 Data Model

#### NoteEntity (New)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Primary key |
| `title` | string | Note name (e.g., "Sysco Order 1/6") |
| `tag` | string \| null | One of: orders, inventory, tasks, notes, money |
| `createdAt` | number | Unix timestamp (ms) |
| `updatedAt` | number | Unix timestamp (ms) - updates on any item add/edit |
| `status` | string | One of: active, stale, junk |
| `siteId` | string | Location identifier |

#### CaptureEntity (Modified)

Add field:

| Field | Type | Description |
|-------|------|-------------|
| `noteId` | string (FK) | Foreign key to NoteEntity.id |

Existing fields preserved:
- `id`, `timestamp`, `rawInput`, `inputMethod`, `siteId`

### 3.3 Tag System

| Tag | Icon | Color Tint | Purpose |
|-----|------|------------|---------|
| Orders | 📦 (package) | `#5C7C9A` | Vendor orders - Sysco, Pepsi, Produce, etc. |
| Inventory | 📋 (clipboard-list) | `#5C7C9A` | Counts, walkthroughs, stock levels |
| Tasks | ✓ (check-circle) | `#5C7C9A` | To-do items, recurring tasks |
| Notes | 💭 (message-circle) | `#5C7C9A` | Random thoughts, observations |
| Money | 💰 (dollar-sign) | `#5C7C9A` | Kitchen accounting, cost tracking |
| (Untagged) | ○ (circle) | `--text-muted` | Uncategorized - visual distinction |

### 3.4 Note Lifecycle

| Status | Trigger | Visual Treatment | Duration |
|--------|---------|------------------|----------|
| **Active** | Default for new notes, any edit | Normal display | Until 14 days inactive |
| **Stale** | 14 days since `updatedAt` | Age badge ("12 days"), muted appearance | 7 more days |
| **Junk** | Manual move OR 21 days total inactive | Moved to Junk section | 7 days |
| **Deleted** | Manual OR 7 days in Junk | Permanently removed | Immediate |

**Lifecycle transitions:**
- Active → Stale: Automatic at 14 days inactive
- Stale → Junk: Automatic at 21 days OR manual swipe
- Junk → Deleted: Automatic at 28 days OR manual "Empty Junk"
- Junk → Active: Manual restore (resets `updatedAt`)

### 3.5 Screen Specifications

#### Screen 1: Note List (Home for Notes Module)

**Purpose:** Show all notes, filter by tag, access any note in one tap

**Layout:**
```
┌─────────────────────────────────────┐
│ ← Notes                        [+]  │  ← Header with back arrow, title, add button
├─────────────────────────────────────┤
│ [All] [📦] [📋] [✓] [💭] [💰]      │  ← Filter chips, horizontally scrollable
├─────────────────────────────────────┤
│ 📦 Sysco Order 1/6                  │
│    5 items                          │  ← Note card
│                                     │
│ 📦 Pepsi Order                      │
│    3 items · 2 days                 │  ← Shows age if stale
│                                     │
│ ○ Random observations               │
│    12 items · 15 days               │  ← Untagged sinks lower
├─────────────────────────────────────┤
│ 🗑️ Junk (3)                    ›    │  ← Collapsed junk section
└─────────────────────────────────────┘
```

**Components:**
- Header: Back arrow (returns to Ops Dash), "Notes" title, [+] button for new note
- Filter row: Horizontal scrolling chips [All] [Orders] [Inventory] [Tasks] [Notes] [Money]
- Note list: Scrollable, sorted by tag presence then `updatedAt`
- Junk section: Collapsed at bottom, shows count, tap to expand

**Sorting Logic:**
1. Tagged notes first, sorted by `updatedAt` descending
2. Untagged notes second, sorted by `updatedAt` descending
3. Within each group: Active before Stale

**Interactions:**
- Tap filter chip → Filter list to that tag (or show all)
- Tap note card → Open Note Detail
- Swipe note left → Reveal "Move to Junk" action
- Tap [+] → Open New Note modal
- Tap Junk section → Expand to show junk notes with restore/delete options

#### Screen 2: New Note (Modal)

**Purpose:** Quick note creation - title only, tag later

**Layout:**
```
┌─────────────────────────────────────┐
│                              [X]    │
│                                     │
│ New Note                            │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Note title...                   │ │  ← Auto-focused text field
│ └─────────────────────────────────┘ │
│                                     │
│        [ Create Note ]              │  ← Primary button, disabled until text
│                                     │
└─────────────────────────────────────┘
```

**Behavior:**
- Modal overlay, slides up from bottom
- Title field auto-focused, keyboard appears
- No tag selection required (speed over organization)
- Tap "Create Note" → Creates note, immediately opens Note Detail
- Tap X or outside → Dismisses without creating

#### Screen 3: Note Detail

**Purpose:** View and add items to a note, optionally categorize

**Layout:**
```
┌─────────────────────────────────────┐
│ ←                          [Export] │  ← Back arrow, export button
├─────────────────────────────────────┤
│ Sysco Order 1/6              [Edit] │  ← Editable title
│ Created Jan 6, 2026                 │  ← Metadata
│ 📦 Orders                           │  ← Tag badge (if tagged)
├─────────────────────────────────────┤
│                                     │
│ 5 cases milk 2%                     │
│ 10:32 AM                            │  ← Item with timestamp
│                                     │
│ 2 boxes romaine                     │
│ 10:33 AM                            │
│                                     │
│ [Swipe to delete items]             │
│                                     │
├─────────────────────────────────────┤
│ ○ Tag: [📦] [📋] [✓] [💭] [💰]     │  ← Only shows if untagged
├─────────────────────────────────────┤
│ [Add item...            ] [🎤] [+]  │  ← Input bar, always visible
└─────────────────────────────────────┘
```

**Components:**
- Header: Back arrow, Export button (top right)
- Title section: Editable title, creation date, tag badge
- Item list: Scrollable, each item shows text and timestamp
- Tag prompt: Only visible if note is untagged - shows all 5 tag icons
- Input bar: Fixed at bottom - text field, mic button, add button

**Interactions:**
- Tap back → Return to Note List
- Tap Export → Generate CSV for this note, open share sheet
- Tap title [Edit] → Inline edit mode
- Tap tag icon (in prompt) → Assign tag, prompt disappears
- Type + tap [+] → Add item to note, updates `updatedAt`
- Tap [🎤] → Voice input, auto-saves on recognition
- Swipe item left → Delete single item (with undo snackbar)

### 3.6 Component Specifications

#### Filter Chips

```css
.filter-row {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.filter-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-full);
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  white-space: nowrap;
  transition: all 0.15s ease;
}

.filter-chip.active {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: white;
}

.filter-chip-icon {
  width: 16px;
  height: 16px;
}
```

#### Note Card

```css
.note-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  margin: 0 16px 8px;
}

.note-card-icon {
  width: 24px;
  height: 24px;
  color: var(--accent-primary);
  flex-shrink: 0;
}

.note-card-icon.untagged {
  color: var(--text-muted);
}

.note-card-content {
  flex: 1;
  min-width: 0;
}

.note-card-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.note-card-meta {
  font-size: 14px;
  color: var(--text-secondary);
  display: flex;
  gap: 8px;
}

.note-card-age {
  color: var(--color-warning);
}

.note-card.stale {
  opacity: 0.7;
}
```

#### Tag Prompt (in Note Detail)

```css
.tag-prompt {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-default);
}

.tag-prompt-label {
  font-size: 14px;
  color: var(--text-muted);
}

.tag-prompt-options {
  display: flex;
  gap: 8px;
}

.tag-option {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  transition: all 0.15s ease;
}

.tag-option:active {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: white;
}
```

#### Input Bar (Note Detail)

```css
.input-bar {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  padding-bottom: calc(12px + env(safe-area-inset-bottom));
  background: var(--bg-surface);
  border-top: 1px solid var(--border-default);
}

.input-field {
  flex: 1;
  height: 44px;
  padding: 0 16px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-full);
  font-size: 16px;
  color: var(--text-primary);
}

.input-field::placeholder {
  color: var(--text-muted);
}

.input-button {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-full);
  color: var(--text-secondary);
}

.input-button.primary {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: white;
}

.input-button:active {
  opacity: 0.8;
}
```

### 3.7 CSV Export Format

Per-note export generates:

| Column | Description |
|--------|-------------|
| `note_title` | Title of the note |
| `note_tag` | Tag (orders/inventory/tasks/notes/money) or empty |
| `item` | The captured text |
| `timestamp` | ISO8601 UTC timestamp |
| `input_method` | "text" or "voice" |
| `site` | Site identifier |

Filename format: `{note_title}_{YYYY-MM-DD}.csv`

---

## Part 4: Implementation Phases

### Phase 1: Design System Foundation (Day 1)

1. Create CSS custom properties file with all tokens
2. Set up theme switching (dark/light) with CSS variables
3. Implement color palette throughout existing components
4. Test on both themes

**Files to create/modify:**
- `styles/tokens.css` (new)
- `styles/theme.css` (new or modify existing)

### Phase 2: Navigation Architecture (Days 2-3)

1. Create BottomTabBar component
2. Create BottomSheet component (for "More" menu)
3. Create FAB component with speed dial
4. Remove side drawer/hamburger
5. Update routing to work with new navigation
6. Add page content padding for fixed bottom nav

**Files to create:**
- `components/BottomTabBar.tsx` (or .vue/.svelte based on stack)
- `components/BottomSheet.tsx`
- `components/FAB.tsx`

**Files to modify:**
- Main layout component (remove drawer)
- Router configuration

### Phase 3: Notes Data Model (Day 4)

1. Create NoteEntity schema
2. Add `noteId` field to existing captures
3. Create Note repository/service
4. Implement CRUD operations
5. Add lifecycle status update logic (stale detection)

**Database changes:**
- New `notes` table
- Migration to add `noteId` to captures

### Phase 4: Notes UI (Days 5-6)

1. Create NoteListScreen
2. Create NewNoteModal
3. Create NoteDetailScreen
4. Implement filter chips
5. Wire up voice capture to new flow
6. Implement per-note CSV export

**Files to create:**
- `screens/Notes/NoteListScreen.tsx`
- `screens/Notes/NoteDetailScreen.tsx`
- `components/Notes/NewNoteModal.tsx`
- `components/Notes/NoteCard.tsx`
- `components/Notes/FilterChips.tsx`
- `components/Notes/TagPrompt.tsx`

### Phase 5: Lifecycle & Polish (Day 7)

1. Implement stale detection (run on app open)
2. Add Junk folder view
3. Implement swipe-to-junk gesture
4. Add auto-delete for old junk (7 days in junk)
5. Add "Empty Junk" button
6. Polish animations and transitions

---

## Part 5: Success Criteria

### Navigation

| Metric | Target |
|--------|--------|
| Taps to reach any primary destination | 1 |
| Taps to reach any secondary destination | 2 |
| Tab bar visible at all times | Yes |
| Works with system back gesture | Yes |
| Supports both hands equally | Yes |

### Notes Module

| Metric | Target |
|--------|--------|
| Taps from launch to first capture | ≤ 3 |
| Taps to reach any existing note | 1 |
| Can use without categorizing | Yes |
| Visual distinction: tagged vs untagged | Obvious |
| Export scope | Per-note |
| Works offline | Yes |

### General

| Metric | Target |
|--------|--------|
| Touch targets | ≥ 48px |
| Color contrast (WCAG AA) | ≥ 4.5:1 |
| Both themes implemented | Yes |
| Safe area handling | Yes |

---

## Part 6: Open Questions (For Joseph)

Before implementation begins, confirm:

1. **Default notes on fresh install:** Pre-made notes (Sysco, Pepsi, Inventory, etc.) or start empty?

2. **Stale threshold:** 14 days uniform, or different by tag? (e.g., Orders stale at 7 days, Inventory at 30?)

3. **Item deletion:** Swipe to delete individual items in v1, or note-level only?

4. **Voice recognition:** Keep Android native speech-to-text approach, or integrate with existing AI Assistant?

5. **Multi-site:** Should notes be site-specific (filter by current site) or global across all sites?

---

## Appendix A: Icon Reference

Using Lucide icons (or similar) for consistency:

| Usage | Icon Name |
|-------|-----------|
| Home tab | `home` |
| Health tab | `alert-triangle` |
| Inbox tab | `inbox` |
| Search tab | `search` |
| More tab | `more-horizontal` |
| Documents | `file-text` |
| Notes | `edit-3` or `sticky-note` |
| AI Assistant | `bot` |
| Settings | `settings` |
| Orders tag | `package` |
| Inventory tag | `clipboard-list` |
| Tasks tag | `check-circle` |
| Notes tag | `message-circle` |
| Money tag | `dollar-sign` |
| Untagged | `circle` (outline only) |
| FAB default | `plus` |
| FAB expanded | `x` |
| Add Note action | `edit-3` |
| Report Issue action | `alert-circle` |
| Quick Count action | `clipboard` |
| Back | `arrow-left` |
| Export | `share` or `download` |
| Microphone | `mic` |
| Delete/Junk | `trash-2` |

---

## Appendix B: Animations

**Tab switching:** Instant (no page transition animation - speed matters)

**Bottom sheet:**
- Open: 300ms cubic-bezier(0.32, 0.72, 0, 1)
- Close: 200ms ease-out

**FAB speed dial:**
- Expand: 200ms ease-out, stagger items 50ms
- Collapse: 150ms ease-in

**Swipe actions:**
- Reveal threshold: 80px
- Execute threshold: 160px
- Spring back: 200ms ease-out

**Page transitions:**
- Note List → Note Detail: Slide left, 250ms
- Note Detail → Note List: Slide right, 250ms

---

*End of Spec*
