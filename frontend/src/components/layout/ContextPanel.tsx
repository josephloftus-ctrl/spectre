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
