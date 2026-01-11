import { useState, useEffect, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Plus, X, StickyNote, AlertCircle, ClipboardList } from 'lucide-react'
import { cn } from '@/lib/utils'

interface FABAction {
  icon: React.ComponentType<{ className?: string }>
  label: string
  onClick: () => void
}

interface FABProps {
  onAddNote?: () => void
  onReportIssue?: () => void
  onQuickCount?: () => void
}

export function FAB({ onAddNote, onReportIssue, onQuickCount }: FABProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()

  // Close menu on route change
  useEffect(() => {
    setIsExpanded(false)
  }, [location.pathname])

  // Close on escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isExpanded) {
        setIsExpanded(false)
      }
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isExpanded])

  const handleAddNote = useCallback(() => {
    setIsExpanded(false)
    if (onAddNote) {
      onAddNote()
    } else {
      navigate('/notes')
    }
  }, [onAddNote, navigate])

  const handleReportIssue = useCallback(() => {
    setIsExpanded(false)
    if (onReportIssue) {
      onReportIssue()
    }
    // TODO: Implement issue reporting
  }, [onReportIssue])

  const handleQuickCount = useCallback(() => {
    setIsExpanded(false)
    if (onQuickCount) {
      onQuickCount()
    }
    // TODO: Implement quick count
  }, [onQuickCount])

  const actions: FABAction[] = [
    { icon: StickyNote, label: 'Add Note', onClick: handleAddNote },
    { icon: AlertCircle, label: 'Report Issue', onClick: handleReportIssue },
    { icon: ClipboardList, label: 'Quick Count', onClick: handleQuickCount },
  ]

  return (
    <>
      {/* Backdrop when expanded */}
      {isExpanded && (
        <div
          className="fixed inset-0 z-[45] bg-black/20 animate-fade-in"
          onClick={() => setIsExpanded(false)}
        />
      )}

      {/* FAB Container - positioned higher to not crowd bottom nav */}
      <div
        className="fixed z-[46] right-5 bottom-[104px]"
      >
        {/* Speed dial menu */}
        <div
          className={cn(
            "absolute bottom-16 right-0 flex flex-col gap-3",
            "transition-all duration-200",
            isExpanded
              ? "opacity-100 translate-y-0 pointer-events-auto"
              : "opacity-0 translate-y-4 pointer-events-none"
          )}
        >
          {actions.map((action, index) => {
            const Icon = action.icon
            return (
              <button
                key={action.label}
                onClick={action.onClick}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 bg-card rounded-full shadow-md",
                  "hover:bg-muted transition-colors whitespace-nowrap",
                  isExpanded && "animate-fab-expand"
                )}
                style={{
                  animationDelay: `${index * 50}ms`,
                }}
              >
                <Icon className="h-5 w-5 text-primary" />
                <span className="text-sm font-medium text-foreground">{action.label}</span>
              </button>
            )
          })}
        </div>

        {/* Main FAB button */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={cn(
            "w-14 h-14 rounded-full bg-primary text-primary-foreground",
            "flex items-center justify-center",
            "shadow-lg hover:bg-accent-dark active:scale-95",
            "transition-all duration-200"
          )}
          style={{ boxShadow: 'var(--shadow-fab)' }}
        >
          <div
            className={cn(
              "transition-transform duration-200",
              isExpanded && "rotate-45"
            )}
          >
            {isExpanded ? <X className="h-6 w-6" /> : <Plus className="h-6 w-6" />}
          </div>
        </button>
      </div>
    </>
  )
}
