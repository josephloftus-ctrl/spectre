import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { RefreshCw, Loader2, Camera, AlertTriangle, DollarSign, Building2 } from 'lucide-react'
import { fetchScores, refreshScores, createScoreSnapshot, UnitScore, ScoreStatus } from '@/lib/api'
import { cn } from '@/lib/utils'
import { getStatusLabel } from '@/components/ui/status-indicator'
import { SiteCard, SiteDetailPanel } from '@/components/dashboard'
import { useContextPanel } from '@/components/layout'

type FilterStatus = ScoreStatus | 'all'

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export function InventoryPage() {
  const [units, setUnits] = useState<UnitScore[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [snapshotting, setSnapshotting] = useState(false)
  const [filter, setFilter] = useState<FilterStatus>('all')
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null)
  const contextPanel = useContextPanel()

  const loadScores = useCallback(async () => {
    try {
      setLoading(true)
      const statusFilter = filter === 'all' ? undefined : filter
      const { units: fetchedUnits } = await fetchScores({ status: statusFilter })
      setUnits(fetchedUnits)
    } catch (error) {
      console.error('Failed to fetch scores:', error)
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    loadScores()
  }, [loadScores])

  const handleRefresh = async () => {
    try {
      setRefreshing(true)
      await refreshScores()
      setTimeout(loadScores, 2000)
    } catch (error) {
      console.error('Failed to trigger refresh:', error)
    } finally {
      setRefreshing(false)
    }
  }

  const handleSnapshot = async () => {
    try {
      setSnapshotting(true)
      await createScoreSnapshot()
      loadScores()
    } catch (error) {
      console.error('Failed to create snapshot:', error)
    } finally {
      setSnapshotting(false)
    }
  }

  const handleSiteClick = (siteId: string) => {
    setSelectedSiteId(siteId)
    contextPanel.open(<SiteDetailPanel siteId={siteId} />)
  }

  // Calculate stats
  const statusCounts = units.reduce((acc, u) => {
    acc[u.status] = (acc[u.status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const totalValue = units.reduce((sum, u) => sum + u.total_value, 0)
  const totalFlags = units.reduce((sum, u) => sum + u.item_flags, 0)
  const criticalCount = statusCounts.critical || 0
  const warningCount = statusCounts.warning || 0

  const filteredUnits = filter === 'all' ? units : units.filter(u => u.status === filter)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Inventory</h1>
          <p className="text-muted-foreground">
            {units.length} sites tracked
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleSnapshot}
            disabled={snapshotting}
            title="Create a snapshot for week-over-week comparison"
          >
            <Camera className={cn('h-4 w-4 mr-2', snapshotting && 'opacity-50')} />
            Snapshot
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={cn('h-4 w-4 mr-2', refreshing && 'animate-spin')} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Building2 className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-semibold">{units.length}</p>
              <p className="text-sm text-muted-foreground">Total Sites</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-destructive/10">
              <AlertTriangle className="h-5 w-5 text-destructive" />
            </div>
            <div>
              <p className="text-2xl font-semibold">
                {criticalCount + warningCount}
              </p>
              <p className="text-sm text-muted-foreground">Need Attention</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning/10">
              <AlertTriangle className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-semibold">{totalFlags}</p>
              <p className="text-sm text-muted-foreground">Total Flags</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10">
              <DollarSign className="h-5 w-5 text-emerald-500" />
            </div>
            <div>
              <p className="text-2xl font-semibold">{formatCurrency(totalValue)}</p>
              <p className="text-sm text-muted-foreground">Total Value</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Status Filters */}
      <div className="flex gap-2 flex-wrap">
        {(['all', 'critical', 'warning', 'healthy', 'clean'] as FilterStatus[]).map(status => (
          <Button
            key={status}
            variant={filter === status ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setFilter(status)}
            className={cn(
              status === 'critical' && filter === status && 'text-red-500',
              status === 'warning' && filter === status && 'text-amber-500',
              status === 'healthy' && filter === status && 'text-green-500',
              status === 'clean' && filter === status && 'text-emerald-500'
            )}
          >
            {status === 'all' ? 'All' : getStatusLabel(status as ScoreStatus)}
            {status !== 'all' && statusCounts[status] ? ` (${statusCounts[status]})` : ''}
          </Button>
        ))}
      </div>

      {/* Loading state */}
      {loading && units.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Empty state */}
      {!loading && units.length === 0 && (
        <Card className="p-8 text-center border-dashed">
          <Building2 className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
          <p className="font-medium">No sites yet</p>
          <p className="text-sm text-muted-foreground">
            Upload inventory files to start tracking site health
          </p>
        </Card>
      )}

      {/* Site Grid */}
      {filteredUnits.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredUnits.map(unit => (
            <SiteCard
              key={unit.site_id}
              site={unit}
              selected={selectedSiteId === unit.site_id}
              onClick={() => handleSiteClick(unit.site_id)}
            />
          ))}
        </div>
      )}

      {/* No filter results */}
      {!loading && units.length > 0 && filteredUnits.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          No sites with "{getStatusLabel(filter as ScoreStatus)}" status
        </div>
      )}
    </div>
  )
}
