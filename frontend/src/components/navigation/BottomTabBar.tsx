import { useLocation, useNavigate } from 'react-router-dom'
import { Home, Package, Files, Bot, MoreHorizontal } from 'lucide-react'
import { cn } from '@/lib/utils'

interface TabItem {
  path: string
  icon: React.ComponentType<{ className?: string }>
  label: string
  isMore?: boolean
}

interface BottomTabBarProps {
  onMoreClick: () => void
}

export function BottomTabBar({ onMoreClick }: BottomTabBarProps) {
  const location = useLocation()
  const navigate = useNavigate()

  const tabs: TabItem[] = [
    { path: '/', icon: Home, label: 'Home' },
    { path: '/inventory', icon: Package, label: 'Inventory' },
    { path: '/documents', icon: Files, label: 'Docs' },
    { path: '/assistant', icon: Bot, label: 'Assistant' },
    { path: 'more', icon: MoreHorizontal, label: 'More', isMore: true },
  ]

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  // Check if we're on a "More" menu page
  const isMoreActive = ['/search', '/notes', '/settings'].some(
    p => location.pathname.startsWith(p)
  )

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 bg-card border-t border-border pb-[env(safe-area-inset-bottom)]"
    >
      <div className="flex justify-around items-stretch h-14">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const active = tab.isMore ? isMoreActive : isActive(tab.path)

          return (
            <button
              key={tab.path}
              onClick={() => tab.isMore ? onMoreClick() : navigate(tab.path)}
              className={cn(
                "flex flex-col items-center justify-center flex-1 max-w-[80px] py-2",
                "transition-colors duration-150",
                active ? "text-primary" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <div className="relative flex items-center justify-center">
                <Icon className="h-5 w-5" />
              </div>
              <span className="text-[10px] font-medium mt-0.5 leading-tight">{tab.label}</span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
