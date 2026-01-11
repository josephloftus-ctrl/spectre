import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  RefreshCw, Loader2, ChevronRight, AlertCircle, ArrowRightLeft, CheckCircle2, Package
} from 'lucide-react'
import {
  fetchPurchaseMatchStatus,
  runPurchaseMatch,
  reloadPurchaseMatch,
  formatSiteName
} from '@/lib/api'
import { cn } from '@/lib/utils'

interface UnitStats {
  unit: string
  clean: number
  mismatches: number
  orphans: number
  total: number
  loading: boolean
  error: string | null
}

type FilterType = 'all' | 'issues' | 'clean'

export function PurchaseMatchPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [unitStats, setUnitStats] = useState<Record<string, UnitStats>>({})
  const [filter, setFilter] = useState<FilterType>('all')

  // Fetch system status
  const { data: status, isLoading: statusLoading, error: statusError } = useQuery({
    queryKey: ['purchase-match-status'],
    queryFn: fetchPurchaseMatchStatus,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Reload mutation
  const reloadMutation = useMutation({
    mutationFn: reloadPurchaseMatch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-match-status'] })
      setUnitStats({}) // Clear cached stats
    }
  })

  // Load stats for each unit
  const loadUnitStats = useCallback(async (unit: string) => {
    setUnitStats(prev => ({
      ...prev,
      [unit]: { ...prev[unit], unit, loading: true, error: null, clean: 0, mismatches: 0, orphans: 0, total: 0 }
    }))

    try {
      const result = await runPurchaseMatch(unit, false)
      setUnitStats(prev => ({
        ...prev,
        [unit]: {
          unit,
          clean: result.summary.clean,
          mismatches: result.summary.sku_mismatch,
          orphans: result.summary.orphan,
          total: result.summary.total,
          loading: false,
          error: null
        }
      }))
    } catch (err) {
      setUnitStats(prev => ({
        ...prev,
        [unit]: { ...prev[unit], loading: false, error: 'Failed to load' }
      }))
    }
  }, [])

  // Load stats for all units when status changes
  useEffect(() => {
    if (status?.available_units) {
      status.available_units.forEach(unit => {
        if (!unitStats[unit]) {
          loadUnitStats(unit)
        }
      })
    }
  }, [status?.available_units, loadUnitStats])

  const units = status?.available_units || []

  // Filter units
  const filteredUnits = units.filter(unit => {
    const stats = unitStats[unit]
    if (!stats || stats.loading) return true // Show loading units
    if (filter === 'issues') return stats.mismatches > 0 || stats.orphans > 0
    if (filter === 'clean') return stats.mismatches === 0 && stats.orphans === 0
    return true
  })

  // Calculate totals
  const totals = Object.values(unitStats).reduce(
    (acc, s) => ({
      clean: acc.clean + (s.clean || 0),
      mismatches: acc.mismatches + (s.mismatches || 0),
      orphans: acc.orphans + (s.orphans || 0),
    }),
    { clean: 0, mismatches: 0, orphans: 0 }
  )

  const issueUnits = Object.values(unitStats).filter(s => s.mismatches > 0 || s.orphans > 0).length
  const cleanUnits = Object.values(unitStats).filter(s => s.mismatches === 0 && s.orphans === 0 && !s.loading).length

  if (statusLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (statusError || !status) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="py-12 text-center">
          <AlertCircle className="h-12 w-12 mx-auto text-destructive mb-4" />
          <h2 className="text-lg font-semibold mb-2">Failed to Load</h2>
          <p className="text-muted-foreground mb-4">
            Could not connect to Purchase Match service
          </p>
          <Button variant="outline" onClick={() => queryClient.invalidateQueries({ queryKey: ['purchase-match-status'] })}>
            Try Again
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-head">Purchase Match</h1>
          <p className="text-muted-foreground">
            {status.canon_record_count.toLocaleString()} purchase records loaded
            {status.available_units.length > 0 && ` • ${status.available_units.length} units`}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => reloadMutation.mutate()}
          disabled={reloadMutation.isPending}
        >
          <RefreshCw className={cn('h-4 w-4 mr-2', reloadMutation.isPending && 'animate-spin')} />
          Reload Data
        </Button>
      </div>

      {/* Summary Cards - Clickable */}
      <div className="grid gap-4 md:grid-cols-3">
        <button
          onClick={() => totals.mismatches > 0 && navigate('/inventory/match/category/mismatches')}
          disabled={totals.mismatches === 0}
          className={cn(
            "text-left transition-all",
            totals.mismatches > 0 && "hover:scale-[1.02] hover:shadow-md cursor-pointer"
          )}
        >
          <Card className={cn(
            totals.mismatches > 0 && "border-amber-500/30 hover:border-amber-500/50"
          )}>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2">
                <ArrowRightLeft className="h-4 w-4 text-amber-500" />
                SKU Mismatches
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold font-mono text-amber-500">
                {totals.mismatches}
              </p>
              <p className="text-xs text-muted-foreground">
                {totals.mismatches > 0 ? 'Click to view all' : 'Quick fixes available'}
              </p>
            </CardContent>
          </Card>
        </button>

        <button
          onClick={() => totals.orphans > 0 && navigate('/inventory/match/category/needs-review')}
          disabled={totals.orphans === 0}
          className={cn(
            "text-left transition-all",
            totals.orphans > 0 && "hover:scale-[1.02] hover:shadow-md cursor-pointer"
          )}
        >
          <Card className={cn(
            totals.orphans > 0 && "border-red-500/30 hover:border-red-500/50"
          )}>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-500" />
                Needs Review
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold font-mono text-red-500">
                {totals.orphans}
              </p>
              <p className="text-xs text-muted-foreground">
                {totals.orphans > 0 ? 'Click to view all' : 'Items to investigate'}
              </p>
            </CardContent>
          </Card>
        </button>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              Clean Items
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold font-mono text-emerald-500">
              {totals.clean}
            </p>
            <p className="text-xs text-muted-foreground">SKUs verified</p>
          </CardContent>
        </Card>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        {([
          { key: 'all', label: 'All Units', count: units.length },
          { key: 'issues', label: 'Has Issues', count: issueUnits },
          { key: 'clean', label: 'Clean', count: cleanUnits },
        ] as const).map(({ key, label, count }) => (
          <Button
            key={key}
            variant={filter === key ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setFilter(key)}
            className={cn(
              key === 'issues' && filter === key && 'text-amber-500',
              key === 'clean' && filter === key && 'text-emerald-500'
            )}
          >
            {label} ({count})
          </Button>
        ))}
      </div>

      {/* Unit list */}
      {!status.initialized && (
        <Card className="border-dashed">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-muted flex items-center justify-center">
              <Package className="h-6 w-6 text-muted-foreground" />
            </div>
            <CardTitle>Not Initialized</CardTitle>
            <CardDescription>
              Purchase match data hasn't been loaded yet. Click "Reload Data" to initialize.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {status.initialized && filteredUnits.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          No units match the selected filter
        </div>
      )}

      {status.initialized && filteredUnits.length > 0 && (
        <div className="space-y-2">
          {filteredUnits.map(unit => {
            const stats = unitStats[unit]
            const hasIssues = stats && (stats.mismatches > 0 || stats.orphans > 0)

            return (
              <button
                key={unit}
                onClick={() => navigate(`/inventory/match/${encodeURIComponent(unit)}`)}
                className={cn(
                  "w-full flex items-center gap-4 p-4 rounded-lg border bg-card",
                  "hover:border-primary/50 hover:bg-accent/50 transition-all",
                  "text-left group",
                  hasIssues && "border-amber-500/30"
                )}
              >
                {/* Status indicator */}
                <div className={cn(
                  "h-10 w-10 rounded-full flex items-center justify-center",
                  stats?.loading ? "bg-muted" :
                    hasIssues ? "bg-amber-500/10" : "bg-emerald-500/10"
                )}>
                  {stats?.loading ? (
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  ) : hasIssues ? (
                    <AlertCircle className="h-5 w-5 text-amber-500" />
                  ) : (
                    <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                  )}
                </div>

                {/* Unit name and stats */}
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">
                    {formatSiteName(unit)}
                  </p>
                  {stats && !stats.loading && !stats.error && (
                    <p className="text-xs text-muted-foreground">
                      {stats.mismatches > 0 && (
                        <span className="text-amber-500">{stats.mismatches} mismatch{stats.mismatches !== 1 ? 'es' : ''}</span>
                      )}
                      {stats.mismatches > 0 && stats.orphans > 0 && ' • '}
                      {stats.orphans > 0 && (
                        <span className="text-red-500">{stats.orphans} needs review</span>
                      )}
                      {stats.mismatches === 0 && stats.orphans === 0 && (
                        <span className="text-emerald-500">{stats.clean} items verified</span>
                      )}
                    </p>
                  )}
                  {stats?.error && (
                    <p className="text-xs text-red-500">{stats.error}</p>
                  )}
                </div>

                {/* Arrow */}
                <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
