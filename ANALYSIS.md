# Spectre Codebase Analysis

> Generated 2026-01-17

---

## Architecture Overview

**Current Stack:**
- **Backend**: FastAPI with 26 routers (~3,800 lines total), SQLite + ChromaDB, Ollama integration
- **Frontend**: React 18 + Vite + TailwindCSS + shadcn/ui, ~24 pages, 8 custom hooks
- **AI**: Local Ollama (granite4:3b) for chat/analysis, nomic-embed-text for embeddings, optional Claude proxy

**Domain**: Food service inventory management with AI-powered analysis, document parsing, semantic search, health scoring, and purchase matching.

---

## Simplification Opportunities

### 1. Consolidate Routers (High Impact)

26 routers, many under 100 lines. Suggested merges:

| Merge These | Into | Reason |
|-------------|------|--------|
| `memory.py`, `helpdesk.py`, `standup.py` | `ai.py` | All AI/LLM features |
| `counting.py`, `locations.py`, `rooms.py`, `snapshots.py` | `inventory_ops.py` | All inventory operations |
| `cart.py`, `catalog.py` | `ordering.py` | Both relate to ordering |

This would reduce 26 routers → ~12-15.

### 2. Remove Legacy Pages/Routes

`App.tsx` has many redirects for old routes. These legacy pages can be deleted:
- `AIPage.tsx`
- `GlancePage.tsx`
- `HistoryPage.tsx`
- `InboxPage.tsx`
- `ScoresPage.tsx`
- `StandupPage.tsx`
- `SystemPage.tsx`
- `CollectionsPage.tsx`
- `PurchaseMatchPage.tsx`

### 3. Simplify Database Layer

`database.py` is just a re-export wrapper around `backend/core/db/`. Remove the indirection - import directly from `backend.core.db`.

### 4. Deduplicate Flag Checking Logic

`flag_checker.py` (591 lines) has repeated key parsing patterns. Extract a `parse_row_fields(row)` helper that normalizes all common fields once.

### 5. Split Frontend API Client

`api.ts` is 1,500+ lines with 100+ exported functions. Split into:

```
lib/api/
├── inventory.ts
├── search.ts
├── cart.ts
├── scores.ts
├── files.ts
└── index.ts  (re-exports)
```

---

## New Feature Opportunities

### 1. Real-Time Sync / WebSockets

Currently polling-based. Adding WebSocket support for:
- Live file processing status
- Real-time score updates
- Multi-user count sessions

### 2. Mobile PWA Enhancements

Already have FAB and BottomTabBar components. Add:
- Offline mode with service worker
- Camera-based barcode scanning for counts
- Push notifications for critical alerts

### 3. Predictive Ordering

Use historical data to:
- Suggest reorder quantities based on consumption patterns
- Predict when items will run low
- Auto-populate cart from usage trends

### 4. Multi-Tenant / Team Features

- User accounts and role-based access
- Audit trail (who changed what)
- Team assignments per site

### 5. Enhanced AI Features

- **Voice commands**: Already have `useVoice.ts` - expand to voice-controlled counts
- **Document Q&A**: Chat directly with uploaded PDFs/Excel files
- **Auto-categorization**: Use LLM to suggest room assignments for new items

### 6. Integration Hooks

- Webhook support for external systems
- Direct vendor API integration (auto-pull catalog updates)
- Export to accounting systems (QuickBooks, etc.)

### 7. Analytics Dashboard

- Historical trend charts (data exists in history)
- Variance reports over time
- Cost center breakdown

---

## Quick Wins (Low Effort, High Value)

1. **Delete the 9+ unused page files** - immediate cleanup
2. **Add TypeScript strict mode** - catch bugs early
3. **Consolidate the 3 AI routers** into one - reduce complexity
4. **Add loading skeletons** - `skeleton.tsx` exists, use it more
5. **Split api.ts** - better code organization and tree-shaking

---

## Complexity Hotspots

| File | Lines | Notes |
|------|-------|-------|
| `purchase_match.py` | 484 | Core business logic, consider service layer extraction |
| `flag_checker.py` | 591 | Repeated patterns, needs helper extraction |
| `export.py` | 329 | Template filling logic, could be simplified |
| `api.ts` (frontend) | 1505 | Should be split into modules |

---

## In Progress

- [ ] Desktop layout with collapsible sidebar
- [ ] Keep mobile nav for smaller screens
- [ ] Responsive breakpoint switching
