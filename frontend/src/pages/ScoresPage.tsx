import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  RefreshCw, Loader2, ChevronRight, TrendingUp, TrendingDown, Minus, Camera, FileText
} from 'lucide-react'
import { fetchScores, refreshScores, createScoreSnapshot, UnitScore, ScoreStatus, formatSiteName } from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  StatusIndicator,
  getStatusLabel,
  getTrendColor
} from '@/components/ui/status-indicator'

interface UnitRowProps {
  unit: UnitScore
  onClick: () => void
}

function UnitRow({ unit, onClick }: UnitRowProps) {
  const TrendIcon = unit.trend === 'up' ? TrendingUp :
    unit.trend === 'down' ? TrendingDown : Minus

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-4 p-4 rounded-lg border bg-card",
        "hover:border-primary/50 hover:bg-accent/50 transition-all",
        "text-left group",
        unit.status === 'critical' && "border-red-500/30",
        unit.status === 'warning' && "border-amber-500/30"
      )}
    >
      {/* Status indicator */}
      <StatusIndicator status={unit.status} size="lg" showIcon />

      {/* Site name and flags */}
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">
          {formatSiteName(unit.site_id)}
        </p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {unit.item_flags > 0 && (
            <span>{unit.item_flags} item{unit.item_flags !== 1 ? 's' : ''} flagged</span>
          )}
          {unit.source_file && (
            <span className="flex items-center gap-1 truncate max-w-[200px]" title={unit.source_file.filename}>
              <FileText className="h-3 w-3 flex-shrink-0" />
              <span className="truncate">{unit.source_file.filename}</span>
            </span>
          )}
        </div>
      </div>

      {/* Trend indicator */}
      {unit.trend && (
        <div className={cn("flex items-center gap-1 text-xs", getTrendColor(unit.trend))}>
          <TrendIcon className="h-3 w-3" />
        </div>
      )}

      {/* Arrow */}
      <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
    </button>
  )
}

type FilterStatus = ScoreStatus | 'all'

export function ScoresPage() {
  const navigate = useNavigate()
  const [units, setUnits] = useState<UnitScore[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [snapshotting, setSnapshotting] = useState(false)
  const [filter, setFilter] = useState<FilterStatus>('all')

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
      // Wait a moment for jobs to process, then reload
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
      const result = await createScoreSnapshot()
      console.log('Snapshot created:', result)
      // Reload to refresh any trend data
      loadScores()
    } catch (error) {
      console.error('Failed to create snapshot:', error)
    } finally {
      setSnapshotting(false)
    }
  }

  const statusCounts = units.reduce((acc, u) => {
    acc[u.status] = (acc[u.status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const filteredUnits = filter === 'all' ? units : units.filter(u => u.status === filter)

  // Counts for summary
  const criticalCount = statusCounts.critical || 0
  const warningCount = statusCounts.warning || 0
  const cleanCount = (statusCounts.clean || 0) + (statusCounts.healthy || 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-head">Unit Health</h1>
          <p className="text-muted-foreground">
            {units.length} units •
            {criticalCount > 0 && <span className="text-red-500 ml-1">{criticalCount} critical</span>}
            {warningCount > 0 && <span className="text-amber-500 ml-1">{warningCount} warning</span>}
            {cleanCount > 0 && <span className="text-emerald-500 ml-1">{cleanCount} clean</span>}
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
            Refresh All
          </Button>
        </div>
      </div>

      {/* Status filter tabs */}
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
        <Card className="border-dashed">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-muted flex items-center justify-center">
              <StatusIndicator status="clean" size="lg" showIcon />
            </div>
            <CardTitle>No Scores Yet</CardTitle>
            <CardDescription>
              Unit health scores will appear here after files are processed.
              Upload inventory files to get started.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center pb-6">
            <Button variant="outline" onClick={() => navigate('/inbox')}>
              Go to Inbox
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Unit list */}
      {filteredUnits.length > 0 && (
        <div className="space-y-2">
          {filteredUnits.map(unit => (
            <UnitRow
              key={unit.site_id}
              unit={unit}
              onClick={() => navigate(`/inventory/site/${encodeURIComponent(unit.site_id)}`)}
            />
          ))}
        </div>
      )}

      {/* No filter results */}
      {!loading && units.length > 0 && filteredUnits.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          No units with "{getStatusLabel(filter as ScoreStatus)}" status
        </div>
      )}
    </div>
  )
}
