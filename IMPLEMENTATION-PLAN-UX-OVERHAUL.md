# UX Overhaul Implementation Plan

**Based on:** ops-dash-ux-implementation-spec.md (SPEC-007.2)
**Current State:** Analyzed via codebase exploration
**Approach:** Minimal refactoring, leverage existing infrastructure

---

## Executive Summary

The existing codebase is **well-positioned** for this overhaul:
- IndexedDB (Dexie) already handles notes with tags, categories, voice support
- Theme system uses CSS variables (easy to extend)
- Component library (shadcn/ui) provides building blocks
- React Router handles navigation

**Key insight:** The spec's "Notes" concept maps closely to existing notes, but with a parent-child twist - a "Note" becomes a container for multiple "Captures" (items). This requires a schema change but not a rewrite.

---

## Phase 0: Pre-Work Decisions

Before coding, resolve open questions from the spec:

| Question | Recommended Answer | Rationale |
|----------|-------------------|-----------|
| Default notes on fresh install? | Empty start | Cleaner UX, users create what they need |
| Stale threshold by tag? | Uniform 14 days (v1) | Simplicity; can add per-tag thresholds later |
| Item deletion? | Yes, swipe-to-delete items | Spec supports it, adds value |
| Voice recognition | Keep native Web Speech API | Already works, no AI dependency |
| Multi-site notes? | Site-specific by default | Matches existing `siteId` pattern |

---

## Phase 1: Design System Foundation

**Goal:** New color palette, spacing, typography tokens
**Impact:** Low risk, all additive

### 1.1 Update CSS Variables

**File:** `frontend/src/index.css`

```css
/* Add new tokens alongside existing */
:root {
  /* Accent Colors - Calm Steel Blue */
  --accent-primary: 207 25% 48%;      /* #5C7C9A */
  --accent-light: 207 28% 60%;        /* #7A9BB8 */
  --accent-dark: 207 32% 35%;         /* #3D5A73 */

  /* Semantic (keep existing, refine if needed) */
  --color-success: 142 71% 45%;
  --color-warning: 38 92% 50%;
  --color-error: 0 84% 60%;
  --color-info: 217 91% 60%;

  /* Touch targets */
  --touch-min: 44px;
  --touch-recommended: 48px;
  --fab-size: 56px;

  /* Spacing (already have some, ensure complete) */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;

  /* Bottom nav safe area */
  --nav-height: 56px;
  --content-bottom-padding: calc(var(--nav-height) + 16px + env(safe-area-inset-bottom));
}
```

### 1.2 Tailwind Extensions

**File:** `frontend/tailwind.config.js`

Add to `extend.colors`:
```js
accent: {
  DEFAULT: "hsl(var(--accent-primary))",
  light: "hsl(var(--accent-light))",
  dark: "hsl(var(--accent-dark))",
}
```

**Effort:** ~1 hour

---

## Phase 2: Navigation Architecture

**Goal:** Replace sidebar with bottom tab bar + FAB + bottom sheet
**Impact:** Medium - touches layout but not page content

### 2.1 New Components to Create

| Component | Location | Purpose |
|-----------|----------|---------|
| `BottomTabBar` | `components/navigation/BottomTabBar.tsx` | 5-tab fixed bottom nav |
| `BottomSheet` | `components/ui/bottom-sheet.tsx` | Reusable sheet for "More" |
| `FAB` | `components/navigation/FAB.tsx` | Floating action with speed dial |
| `TabItem` | Internal to BottomTabBar | Single tab with icon/label/badge |

### 2.2 Component: BottomTabBar

```tsx
// Tab configuration
const tabs = [
  { path: '/', icon: Home, label: 'Home' },
  { path: '/scores', icon: AlertTriangle, label: 'Health', badge: criticalCount },
  { path: '/inbox', icon: Inbox, label: 'Inbox', badge: pendingCount },
  { path: '/search', icon: Search, label: 'Search' },
  { path: 'more', icon: MoreHorizontal, label: 'More', isSheet: true },
]
```

- Fixed bottom, full width
- 56px height + safe-area-inset-bottom
- Active tab uses `--accent-primary`
- Badge support for counts (Health issues, Inbox pending)

### 2.3 Component: BottomSheet (More Menu)

Contents:
- Documents → /documents
- Notes → /notes
- AI Assistant → /ai
- Settings → /settings
- Status indicator (non-tappable)

Features:
- Drag-to-dismiss gesture
- Overlay backdrop
- Smooth animation (300ms cubic-bezier)

### 2.4 Component: FAB with Speed Dial

Position: Bottom-right, 20px from edge, 16px above tab bar

Actions (expanded):
1. **Add Note** → Opens new note modal
2. **Report Issue** → Opens issue form (new feature, stub for v1)
3. **Quick Count** → Opens inventory quick capture (stub for v1)

**Beyond spec:** Make FAB context-aware - on Notes page, primary action is "Add Note"; on Health page, it's "Report Issue".

### 2.5 Layout Changes

**File:** `components/layout/DashboardLayout.tsx`

Before:
```tsx
<div className="flex">
  <Sidebar className="hidden md:block" />
  <MobileSidebar />  {/* hamburger drawer */}
  <main className="flex-1 md:ml-64">
    {children}
  </main>
</div>
```

After:
```tsx
<div className="flex flex-col min-h-screen">
  <main className="flex-1 pb-[var(--content-bottom-padding)]">
    {children}
  </main>
  <BottomTabBar />
  <FAB />
</div>
```

### 2.6 Files to Delete/Deprecate

- `components/layout/Sidebar.tsx` - Remove entirely
- Mobile hamburger in header - Remove

**Effort:** ~4-6 hours

---

## Phase 3: Notes Data Model Evolution

**Goal:** Transform flat notes into "Manager's Notebook" with Note → Items hierarchy
**Impact:** Schema migration, but Dexie handles this cleanly

### 3.1 Schema Changes

**Current Note structure** (keep most fields):
```typescript
interface Note {
  id: string
  content: string        // Will become: items joined by newline (for search)
  title: string
  category?: string      // Maps to: tag
  tags: string[]         // Keep for flexibility
  createdAt: string
  updatedAt: string
  deleted: boolean
  isVoiceNote?: boolean
}
```

**New structure:**
```typescript
interface NoteEntity {
  id: string
  title: string
  tag: NoteTag | null    // Renamed from category, single value
  status: 'active' | 'stale' | 'junk'
  siteId: string
  createdAt: number      // Unix timestamp (easier math)
  updatedAt: number
}

type NoteTag = 'orders' | 'inventory' | 'tasks' | 'notes' | 'money'

interface CaptureEntity {
  id: string
  noteId: string         // FK to NoteEntity
  content: string        // The actual text
  timestamp: number
  inputMethod: 'text' | 'voice'
}
```

### 3.2 Migration Strategy

**Option A (Recommended): Parallel tables**
- Create new `notebooks` and `captures` tables
- Keep existing `notes` table for backward compatibility
- Migrate data lazily or on-demand
- Delete old table in future version

**Option B: In-place migration**
- Add new fields to existing notes
- Create captures table
- Split existing note.content into captures
- Higher risk, but cleaner

**Recommendation:** Option A - safer, allows rollback

### 3.3 Database Changes

**File:** `lib/db/index.ts`

```typescript
// New tables (version 3)
notebooks: '++id, tag, status, siteId, updatedAt',
captures: '++id, noteId, timestamp',

// Keep existing 'notes' table as-is for migration period
```

### 3.4 Lifecycle Logic

**File:** `lib/db/notebooks.ts` (new)

```typescript
function updateLifecycleStatus(notebook: NoteEntity): NoteEntity {
  const now = Date.now()
  const daysSinceUpdate = (now - notebook.updatedAt) / (1000 * 60 * 60 * 24)

  if (notebook.status === 'junk') {
    // Auto-delete after 7 days in junk
    if (daysSinceUpdate > 7) {
      return { ...notebook, status: 'deleted' }
    }
  } else if (daysSinceUpdate > 21) {
    return { ...notebook, status: 'junk' }
  } else if (daysSinceUpdate > 14) {
    return { ...notebook, status: 'stale' }
  }

  return notebook
}

// Run on app open
async function refreshAllLifecycles() {
  const all = await db.notebooks.toArray()
  const updates = all.map(updateLifecycleStatus).filter(n => n.status !== 'active')
  await db.notebooks.bulkPut(updates)
}
```

**Effort:** ~3-4 hours

---

## Phase 4: Notes UI Overhaul

**Goal:** New screens matching spec wireframes
**Impact:** Mostly new components, minimal changes to existing

### 4.1 New Components

| Component | File | Purpose |
|-----------|------|---------|
| `NotebookList` | `pages/NotesPage.tsx` (refactor) | Main list with filter chips |
| `NotebookCard` | `components/notes/NotebookCard.tsx` | List item with tag icon, meta |
| `NotebookDetail` | `pages/NotebookDetailPage.tsx` | View/edit single notebook |
| `NewNotebookModal` | `components/notes/NewNotebookModal.tsx` | Quick create |
| `FilterChips` | `components/notes/FilterChips.tsx` | Horizontal tag filter |
| `TagPrompt` | `components/notes/TagPrompt.tsx` | Assign tag inline |
| `CaptureInput` | `components/notes/CaptureInput.tsx` | Bottom input bar |
| `JunkSection` | `components/notes/JunkSection.tsx` | Collapsible junk area |

### 4.2 Notebook List Screen

**Sorting logic:**
1. Tagged notebooks first (by updatedAt desc)
2. Untagged notebooks second (by updatedAt desc)
3. Within groups: active → stale

**Filter chips:**
```tsx
const filters = [
  { key: 'all', label: 'All', icon: null },
  { key: 'orders', label: 'Orders', icon: Package },
  { key: 'inventory', label: 'Inventory', icon: ClipboardList },
  { key: 'tasks', label: 'Tasks', icon: CheckCircle },
  { key: 'notes', label: 'Notes', icon: MessageCircle },
  { key: 'money', label: 'Money', icon: DollarSign },
]
```

### 4.3 Notebook Detail Screen

**Layout zones:**
1. Header: Back arrow + Export button
2. Title section: Editable title, created date, tag badge
3. Item list: Scrollable captures with timestamps
4. Tag prompt: Only if untagged
5. Input bar: Fixed bottom with text field + mic + add

**Interactions:**
- Swipe item left → Delete with undo snackbar
- Tap mic → Voice capture (reuse existing useVoice hook)
- Tap export → Generate CSV, trigger share

### 4.4 New Route

**File:** `App.tsx`

```tsx
<Route path="/notes/:notebookId" element={<NotebookDetailPage />} />
```

### 4.5 CSV Export

**File:** `lib/export.ts` (new)

```typescript
function exportNotebookToCSV(notebook: NoteEntity, captures: CaptureEntity[]): string {
  const headers = ['note_title', 'note_tag', 'item', 'timestamp', 'input_method', 'site']
  const rows = captures.map(c => [
    notebook.title,
    notebook.tag || '',
    c.content,
    new Date(c.timestamp).toISOString(),
    c.inputMethod,
    notebook.siteId
  ])
  return [headers, ...rows].map(r => r.map(escapeCSV).join(',')).join('\n')
}
```

**Effort:** ~8-10 hours

---

## Phase 5: Polish & Enhancements

### 5.1 Animations

**File:** `index.css` (add keyframes)

```css
@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fabExpand {
  from { transform: scale(0.8) translateY(20px); opacity: 0; }
  to { transform: scale(1) translateY(0); opacity: 1; }
}
```

### 5.2 Gestures

**Swipe-to-delete/junk:** Use `@use-gesture/react` or simple touch handlers

```tsx
// Already have gesture handling potential via existing touch events
// Implement threshold-based swipe (80px reveal, 160px execute)
```

### 5.3 Safe Area Handling

Already using `env(safe-area-inset-bottom)` in CSS variables - ensure all fixed bottom elements use it.

### 5.4 Beyond Spec Enhancements

| Enhancement | Value | Effort |
|-------------|-------|--------|
| Notebook search | Find across all notebooks | Low |
| Drag-to-reorder items | Better organization | Medium |
| Notebook templates | "Sysco Order" pre-made | Low |
| Share to notebook | OS share target | Medium |
| Offline indicator | Show when offline | Low |
| Bulk select items | Delete multiple | Medium |

**Effort:** ~4-6 hours

---

## Implementation Order

```
Week 1:
├── Phase 1: Design tokens (1 hr)
├── Phase 2: Navigation (6 hrs)
│   ├── BottomTabBar
│   ├── BottomSheet
│   ├── FAB
│   └── Layout refactor
└── Testing navigation

Week 2:
├── Phase 3: Data model (4 hrs)
│   ├── Schema migration
│   ├── CRUD operations
│   └── Lifecycle logic
├── Phase 4: Notes UI (10 hrs)
│   ├── NotebookList
│   ├── NotebookDetail
│   ├── NewNotebookModal
│   └── CSV export
└── Phase 5: Polish (4 hrs)
```

**Total estimated effort:** 25-30 hours

---

## Files to Create

```
frontend/src/
├── components/
│   ├── navigation/
│   │   ├── BottomTabBar.tsx
│   │   ├── FAB.tsx
│   │   └── index.ts
│   ├── ui/
│   │   └── bottom-sheet.tsx
│   └── notes/
│       ├── NotebookCard.tsx
│       ├── FilterChips.tsx
│       ├── TagPrompt.tsx
│       ├── CaptureInput.tsx
│       ├── JunkSection.tsx
│       └── NewNotebookModal.tsx
├── pages/
│   └── NotebookDetailPage.tsx
├── lib/
│   ├── db/
│   │   └── notebooks.ts
│   └── export.ts
└── hooks/
    └── useNotebooks.ts
```

## Files to Modify

```
frontend/src/
├── index.css                    # Design tokens
├── tailwind.config.js           # Color extensions
├── App.tsx                      # New route
├── components/layout/
│   └── DashboardLayout.tsx      # Remove sidebar, add bottom nav
├── pages/
│   └── NotesPage.tsx            # Refactor to NotebookList
└── lib/db/
    ├── index.ts                 # New tables
    └── types.ts                 # New types
```

## Files to Delete

```
frontend/src/components/layout/Sidebar.tsx  # Replaced by BottomTabBar
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Data loss during migration | Parallel tables, keep old data |
| Navigation breaks existing flows | Feature flag for new nav |
| Performance with many notebooks | Virtual list, pagination |
| Offline sync complexity | Defer full sync to v2 |

---

## Success Metrics

From spec, validated against implementation:

- [x] 1 tap to any primary destination (bottom tab)
- [x] 2 taps to secondary (More → item)
- [x] Tab bar always visible
- [x] ≤3 taps from launch to first capture
- [x] Works without categorizing (tag optional)
- [x] Per-note export (CSV)
- [x] Touch targets ≥48px
- [x] Both themes supported

---

*Ready for implementation. Start with Phase 1 → Phase 2 for immediate visual impact.*
