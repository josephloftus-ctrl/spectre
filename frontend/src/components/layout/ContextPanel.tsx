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
    <>
      {/* Backdrop overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-30 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-[60px] right-0 bottom-0 w-[var(--context-panel-width)] bg-card/95 backdrop-blur-xl border-l border-border shadow-2xl transform transition-transform duration-300 ease-out z-40 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Panel Header */}
        <div className="h-[60px] px-5 flex items-center justify-between border-b border-border bg-card/50">
          <h2 className="font-semibold font-head text-foreground tracking-tight">
            {title || 'Details'}
          </h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-9 w-9 text-muted-foreground hover:text-foreground hover:bg-muted"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Panel Content */}
        <div className="p-5 overflow-y-auto h-[calc(100%-60px)]">
          {children}
        </div>
      </aside>
    </>
  )
}
