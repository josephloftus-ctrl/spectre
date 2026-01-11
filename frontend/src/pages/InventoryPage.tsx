import { useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Activity, History, ArrowRightLeft } from 'lucide-react'
import { cn } from '@/lib/utils'

// Import existing page content
import { ScoresPage } from './ScoresPage'
import { HistoryPage } from './HistoryPage'
import { PurchaseMatchPage } from './PurchaseMatchPage'

type TabKey = 'health' | 'history' | 'match'

interface Tab {
  key: TabKey
  label: string
  icon: React.ComponentType<{ className?: string }>
}

const TABS: Tab[] = [
  { key: 'health', label: 'Health', icon: Activity },
  { key: 'history', label: 'History', icon: History },
  { key: 'match', label: 'Purchase Match', icon: ArrowRightLeft },
]

export function InventoryPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = (searchParams.get('tab') as TabKey) || 'health'

  const handleTabChange = (tab: TabKey) => {
    setSearchParams({ tab })
  }

  return (
    <div className="space-y-4">
      {/* Tab Navigation */}
      <div className="flex gap-1 p-1 bg-muted/50 rounded-lg w-fit">
        {TABS.map(({ key, label, icon: Icon }) => (
          <Button
            key={key}
            variant={activeTab === key ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => handleTabChange(key)}
            className={cn(
              "gap-2",
              activeTab === key && "shadow-sm"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Button>
        ))}
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'health' && <ScoresPage />}
        {activeTab === 'history' && <HistoryPage />}
        {activeTab === 'match' && <PurchaseMatchPage />}
      </div>
    </div>
  )
}
