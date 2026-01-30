import { useState, useEffect, useCallback, useMemo } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Loader2, TrendingUp, TrendingDown, Minus, ArrowUp, ArrowDown,
  Plus, MinusCircle, DollarSign, Package, AlertTriangle, ChevronDown,
  Calendar
} from 'lucide-react'
import {
  fetchSites, fetchSiteHistory, fetchSiteMovers, fetchSiteAnomalies,
  SiteHistory, MoversResponse, AnomaliesResponse, Mover, AnomalyItem,
  formatSiteName
} from '@/lib/api'
import { cn } from '@/lib/utils'

// Helper to get ISO week number
function getWeekNumber(date: Date): number {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  const dayNum = d.getUTCDay() || 7
  d.setUTCDate(d.getUTCDate() + 4 - dayNum)
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
  return Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7)
}

// Helper to get week label
function getWeekLabel(date: Date): string {
  const now = new Date()
  const weekNum = getWeekNumber(date)
  const currentWeek = getWeekNumber(now)
  const year = date.getFullYear()
  const currentYear = now.getFullYear()

  if (year === currentYear && weekNum === currentWeek) {
    return 'This Week'
  } else if (year === currentYear && weekNum === currentWeek - 1) {
    return 'Last Week'
  } else {
    // Get the Monday of this week for the date range
    const monday = new Date(date)
    monday.setDate(date.getDate() - (date.getDay() || 7) + 1)
    const sunday = new Date(monday)
    sunday.setDate(monday.getDate() + 6)

    const formatDate = (d: Date) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    return `${formatDate(monday)} - ${formatDate(sunday)}`
  }
}

interface WeekGroup {
  weekKey: string
  label: string
  entries: Array<{
    snapshot_date: string
    total_value: number
    item_flag_count: number
    score: number
    status: string
  }>
}

type TimeRange = 3 | 8 | 12 | 52  // weeks: 3 (default), 8 (~2 months), 12 (~3 months), 52 (year)

interface MetricCardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  trend?: {
    direction: 'up' | 'down' | 'stable'
    value: string
  }
  subtitle?: string
}

function MetricCard({ title, value, icon, trend, subtitle }: MetricCardProps) {
  const TrendIcon = trend?.direction === 'up' ? TrendingUp :
    trend?.direction === 'down' ? TrendingDown : Minus

  return (
    <Card>
      <CardContent className="pt-4 pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">{title}</p>
            <p className="text-2xl font-bold mt-1">{value}</p>
            {subtitle && (
              <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
            )}
          </div>
          <div className="p-2 bg-muted rounded-lg">
            {icon}
          </div>
        </div>
        {trend && (
          <div className={cn(
            "flex items-center gap-1 mt-2 text-xs",
            trend.direction === 'up' && "text-red-500",
            trend.direction === 'down' && "text-emerald-500",
            trend.direction === 'stable' && "text-muted-foreground"
          )}>
            <TrendIcon className="h-3 w-3" />
            <span>{trend.value}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface MoverRowProps {
  mover: Mover
}

function MoverRow({ mover }: MoverRowProps) {
  return (
    <div className="flex items-center gap-3 py-2 border-b last:border-0">
      <div className={cn(
        "p-1.5 rounded",
        mover.direction === 'up' ? "bg-emerald-100 text-emerald-600" : "bg-red-100 text-red-600"
      )}>
        {mover.direction === 'up' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{mover.description || mover.sku}</p>
        <p className="text-xs text-muted-foreground">SKU: {mover.sku}</p>
      </div>
      <div className="text-right">
        <p className={cn(
          "text-sm font-medium",
          mover.direction === 'up' ? "text-emerald-600" : "text-red-600"
        )}>
          {mover.direction === 'up' ? '+' : ''}{mover.change}
        </p>
        <p className="text-xs text-muted-foreground">
          {mover.previous_qty} → {mover.current_qty}
        </p>
      </div>
    </div>
  )
}

interface AnomalyRowProps {
  item: AnomalyItem
  type: 'appeared' | 'vanished'
}

function AnomalyRow({ item, type }: AnomalyRowProps) {
  return (
    <div className="flex items-center gap-3 py-2 border-b last:border-0">
      <div className={cn(
        "p-1.5 rounded",
        type === 'appeared' ? "bg-emerald-100 text-emerald-600" : "bg-amber-100 text-amber-600"
      )}>
        {type === 'appeared' ? <Plus className="h-3 w-3" /> : <MinusCircle className="h-3 w-3" />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{item.description || item.sku}</p>
        <p className="text-xs text-muted-foreground">SKU: {item.sku}</p>
      </div>
      <div className="text-right">
        <p className="text-sm font-medium">Qty: {item.quantity}</p>
        {item.price > 0 && (
          <p className="text-xs text-muted-foreground">${item.price.toFixed(2)}</p>
        )}
      </div>
    </div>
  )
}

// Group history entries by week
function groupByWeek(entries: SiteHistory['history']): WeekGroup[] {
  const groups = new Map<string, WeekGroup>()

  for (const entry of entries) {
    const date = new Date(entry.snapshot_date)
    const year = date.getFullYear()
    const week = getWeekNumber(date)
    const weekKey = `${year}-W${week.toString().padStart(2, '0')}`

    if (!groups.has(weekKey)) {
      groups.set(weekKey, {
        weekKey,
        label: getWeekLabel(date),
        entries: []
      })
    }
    groups.get(weekKey)!.entries.push(entry)
  }

  // Sort groups by weekKey descending (newest first)
  return Array.from(groups.values()).sort((a, b) => b.weekKey.localeCompare(a.weekKey))
}

interface HistoryTimelineProps {
  weekGroups: WeekGroup[]
  formatCurrency: (value: number) => string
}

function HistoryTimeline({ weekGroups, formatCurrency }: HistoryTimelineProps) {
  if (weekGroups.length === 0) return null

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Calendar className="h-5 w-5" />
          Weekly History
        </CardTitle>
        <p className="text-xs text-muted-foreground">Inventory snapshots by week</p>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {weekGroups.map((group) => (
            <div key={group.weekKey}>
              {/* Week header */}
              <div className="flex items-center gap-2 mb-2">
                <div className="h-px flex-1 bg-border" />
                <span className="text-xs font-medium text-muted-foreground px-2 bg-background">
                  {group.label}
                </span>
                <div className="h-px flex-1 bg-border" />
              </div>

              {/* Entries for this week */}
              <div className="space-y-2 pl-4 border-l-2 border-muted">
                {group.entries.map((entry, idx) => {
                  const date = new Date(entry.snapshot_date)
                  const dayName = date.toLocaleDateString('en-US', { weekday: 'short' })
                  const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

                  return (
                    <div
                      key={`${entry.snapshot_date}-${idx}`}
                      className="flex items-center gap-3 py-2 px-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                    >
                      <div className="text-xs text-muted-foreground w-16">
                        <span className="font-medium">{dayName}</span>
                        <br />
                        {dateStr}
                      </div>
                      <div className="flex-1 flex items-center gap-4">
                        <div>
                          <p className="text-sm font-medium">{formatCurrency(entry.total_value)}</p>
                          <p className="text-xs text-muted-foreground">Total Value</p>
                        </div>
                        {entry.item_flag_count > 0 && (
                          <div className="flex items-center gap-1 text-amber-500">
                            <AlertTriangle className="h-3 w-3" />
                            <span className="text-xs">{entry.item_flag_count} flags</span>
                          </div>
                        )}
                      </div>
                      <div className={cn(
                        "text-xs px-2 py-0.5 rounded-full",
                        entry.status === 'good' && "bg-emerald-100 text-emerald-700",
                        entry.status === 'warning' && "bg-amber-100 text-amber-700",
                        entry.status === 'critical' && "bg-red-100 text-red-700"
                      )}>
                        {entry.status}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export function HistoryPage() {
  const [sites, setSites] = useState<string[]>([])
  const [selectedSite, setSelectedSite] = useState<string>('')
  const [timeRange, setTimeRange] = useState<TimeRange>(3)
  const [loading, setLoading] = useState(true)
  const [history, setHistory] = useState<SiteHistory | null>(null)
  const [movers, setMovers] = useState<MoversResponse | null>(null)
  const [anomalies, setAnomalies] = useState<AnomaliesResponse | null>(null)

  // Load sites on mount
  useEffect(() => {
    const loadSites = async () => {
      try {
        const { sites: siteList } = await fetchSites()
        const siteIds = siteList.map(s => s.site_id)
        setSites(siteIds)
        if (siteIds.length > 0 && !selectedSite) {
          setSelectedSite(siteIds[0])
        }
      } catch (error) {
        console.error('Failed to load sites:', error)
      }
    }
    loadSites()
  }, [])

  // Load data when site or time range changes
  const loadData = useCallback(async () => {
    if (!selectedSite) return

    setLoading(true)
    try {
      const [historyData, moversData, anomaliesData] = await Promise.all([
        fetchSiteHistory(selectedSite, timeRange),
        fetchSiteMovers(selectedSite),
        fetchSiteAnomalies(selectedSite)
      ])
      setHistory(historyData)
      setMovers(moversData)
      setAnomalies(anomaliesData)
    } catch (error) {
      console.error('Failed to load history:', error)
    } finally {
      setLoading(false)
    }
  }, [selectedSite, timeRange])

  useEffect(() => {
    loadData()
  }, [loadData])

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value)
  }

  // Group history by week
  const weekGroups = useMemo(() => {
    if (!history?.history) return []
    return groupByWeek(history.history)
  }, [history?.history])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold font-head">History</h1>
        <p className="text-muted-foreground">Track changes over time</p>
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative">
          <select
            value={selectedSite}
            onChange={(e) => setSelectedSite(e.target.value)}
            className={cn(
              "w-full sm:w-[200px] h-9 px-3 pr-8 rounded-md border border-input bg-background",
              "text-sm appearance-none cursor-pointer",
              "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            )}
          >
            <option value="">Select site</option>
            {sites.map(site => (
              <option key={site} value={site}>
                {formatSiteName(site)}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        </div>

        <div className="flex gap-1">
          {([
            { value: 3 as TimeRange, label: '3w' },
            { value: 8 as TimeRange, label: '2mo' },
            { value: 12 as TimeRange, label: '3mo' },
            { value: 52 as TimeRange, label: '1y' }
          ]).map(({ value, label }) => (
            <Button
              key={value}
              variant={timeRange === value ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setTimeRange(value)}
            >
              {label}
            </Button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Content */}
      {!loading && history && (
        <div className="space-y-6">
          {/* Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <MetricCard
              title="Total Value"
              value={formatCurrency(history.current?.total_value || 0)}
              icon={<DollarSign className="h-5 w-5 text-muted-foreground" />}
              trend={history.trends.value ? {
                direction: history.trends.value.direction,
                value: `${history.trends.value.percent}% from last period`
              } : undefined}
            />
            <MetricCard
              title="Item Count"
              value={history.current?.item_count || 0}
              icon={<Package className="h-5 w-5 text-muted-foreground" />}
              subtitle="Total items on inventory"
            />
            <MetricCard
              title="Flagged Items"
              value={history.current?.item_flag_count || 0}
              icon={<AlertTriangle className="h-5 w-5 text-muted-foreground" />}
              trend={history.trends.flags ? {
                direction: history.trends.flags.direction,
                value: `${history.trends.flags.change > 0 ? '+' : ''}${history.trends.flags.change} from last period`
              } : undefined}
            />
          </div>

          {/* Weekly History Timeline */}
          {weekGroups.length > 0 ? (
            <HistoryTimeline weekGroups={weekGroups} formatCurrency={formatCurrency} />
          ) : (
            <Card className="border-dashed">
              <CardContent className="py-6 text-center text-muted-foreground">
                <p>No historical data yet. History will build up over time as more inventory files are processed.</p>
              </CardContent>
            </Card>
          )}

          {/* Movers and Anomalies */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Movers */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Top Movers</CardTitle>
                <p className="text-xs text-muted-foreground">Biggest quantity changes</p>
              </CardHeader>
              <CardContent>
                {movers?.message ? (
                  <p className="text-sm text-muted-foreground py-4">{movers.message}</p>
                ) : movers?.movers.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4">No significant changes detected</p>
                ) : (
                  <div className="max-h-[300px] overflow-y-auto">
                    {movers?.movers.map((mover, i) => (
                      <MoverRow key={`${mover.sku}-${i}`} mover={mover} />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Anomalies */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Anomalies</CardTitle>
                <p className="text-xs text-muted-foreground">Items appeared or vanished</p>
              </CardHeader>
              <CardContent>
                {anomalies?.message ? (
                  <p className="text-sm text-muted-foreground py-4">{anomalies.message}</p>
                ) : (anomalies?.appeared.length === 0 && anomalies?.vanished.length === 0) ? (
                  <p className="text-sm text-muted-foreground py-4">No anomalies detected</p>
                ) : (
                  <div className="space-y-4 max-h-[300px] overflow-y-auto">
                    {anomalies && anomalies.appeared.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-emerald-600 mb-2">
                          New Items ({anomalies.appeared_count})
                        </p>
                        {anomalies.appeared.slice(0, 5).map((item, i) => (
                          <AnomalyRow key={`appeared-${item.sku}-${i}`} item={item} type="appeared" />
                        ))}
                      </div>
                    )}
                    {anomalies && anomalies.vanished.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-amber-600 mb-2">
                          Missing Items ({anomalies.vanished_count})
                        </p>
                        {anomalies.vanished.slice(0, 5).map((item, i) => (
                          <AnomalyRow key={`vanished-${item.sku}-${i}`} item={item} type="vanished" />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* No site selected */}
      {!loading && !selectedSite && sites.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No sites available. Upload inventory files to get started.</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
