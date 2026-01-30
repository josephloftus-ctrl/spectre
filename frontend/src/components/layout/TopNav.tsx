import { useLocation, useNavigate } from 'react-router-dom'
import { Search, Settings, Sun, Moon, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/hooks'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard' },
  { path: '/inbox', label: 'Inbox' },
  { path: '/issues', label: 'Issues' },
  { path: '/inventory', label: 'Inventory' },
  { path: '/assistant', label: 'Assistant' },
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
    <header className="fixed top-0 left-0 right-0 z-50 h-[60px] bg-background/80 backdrop-blur-xl border-b border-border">
      <div className="h-full px-6 flex items-center justify-between">
        {/* Logo & Navigation */}
        <div className="flex items-center gap-8">
          {/* Logo */}
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 group"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center shadow-md group-hover:shadow-lg group-hover:shadow-primary/20 transition-all">
              <Zap className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="text-lg font-bold font-head tracking-tight text-foreground">
              Spectre
            </span>
          </button>

          {/* Separator */}
          <div className="hidden md:block h-6 w-px bg-border" />

          {/* Main Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={cn(
                  "relative px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200",
                  isActive(item.path)
                    ? "text-primary-foreground bg-primary shadow-md shadow-primary/25"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                )}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Right Side Actions */}
        <div className="flex items-center gap-3">
          {/* Command Bar Trigger */}
          <Button
            variant="outline"
            size="sm"
            className="hidden md:flex items-center gap-3 text-muted-foreground bg-muted/50 border-border hover:bg-muted hover:text-foreground h-9 px-4"
            onClick={() => {
              window.dispatchEvent(new CustomEvent('open-command-bar'))
            }}
          >
            <Search className="h-4 w-4" />
            <span className="text-sm">Search</span>
            <div className="flex items-center gap-0.5">
              <kbd className="inline-flex h-5 items-center rounded border border-border bg-background px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                ⌘
              </kbd>
              <kbd className="inline-flex h-5 items-center rounded border border-border bg-background px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                K
              </kbd>
            </div>
          </Button>

          {/* Separator */}
          <div className="hidden md:block h-6 w-px bg-border" />

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="h-9 w-9 text-muted-foreground hover:text-foreground"
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
            className="h-9 w-9 text-muted-foreground hover:text-foreground"
          >
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  )
}
