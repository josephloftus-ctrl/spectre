# UI Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete UI overhaul with three-zone layout, Command Bar navigation, and consolidated views (Inbox, Issues, Inventory).

**Architecture:** Replace current bottom-tab mobile-first layout with a clean desktop-first three-zone layout (top nav, main workspace, context panel). Consolidate 23 pages into 3 main views. Add Command Bar (Cmd+K) for universal search and actions.

**Tech Stack:** React, TypeScript, Tailwind CSS, shadcn/ui, cmdk (for Command Bar)

---

## Phase 1: Foundation

### Task 1: Install Command Bar Dependency

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install cmdk**

Run: `cd frontend && npm install cmdk`

**Step 2: Verify installation**

Run: `npm list cmdk`
Expected: `cmdk@1.x.x`

**Step 3: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore: add cmdk for command bar"
```

---

### Task 2: Update Color Palette

**Files:**
- Modify: `frontend/src/index.css`

**Step 1: Update light theme as default with vibrant accent**

Replace the CSS variables in `index.css` with a clean light theme:

```css
@import "tailwindcss";
@config "../tailwind.config.js";

@layer base {
  /* Light theme (default) */
  :root {
    --background: 0 0% 98%;
    --foreground: 224 71% 4%;

    --card: 0 0% 100%;
    --card-foreground: 224 71% 4%;

    --popover: 0 0% 100%;
    --popover-foreground: 224 71% 4%;

    --primary: 199 89% 48%;
    --primary-foreground: 0 0% 100%;

    --secondary: 220 14% 96%;
    --secondary-foreground: 224 71% 4%;

    --muted: 220 14% 96%;
    --muted-foreground: 220 9% 46%;

    --accent: 199 89% 48%;
    --accent-foreground: 0 0% 100%;

    --destructive: 0 84% 60%;
    --destructive-foreground: 0 0% 100%;

    --success: 142 71% 45%;
    --success-foreground: 0 0% 100%;
    --warning: 38 92% 50%;
    --warning-foreground: 0 0% 0%;

    --border: 220 13% 91%;
    --input: 220 13% 91%;
    --ring: 199 89% 48%;

    --radius: 0.375rem;

    /* Layout */
    --nav-height: 56px;
    --context-panel-width: 400px;
  }

  /* Dark theme */
  .dark {
    --background: 224 71% 4%;
    --foreground: 213 31% 91%;

    --card: 224 71% 8%;
    --card-foreground: 213 31% 91%;

    --popover: 224 71% 8%;
    --popover-foreground: 213 31% 91%;

    --primary: 199 89% 48%;
    --primary-foreground: 0 0% 100%;

    --secondary: 215 28% 17%;
    --secondary-foreground: 213 31% 91%;

    --muted: 215 28% 17%;
    --muted-foreground: 217 10% 64%;

    --accent: 199 89% 48%;
    --accent-foreground: 0 0% 100%;

    --destructive: 0 63% 31%;
    --destructive-foreground: 0 0% 100%;

    --success: 142 71% 45%;
    --success-foreground: 0 0% 100%;
    --warning: 38 92% 50%;
    --warning-foreground: 0 0% 0%;

    --border: 215 28% 17%;
    --input: 215 28% 17%;
    --ring: 199 89% 48%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
    font-feature-settings: "rlig" 1, "calt" 1;
  }
}
```

**Step 2: Verify by running dev server**

Run: `cd frontend && npm run dev`
Expected: App loads with updated colors

**Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "style: update color palette - light default with vibrant accent"
```

---

### Task 3: Create New Layout Shell

**Files:**
- Create: `frontend/src/components/layout/AppShell.tsx`

**Step 1: Create the three-zone layout component**

```tsx
import { useState } from 'react'
import { TopNav } from './TopNav'
import { ContextPanel } from './ContextPanel'

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const [contextPanelOpen, setContextPanelOpen] = useState(false)
  const [contextContent, setContextContent] = useState<React.ReactNode>(null)

  const openContext = (content: React.ReactNode) => {
    setContextContent(content)
    setContextPanelOpen(true)
  }

  const closeContext = () => {
    setContextPanelOpen(false)
    setContextContent(null)
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation */}
      <TopNav />

      {/* Main Content Area */}
      <div className="flex pt-14">
        {/* Workspace */}
        <main className={`flex-1 transition-all duration-200 ${contextPanelOpen ? 'mr-[400px]' : ''}`}>
          <div className="p-6 max-w-6xl mx-auto">
            {children}
          </div>
        </main>

        {/* Context Panel */}
        <ContextPanel
          isOpen={contextPanelOpen}
          onClose={closeContext}
        >
          {contextContent}
        </ContextPanel>
      </div>
    </div>
  )
}
```

**Step 2: Verify file created**

Run: `cat frontend/src/components/layout/AppShell.tsx | head -5`
Expected: Shows import statements

**Step 3: Commit**

```bash
git add frontend/src/components/layout/AppShell.tsx
git commit -m "feat: add AppShell three-zone layout component"
```

---

### Task 4: Create Top Navigation

**Files:**
- Create: `frontend/src/components/layout/TopNav.tsx`

**Step 1: Create top navigation with tabs and command bar trigger**

```tsx
import { useLocation, useNavigate } from 'react-router-dom'
import { Search, Settings, Sun, Moon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/hooks'

const NAV_ITEMS = [
  { path: '/inbox', label: 'Inbox' },
  { path: '/issues', label: 'Issues' },
  { path: '/inventory', label: 'Inventory' },
]

export function TopNav() {
  const location = useLocation()
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-14 bg-background border-b border-border">
      <div className="h-full px-4 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-6">
          <button
            onClick={() => navigate('/')}
            className="text-lg font-semibold text-primary hover:opacity-80 transition-opacity"
          >
            Spectre
          </button>

          {/* Main Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive(item.path)
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Right Side Actions */}
        <div className="flex items-center gap-2">
          {/* Command Bar Trigger */}
          <Button
            variant="outline"
            size="sm"
            className="hidden md:flex items-center gap-2 text-muted-foreground"
            onClick={() => {
              // Will dispatch command bar open event
              window.dispatchEvent(new CustomEvent('open-command-bar'))
            }}
          >
            <Search className="h-4 w-4" />
            <span>Search...</span>
            <kbd className="ml-2 pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-xs font-medium text-muted-foreground">
              ⌘K
            </kbd>
          </Button>

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="h-9 w-9"
          >
            {theme === 'dark' ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>

          {/* Settings */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/settings')}
            className="h-9 w-9"
          >
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/layout/TopNav.tsx
git commit -m "feat: add TopNav component with tabs and command bar trigger"
```

---

### Task 5: Create Context Panel

**Files:**
- Create: `frontend/src/components/layout/ContextPanel.tsx`

**Step 1: Create sliding context panel**

```tsx
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ContextPanelProps {
  isOpen: boolean
  onClose: () => void
  children: React.ReactNode
  title?: string
}

export function ContextPanel({ isOpen, onClose, children, title }: ContextPanelProps) {
  return (
    <aside
      className={`fixed top-14 right-0 bottom-0 w-[400px] bg-card border-l border-border shadow-lg transform transition-transform duration-200 ease-in-out z-40 ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      {/* Panel Header */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-border">
        <h2 className="font-semibold text-foreground">
          {title || 'Details'}
        </h2>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="h-8 w-8"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Panel Content */}
      <div className="p-4 overflow-y-auto h-[calc(100%-56px)]">
        {children}
      </div>
    </aside>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/layout/ContextPanel.tsx
git commit -m "feat: add ContextPanel sliding detail panel"
```

---

### Task 6: Create Command Bar

**Files:**
- Create: `frontend/src/components/command/CommandBar.tsx`

**Step 1: Create command bar component using cmdk**

```tsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Command } from 'cmdk'
import {
  Inbox, AlertTriangle, Package, Search, Upload,
  FileText, Settings, Plus
} from 'lucide-react'

const NAVIGATION_ITEMS = [
  { id: 'inbox', label: 'Inbox', icon: Inbox, path: '/inbox' },
  { id: 'issues', label: 'Issues', icon: AlertTriangle, path: '/issues' },
  { id: 'inventory', label: 'Inventory', icon: Package, path: '/inventory' },
  { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
]

const ACTION_ITEMS = [
  { id: 'upload', label: 'Upload File', icon: Upload, action: 'upload' },
  { id: 'new-count', label: 'New Count Session', icon: Plus, action: 'new-count' },
  { id: 'export', label: 'Export Report', icon: FileText, action: 'export' },
]

export function CommandBar() {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const navigate = useNavigate()

  // Listen for keyboard shortcut and custom event
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen((prev) => !prev)
      }
      if (e.key === 'Escape') {
        setOpen(false)
      }
    }

    const handleOpenEvent = () => setOpen(true)

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('open-command-bar', handleOpenEvent)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('open-command-bar', handleOpenEvent)
    }
  }, [])

  const handleSelect = (item: typeof NAVIGATION_ITEMS[0] | typeof ACTION_ITEMS[0]) => {
    if ('path' in item) {
      navigate(item.path)
    } else {
      // Handle actions
      console.log('Action:', item.action)
      // TODO: Implement action handlers
    }
    setOpen(false)
    setSearch('')
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[100]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />

      {/* Command Dialog */}
      <div className="absolute top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg">
        <Command
          className="rounded-lg border border-border shadow-2xl bg-card overflow-hidden"
          shouldFilter={true}
        >
          <div className="flex items-center border-b border-border px-3">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
            <Command.Input
              value={search}
              onValueChange={setSearch}
              placeholder="Search or type a command..."
              className="flex h-12 w-full rounded-md bg-transparent py-3 px-2 text-sm outline-none placeholder:text-muted-foreground"
              autoFocus
            />
          </div>

          <Command.List className="max-h-80 overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
              No results found.
            </Command.Empty>

            <Command.Group heading="Navigation" className="text-xs text-muted-foreground px-2 py-1.5">
              {NAVIGATION_ITEMS.map((item) => (
                <Command.Item
                  key={item.id}
                  value={item.label}
                  onSelect={() => handleSelect(item)}
                  className="flex items-center gap-3 px-2 py-2 rounded-md cursor-pointer text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
                >
                  <item.icon className="h-4 w-4 text-muted-foreground" />
                  {item.label}
                </Command.Item>
              ))}
            </Command.Group>

            <Command.Group heading="Actions" className="text-xs text-muted-foreground px-2 py-1.5 mt-2">
              {ACTION_ITEMS.map((item) => (
                <Command.Item
                  key={item.id}
                  value={item.label}
                  onSelect={() => handleSelect(item)}
                  className="flex items-center gap-3 px-2 py-2 rounded-md cursor-pointer text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
                >
                  <item.icon className="h-4 w-4 text-muted-foreground" />
                  {item.label}
                </Command.Item>
              ))}
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  )
}
```

**Step 2: Create command directory index**

Create `frontend/src/components/command/index.ts`:

```ts
export { CommandBar } from './CommandBar'
```

**Step 3: Commit**

```bash
git add frontend/src/components/command/
git commit -m "feat: add CommandBar component with Cmd+K shortcut"
```

---

### Task 7: Update Layout Exports

**Files:**
- Modify: `frontend/src/components/layout/index.ts` (create if doesn't exist)

**Step 1: Create/update layout index**

```ts
export { AppShell } from './AppShell'
export { TopNav } from './TopNav'
export { ContextPanel } from './ContextPanel'
export { DashboardLayout } from './DashboardLayout'
```

**Step 2: Commit**

```bash
git add frontend/src/components/layout/index.ts
git commit -m "feat: export new layout components"
```

---

### Task 8: Integrate New Layout in App

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Replace DashboardLayout with AppShell and add CommandBar**

```tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { CommandBar } from '@/components/command'
import {
  DashboardPage, DocumentsPage, NotesPage, SettingsPage,
  SitePage, AssistantPage, SearchPage, InventoryPage,
  PurchaseMatchDetailPage, PurchaseMatchCategoryPage,
  CartPage, CountSessionPage, OffCatalogPage, RoomsPage
} from '@/pages'

function App() {
  return (
    <>
      <CommandBar />
      <AppShell>
        <Routes>
          {/* Main Views */}
          <Route path="/" element={<Navigate to="/inbox" replace />} />
          <Route path="/inbox" element={<DocumentsPage />} />
          <Route path="/issues" element={<DashboardPage />} />
          <Route path="/inventory" element={<InventoryPage />} />

          {/* Inventory sub-routes */}
          <Route path="/inventory/site/:siteId" element={<SitePage />} />
          <Route path="/inventory/match/:unit" element={<PurchaseMatchDetailPage />} />
          <Route path="/inventory/match/category/:category" element={<PurchaseMatchCategoryPage />} />

          {/* Utility pages */}
          <Route path="/cart" element={<CartPage />} />
          <Route path="/count" element={<CountSessionPage />} />
          <Route path="/off-catalog" element={<OffCatalogPage />} />
          <Route path="/rooms" element={<RoomsPage />} />
          <Route path="/notes" element={<NotesPage />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/settings" element={<SettingsPage />} />

          {/* Legacy redirects */}
          <Route path="/documents" element={<Navigate to="/inbox" replace />} />
          <Route path="/scores" element={<Navigate to="/inventory?tab=health" replace />} />
          <Route path="/history" element={<Navigate to="/inventory?tab=history" replace />} />
          <Route path="/purchase-match" element={<Navigate to="/inventory?tab=match" replace />} />
          <Route path="/collections" element={<Navigate to="/search?tab=collections" replace />} />
          <Route path="/ai" element={<Navigate to="/assistant" replace />} />
          <Route path="/standup" element={<Navigate to="/assistant" replace />} />
          <Route path="/glance" element={<Navigate to="/issues" replace />} />
          <Route path="/system" element={<Navigate to="/settings?debug=1" replace />} />

          {/* Legacy site routes */}
          <Route path="/site/:siteId" element={<SitePage />} />
          <Route path="/:siteId" element={<SitePage />} />
        </Routes>
      </AppShell>
    </>
  )
}

export default App
```

**Step 2: Test the app**

Run: `cd frontend && npm run dev`
Expected: App loads with new three-zone layout, Command Bar works with Cmd+K

**Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: integrate new AppShell layout and CommandBar"
```

---

## Phase 2: Inbox View (Tasks 9-12)

### Task 9: Create Inbox Page Shell

**Files:**
- Create: `frontend/src/pages/InboxPage.tsx`

**Step 1: Create the Inbox page with file queue and preview layout**

```tsx
import { useState } from 'react'
import { Upload, FileText, CheckCircle, AlertCircle, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

// Status types for files
type FileStatus = 'pending' | 'processing' | 'needs_review' | 'complete'

interface InboxFile {
  id: string
  name: string
  status: FileStatus
  uploadedAt: Date
  detectedDate?: string
  confidence?: 'high' | 'low'
}

const STATUS_CONFIG = {
  pending: { icon: Clock, label: 'Pending', className: 'text-muted-foreground' },
  processing: { icon: Clock, label: 'Processing', className: 'text-primary animate-pulse' },
  needs_review: { icon: AlertCircle, label: 'Needs Review', className: 'text-warning' },
  complete: { icon: CheckCircle, label: 'Complete', className: 'text-success' },
}

export function InboxPage() {
  const [files, setFiles] = useState<InboxFile[]>([])
  const [selectedFile, setSelectedFile] = useState<InboxFile | null>(null)

  return (
    <div className="h-[calc(100vh-7rem)]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Inbox</h1>
          <p className="text-muted-foreground">Upload and validate files before processing</p>
        </div>
        <Button className="gap-2">
          <Upload className="h-4 w-4" />
          Upload Files
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100%-5rem)]">
        {/* File Queue */}
        <Card className="p-4 overflow-hidden flex flex-col">
          <h2 className="font-medium mb-4">File Queue</h2>

          {files.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
              <FileText className="h-12 w-12 mb-4 opacity-50" />
              <p>No files in queue</p>
              <p className="text-sm">Upload files to get started</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto space-y-2">
              {files.map((file) => {
                const statusConfig = STATUS_CONFIG[file.status]
                const StatusIcon = statusConfig.icon
                return (
                  <button
                    key={file.id}
                    onClick={() => setSelectedFile(file)}
                    className={`w-full p-3 rounded-lg border text-left transition-colors ${
                      selectedFile?.id === file.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="h-5 w-5 text-muted-foreground" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{file.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {file.detectedDate || 'Processing...'}
                        </p>
                      </div>
                      <StatusIcon className={`h-5 w-5 ${statusConfig.className}`} />
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </Card>

        {/* Preview Pane */}
        <Card className="p-4 overflow-hidden flex flex-col">
          <h2 className="font-medium mb-4">Preview</h2>

          {!selectedFile ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
              <p>Select a file to preview</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto">
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-muted-foreground">File Name</label>
                  <p className="font-medium">{selectedFile.name}</p>
                </div>

                <div>
                  <label className="text-sm text-muted-foreground">Detected Date</label>
                  <div className="flex items-center gap-2">
                    <p className="font-medium">{selectedFile.detectedDate || '—'}</p>
                    {selectedFile.confidence === 'low' && (
                      <span className="text-xs px-2 py-0.5 rounded bg-warning/10 text-warning">
                        Please verify
                      </span>
                    )}
                  </div>
                </div>

                <div className="pt-4 flex gap-2">
                  <Button className="flex-1">Accept</Button>
                  <Button variant="outline" className="flex-1">Override Date</Button>
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
```

**Step 2: Export from pages index**

Add to `frontend/src/pages/index.ts`:
```ts
export { InboxPage } from './InboxPage'
```

**Step 3: Commit**

```bash
git add frontend/src/pages/InboxPage.tsx frontend/src/pages/index.ts
git commit -m "feat: add InboxPage with file queue and preview layout"
```

---

### Task 10: Create Issues Page Shell

**Files:**
- Create: `frontend/src/pages/IssuesPage.tsx`

**Step 1: Create Issues page with ranked issue list**

```tsx
import { useState } from 'react'
import { AlertTriangle, TrendingUp, DollarSign, Calendar } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface Issue {
  id: string
  title: string
  type: 'variance' | 'missing' | 'duplicate' | 'pattern'
  dollarImpact: number
  occurrenceCount: number
  lastSeen: Date
  itemName: string
  location: string
}

export function IssuesPage() {
  const [issues, setIssues] = useState<Issue[]>([])
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null)

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Issues</h1>
        <p className="text-muted-foreground">Ranked by dollar impact and frequency</p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-destructive/10">
              <AlertTriangle className="h-5 w-5 text-destructive" />
            </div>
            <div>
              <p className="text-2xl font-semibold">{issues.length}</p>
              <p className="text-sm text-muted-foreground">Open Issues</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning/10">
              <DollarSign className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-semibold">
                {formatCurrency(issues.reduce((sum, i) => sum + i.dollarImpact, 0))}
              </p>
              <p className="text-sm text-muted-foreground">Total Impact</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <TrendingUp className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-semibold">
                {issues.filter(i => i.occurrenceCount > 1).length}
              </p>
              <p className="text-sm text-muted-foreground">Recurring Patterns</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Issue List */}
      <Card className="divide-y divide-border">
        {issues.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No open issues</p>
            <p className="text-sm">Issues will appear here when detected</p>
          </div>
        ) : (
          issues.map((issue) => (
            <button
              key={issue.id}
              onClick={() => setSelectedIssue(issue)}
              className="w-full p-4 text-left hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-medium truncate">{issue.itemName}</p>
                    <Badge variant="outline" className="text-xs">
                      {issue.type}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground truncate">
                    {issue.location}
                  </p>
                </div>

                <div className="text-right">
                  <p className="font-semibold text-destructive">
                    {formatCurrency(issue.dollarImpact)}
                  </p>
                  {issue.occurrenceCount > 1 && (
                    <p className="text-xs text-muted-foreground">
                      {issue.occurrenceCount}x this month
                    </p>
                  )}
                </div>
              </div>
            </button>
          ))
        )}
      </Card>
    </div>
  )
}
```

**Step 2: Export from pages index**

Add to `frontend/src/pages/index.ts`:
```ts
export { IssuesPage } from './IssuesPage'
```

**Step 3: Commit**

```bash
git add frontend/src/pages/IssuesPage.tsx frontend/src/pages/index.ts
git commit -m "feat: add IssuesPage with ranked issue list"
```

---

### Task 11: Update App Routes for New Pages

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Update routes to use new pages**

Update the imports and routes in App.tsx to use InboxPage and IssuesPage:

```tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { CommandBar } from '@/components/command'
import {
  InboxPage, IssuesPage, InventoryPage,
  NotesPage, SettingsPage, SitePage, AssistantPage, SearchPage,
  PurchaseMatchDetailPage, PurchaseMatchCategoryPage,
  CartPage, CountSessionPage, OffCatalogPage, RoomsPage
} from '@/pages'

function App() {
  return (
    <>
      <CommandBar />
      <AppShell>
        <Routes>
          {/* Main Views */}
          <Route path="/" element={<Navigate to="/inbox" replace />} />
          <Route path="/inbox" element={<InboxPage />} />
          <Route path="/issues" element={<IssuesPage />} />
          <Route path="/inventory" element={<InventoryPage />} />

          {/* Rest of routes remain the same... */}
          <Route path="/inventory/site/:siteId" element={<SitePage />} />
          <Route path="/inventory/match/:unit" element={<PurchaseMatchDetailPage />} />
          <Route path="/inventory/match/category/:category" element={<PurchaseMatchCategoryPage />} />

          <Route path="/cart" element={<CartPage />} />
          <Route path="/count" element={<CountSessionPage />} />
          <Route path="/off-catalog" element={<OffCatalogPage />} />
          <Route path="/rooms" element={<RoomsPage />} />
          <Route path="/notes" element={<NotesPage />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/settings" element={<SettingsPage />} />

          {/* Legacy redirects */}
          <Route path="/documents" element={<Navigate to="/inbox" replace />} />
          <Route path="/scores" element={<Navigate to="/inventory?tab=health" replace />} />
          <Route path="/history" element={<Navigate to="/inventory?tab=history" replace />} />
          <Route path="/purchase-match" element={<Navigate to="/inventory?tab=match" replace />} />
          <Route path="/collections" element={<Navigate to="/search?tab=collections" replace />} />
          <Route path="/ai" element={<Navigate to="/assistant" replace />} />
          <Route path="/standup" element={<Navigate to="/assistant" replace />} />
          <Route path="/glance" element={<Navigate to="/issues" replace />} />
          <Route path="/system" element={<Navigate to="/settings?debug=1" replace />} />

          <Route path="/site/:siteId" element={<SitePage />} />
          <Route path="/:siteId" element={<SitePage />} />
        </Routes>
      </AppShell>
    </>
  )
}

export default App
```

**Step 2: Verify app runs**

Run: `cd frontend && npm run dev`
Expected: App loads, navigation between Inbox/Issues/Inventory works

**Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: update routes to use new InboxPage and IssuesPage"
```

---

### Task 12: Build Frontend and Verify

**Files:**
- None (verification only)

**Step 1: Build frontend**

Run: `cd frontend && npm run build`
Expected: Build completes without errors

**Step 2: Commit all remaining changes**

```bash
git add -A
git commit -m "feat: complete Phase 1 & 2 - new layout and core pages"
```

---

## Summary

**Phase 1 (Tasks 1-8):** Foundation
- Install cmdk dependency
- Update color palette (light default, vibrant accent)
- Create AppShell three-zone layout
- Create TopNav with tabs
- Create ContextPanel
- Create CommandBar (Cmd+K)
- Integrate in App.tsx

**Phase 2 (Tasks 9-12):** Core Pages
- Create InboxPage with file queue/preview
- Create IssuesPage with ranked list
- Update routing
- Verify build

**Future Phases (not in this plan):**
- Phase 3: Inbox functionality (file upload, date validation, backend integration)
- Phase 4: Issues functionality (real data, filtering, actions)
- Phase 5: Inventory consolidation
- Phase 6: Context Panel integration
- Phase 7: Polish and animations
