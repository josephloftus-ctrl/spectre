import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Command } from 'cmdk'
import {
  Inbox, AlertTriangle, Package, Search, Upload,
  FileText, Settings, Plus, Building2, ShoppingCart,
  ClipboardList, MessageSquare, BookOpen, ChefHat
} from 'lucide-react'
import { fetchScores, formatSiteName, type UnitScore } from '@/lib/api'
import { cn } from '@/lib/utils'

const NAVIGATION_ITEMS = [
  { id: 'inbox', label: 'Inbox', icon: Inbox, path: '/inbox', keywords: 'upload files documents' },
  { id: 'issues', label: 'Issues', icon: AlertTriangle, path: '/issues', keywords: 'flags problems errors' },
  { id: 'inventory', label: 'Inventory', icon: Package, path: '/inventory', keywords: 'sites scores health' },
  { id: 'cart', label: 'Cart', icon: ShoppingCart, path: '/cart', keywords: 'order buy purchase' },
  { id: 'count', label: 'Count Session', icon: ClipboardList, path: '/count', keywords: 'counting physical' },
  { id: 'menu', label: 'Menu Planning', icon: ChefHat, path: '/menu-planning', keywords: 'menu cycle promo recipes' },
  { id: 'notes', label: 'Notes', icon: BookOpen, path: '/notes', keywords: 'memo quick capture' },
  { id: 'assistant', label: 'Assistant', icon: MessageSquare, path: '/assistant', keywords: 'ai chat help' },
  { id: 'search', label: 'Search', icon: Search, path: '/search', keywords: 'find lookup query' },
  { id: 'settings', label: 'Settings', icon: Settings, path: '/settings', keywords: 'config preferences' },
]

const STATUS_DOT: Record<string, string> = {
  critical: 'bg-red-500',
  warning: 'bg-amber-500',
  healthy: 'bg-emerald-500',
  clean: 'bg-emerald-400',
}

export function CommandBar() {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [sites, setSites] = useState<UnitScore[]>([])
  const navigate = useNavigate()

  // Load sites when command bar opens
  const loadSites = useCallback(async () => {
    try {
      const { units } = await fetchScores({ limit: 100 })
      setSites(units)
    } catch {
      // Silently fail - sites just won't appear
    }
  }, [])

  useEffect(() => {
    if (open && sites.length === 0) {
      loadSites()
    }
  }, [open, sites.length, loadSites])

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

  const handleNavigate = (path: string) => {
    navigate(path)
    setOpen(false)
    setSearch('')
  }

  const handleAction = (action: string) => {
    setOpen(false)
    setSearch('')

    switch (action) {
      case 'upload':
        navigate('/inbox')
        // Trigger upload dialog after navigation
        setTimeout(() => {
          const uploadBtn = document.querySelector('[data-upload-trigger]') as HTMLButtonElement
          uploadBtn?.click()
        }, 100)
        break
      case 'new-count':
        navigate('/count')
        break
      case 'export':
        navigate('/inventory')
        break
    }
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
      <div className="absolute top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg px-4">
        <Command
          className="rounded-lg border border-border shadow-2xl bg-card overflow-hidden"
          shouldFilter={true}
        >
          <div className="flex items-center border-b border-border px-3">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
            <Command.Input
              value={search}
              onValueChange={setSearch}
              placeholder="Jump to site, page, or action..."
              className="flex h-12 w-full rounded-md bg-transparent py-3 px-2 text-sm outline-none placeholder:text-muted-foreground"
              autoFocus
            />
            <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border bg-muted px-1.5 text-[10px] font-medium text-muted-foreground">
              ESC
            </kbd>
          </div>

          <Command.List className="max-h-80 overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
              No results found.
            </Command.Empty>

            {/* Sites - show when searching or always show top few */}
            {sites.length > 0 && (
              <Command.Group heading="Sites" className="text-xs text-muted-foreground px-2 py-1.5">
                {sites.map((site) => (
                  <Command.Item
                    key={site.site_id}
                    value={`${formatSiteName(site.site_id)} ${site.site_id}`}
                    onSelect={() => handleNavigate(`/inventory/site/${encodeURIComponent(site.site_id)}`)}
                    className="flex items-center gap-3 px-2 py-2 rounded-md cursor-pointer text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
                  >
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1">{formatSiteName(site.site_id)}</span>
                    <div className="flex items-center gap-2">
                      {site.item_flags > 0 && (
                        <span className="text-xs text-muted-foreground">{site.item_flags} flags</span>
                      )}
                      <div className={cn('h-2 w-2 rounded-full', STATUS_DOT[site.status] || 'bg-gray-400')} />
                    </div>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            <Command.Group heading="Pages" className="text-xs text-muted-foreground px-2 py-1.5">
              {NAVIGATION_ITEMS.map((item) => (
                <Command.Item
                  key={item.id}
                  value={`${item.label} ${item.keywords}`}
                  onSelect={() => handleNavigate(item.path)}
                  className="flex items-center gap-3 px-2 py-2 rounded-md cursor-pointer text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
                >
                  <item.icon className="h-4 w-4 text-muted-foreground" />
                  {item.label}
                </Command.Item>
              ))}
            </Command.Group>

            <Command.Group heading="Actions" className="text-xs text-muted-foreground px-2 py-1.5 mt-2">
              <Command.Item
                value="Upload File import add"
                onSelect={() => handleAction('upload')}
                className="flex items-center gap-3 px-2 py-2 rounded-md cursor-pointer text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
              >
                <Upload className="h-4 w-4 text-muted-foreground" />
                Upload File
              </Command.Item>
              <Command.Item
                value="New Count Session start counting"
                onSelect={() => handleAction('new-count')}
                className="flex items-center gap-3 px-2 py-2 rounded-md cursor-pointer text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
              >
                <Plus className="h-4 w-4 text-muted-foreground" />
                New Count Session
              </Command.Item>
              <Command.Item
                value="Export Report download"
                onSelect={() => handleAction('export')}
                className="flex items-center gap-3 px-2 py-2 rounded-md cursor-pointer text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
              >
                <FileText className="h-4 w-4 text-muted-foreground" />
                Export Report
              </Command.Item>
            </Command.Group>
          </Command.List>

          <div className="border-t border-border px-3 py-2 flex items-center justify-between text-[10px] text-muted-foreground">
            <div className="flex gap-3">
              <span><kbd className="font-mono">↑↓</kbd> navigate</span>
              <span><kbd className="font-mono">↵</kbd> select</span>
            </div>
            <span><kbd className="font-mono">⌘K</kbd> toggle</span>
          </div>
        </Command>
      </div>
    </div>
  )
}
