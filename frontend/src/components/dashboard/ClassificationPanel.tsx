import { useState, useEffect } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Loader2, RefreshCw, BarChart3 } from 'lucide-react'
import {
  fetchClassificationSummary,
  fetchNineBox,
  refreshClassifications,
  type ClassificationSummary,
} from '@/lib/api'
import { cn } from '@/lib/utils'

interface ClassificationPanelProps {
  siteId: string
}

const ABC_COLORS: Record<string, string> = {
  A: 'bg-red-500/15 text-red-600 border-red-500/30',
  B: 'bg-amber-500/15 text-amber-600 border-amber-500/30',
  C: 'bg-slate-500/15 text-slate-500 border-slate-500/30',
}

const XYZ_COLORS: Record<string, string> = {
  X: 'bg-emerald-500/15 text-emerald-600 border-emerald-500/30',
  Y: 'bg-blue-500/15 text-blue-600 border-blue-500/30',
  Z: 'bg-purple-500/15 text-purple-600 border-purple-500/30',
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export function ClassificationPanel({ siteId }: ClassificationPanelProps) {
  const [summary, setSummary] = useState<ClassificationSummary | null>(null)
  const [nineBox, setNineBox] = useState<Record<string, number> | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [siteId])

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const [summaryData, nineBoxData] = await Promise.all([
        fetchClassificationSummary(siteId),
        fetchNineBox(siteId),
      ])
      setSummary(summaryData)
      setNineBox(nineBoxData.matrix)
    } catch {
      setError(null) // No classifications yet is OK, not an error
      setSummary(null)
    } finally {
      setLoading(false)
    }
  }

  async function handleRefresh() {
    setRefreshing(true)
    try {
      await refreshClassifications(siteId)
      await loadData()
    } catch {
      setError('Failed to refresh classifications')
    } finally {
      setRefreshing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!summary || !summary.abc_distribution || Object.keys(summary.abc_distribution).length === 0) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="font-medium flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            ABC-XYZ Classification
          </h4>
        </div>
        <Card className="p-4 text-center border-dashed">
          <p className="text-sm text-muted-foreground mb-3">
            No classification data yet. Need 4+ weeks of inventory history.
          </p>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={cn('h-3 w-3 mr-1.5', refreshing && 'animate-spin')} />
            Calculate Now
          </Button>
        </Card>
      </div>
    )
  }

  const abcClasses = ['A', 'B', 'C'] as const
  const xyzClasses = ['X', 'Y', 'Z'] as const

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="font-medium flex items-center gap-2">
          <BarChart3 className="h-4 w-4" />
          ABC-XYZ Classification
        </h4>
        <Button variant="ghost" size="sm" onClick={handleRefresh} disabled={refreshing} className="h-7 px-2">
          <RefreshCw className={cn('h-3 w-3', refreshing && 'animate-spin')} />
        </Button>
      </div>

      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}

      {/* ABC Distribution */}
      <div className="space-y-1.5">
        <p className="text-xs text-muted-foreground font-medium">Value Distribution (ABC)</p>
        <div className="flex gap-2">
          {abcClasses.map(cls => {
            const data = summary.abc_distribution[cls]
            if (!data) return null
            return (
              <Card key={cls} className="flex-1 p-2.5">
                <div className="flex items-center gap-1.5 mb-1">
                  <Badge variant="outline" className={cn('text-xs px-1.5 py-0', ABC_COLORS[cls])}>
                    {cls}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{data.pct_of_value}%</span>
                </div>
                <p className="text-lg font-semibold">{data.count}</p>
                <p className="text-xs text-muted-foreground">{formatCurrency(data.total_value)}</p>
              </Card>
            )
          })}
        </div>
      </div>

      {/* XYZ Distribution */}
      {summary.xyz_distribution && Object.keys(summary.xyz_distribution).filter(k => k !== 'unclassified').length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-muted-foreground font-medium">Demand Stability (XYZ)</p>
          <div className="flex gap-2">
            {xyzClasses.map(cls => {
              const data = summary.xyz_distribution[cls]
              if (!data) return null
              const label = cls === 'X' ? 'Stable' : cls === 'Y' ? 'Variable' : 'Erratic'
              return (
                <Card key={cls} className="flex-1 p-2.5">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Badge variant="outline" className={cn('text-xs px-1.5 py-0', XYZ_COLORS[cls])}>
                      {cls}
                    </Badge>
                  </div>
                  <p className="text-lg font-semibold">{data.count}</p>
                  <p className="text-xs text-muted-foreground">{label}</p>
                </Card>
              )
            })}
          </div>
        </div>
      )}

      {/* 9-Box Matrix */}
      {nineBox && Object.values(nineBox).some(v => v > 0) && (
        <div className="space-y-1.5">
          <p className="text-xs text-muted-foreground font-medium">Strategic Matrix</p>
          <div className="grid grid-cols-3 gap-1">
            {/* Header row */}
            <div className="text-center text-[10px] text-muted-foreground py-0.5">X (Stable)</div>
            <div className="text-center text-[10px] text-muted-foreground py-0.5">Y (Variable)</div>
            <div className="text-center text-[10px] text-muted-foreground py-0.5">Z (Erratic)</div>
            {abcClasses.map(abc =>
              xyzClasses.map(xyz => {
                const key = `${abc}${xyz}`
                const count = nineBox[key] || 0
                return (
                  <div
                    key={key}
                    className={cn(
                      'text-center py-2 rounded text-xs font-medium',
                      count > 0 ? 'bg-primary/10 text-primary' : 'bg-muted/50 text-muted-foreground'
                    )}
                    title={key}
                  >
                    <span className="text-[10px] text-muted-foreground block">{abc}</span>
                    {count}
                  </div>
                )
              })
            )}
          </div>
        </div>
      )}

      {summary.last_calculated && (
        <p className="text-[10px] text-muted-foreground text-right">
          Last calculated: {new Date(summary.last_calculated).toLocaleDateString()}
        </p>
      )}
    </div>
  )
}
