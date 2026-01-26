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
