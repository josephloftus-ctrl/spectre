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
