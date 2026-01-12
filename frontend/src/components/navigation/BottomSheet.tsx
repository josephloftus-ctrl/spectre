import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { StickyNote, Search, Settings, Circle, ShoppingCart, ClipboardList } from 'lucide-react'
import { cn } from '@/lib/utils'

interface BottomSheetProps {
  isOpen: boolean
  onClose: () => void
}

interface SheetItem {
  icon: React.ComponentType<{ className?: string }>
  label: string
  path: string
}

const sheetItems: SheetItem[] = [
  { icon: Search, label: 'Search', path: '/search' },
  { icon: ShoppingCart, label: 'Cart', path: '/cart' },
  { icon: ClipboardList, label: 'Count', path: '/count' },
  { icon: StickyNote, label: 'Notes', path: '/notes' },
  { icon: Settings, label: 'Settings', path: '/settings' },
]

export function BottomSheet({ isOpen, onClose }: BottomSheetProps) {
  const navigate = useNavigate()

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  const handleItemClick = useCallback((path: string) => {
    navigate(path)
    onClose()
  }, [navigate, onClose])

  if (!isOpen) return null

  return (
    <>
      {/* Overlay */}
      <div
        className={cn(
          "fixed inset-0 z-[60] bg-black/50",
          isOpen ? "animate-fade-in" : "animate-fade-out"
        )}
        onClick={onClose}
      />

      {/* Sheet */}
      <div
        className={cn(
          "fixed bottom-0 left-0 right-0 z-[61] bg-card rounded-t-2xl",
          "max-h-[70vh] overflow-y-auto",
          isOpen ? "animate-slide-up" : "animate-slide-down"
        )}
        style={{ paddingBottom: 'calc(20px + env(safe-area-inset-bottom))' }}
      >
        {/* Handle */}
        <div className="flex justify-center pt-3 pb-5">
          <div className="w-9 h-1 bg-muted-foreground/30 rounded-full" />
        </div>

        {/* Menu items */}
        <div className="px-5 space-y-1">
          {sheetItems.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.path}
                onClick={() => handleItemClick(item.path)}
                className={cn(
                  "w-full flex items-center gap-4 h-14 px-2 rounded-lg",
                  "text-foreground hover:bg-muted/50 active:bg-muted transition-colors"
                )}
              >
                <Icon className="h-6 w-6 text-muted-foreground" />
                <span className="text-base">{item.label}</span>
              </button>
            )
          })}

          {/* Divider */}
          <div className="h-px bg-border my-2" />

          {/* Status indicator */}
          <div className="flex items-center gap-3 px-2 py-3 text-muted-foreground">
            <Circle className="h-2 w-2 fill-emerald-500 text-emerald-500" />
            <span className="text-sm">Systems Operational</span>
          </div>
        </div>
      </div>
    </>
  )
}
