import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { fetchSummary, SiteSummary, formatSiteName } from '@/lib/api'
import { KPIGrid } from '@/components/dashboard/KPIGrid'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Activity, CheckCircle, AlertTriangle, Clock, LayoutGrid, ArrowRightLeft } from 'lucide-react'
import { PurchaseMatchPage } from './PurchaseMatchPage'
import { cn } from '@/lib/utils'

type DashboardTab = 'overview' | 'match'

// Format a date string to a readable format (e.g., "Jan 30")
function formatShortDate(dateStr?: string | null): string {
  if (!dateStr) return 'Unknown'
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// Check if inventory is current (deadline: Friday 8am)
// Uses inventory_date (when count was taken) if available, otherwise falls back to last_updated
function isInventoryCurrent(inventoryDate?: string | null, lastUpdated?: string): { current: boolean; daysOld: number; status: 'current' | 'due' | 'overdue' } {
  // Prefer inventory_date (actual count date) over last_updated (upload date)
  const dateToCheck = inventoryDate || lastUpdated
  if (!dateToCheck) return { current: false, daysOld: 999, status: 'overdue' }

  const now = new Date()
  const updated = new Date(dateToCheck)
  const diffMs = now.getTime() - updated.getTime()
  const daysOld = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  // Find the most recent Friday 8am
  const lastFriday = new Date(now)
  const dayOfWeek = now.getDay()
  const daysSinceFriday = (dayOfWeek + 2) % 7 // Days since Friday (0 = Sunday)
  lastFriday.setDate(now.getDate() - daysSinceFriday)
  lastFriday.setHours(8, 0, 0, 0)

  // If it's before Friday 8am this week, use last week's Friday
  if (now < lastFriday) {
    lastFriday.setDate(lastFriday.getDate() - 7)
  }

  const current = updated >= lastFriday
  const status = current ? 'current' : daysOld > 7 ? 'overdue' : 'due'

  return { current, daysOld, status }
}

export function DashboardPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = (searchParams.get('tab') as DashboardTab) || 'overview'

  const handleTabChange = (tab: DashboardTab) => {
    if (tab === 'overview') {
      setSearchParams({})
    } else {
      setSearchParams({ tab })
    }
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ['summary'],
    queryFn: fetchSummary,
    staleTime: 2000,
    refetchInterval: 5000
  })

  if (isLoading) {
    return (
      <div className="space-y-8 animate-page-in">
        {/* Header skeleton */}
        <div className="flex items-center justify-between">
          <div>
            <div className="h-8 w-40 skeleton rounded-lg" />
            <div className="h-4 w-56 skeleton rounded-lg mt-2" />
          </div>
          <div className="h-10 w-48 skeleton rounded-xl" />
        </div>
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-24 skeleton rounded-lg" />
          ))}
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-20 skeleton rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-6 animate-page-in">
        <div className="h-20 w-20 rounded-2xl bg-destructive/10 ring-1 ring-destructive/20 flex items-center justify-center">
          <Activity className="h-10 w-10 text-destructive" />
        </div>
        <div className="text-center">
          <div className="text-xl font-bold font-head text-foreground">Connection Lost</div>
          <p className="text-muted-foreground mt-2 max-w-sm">
            Unable to reach the backend API. Check that the server is running.
          </p>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="mt-2 px-6 py-2.5 bg-primary text-primary-foreground rounded-xl font-medium btn-press hover:bg-primary/90 transition-colors shadow-lg shadow-primary/25"
        >
          Try Again
        </button>
      </div>
    )
  }

  const handleSiteClick = (siteId: string) => {
    navigate(`/site/${encodeURIComponent(siteId)}`)
  }

  // Sort sites: overdue first, then by health score (worst first), then by value
  const sortedSites = [...data.sites].sort((a: SiteSummary, b: SiteSummary) => {
    const statusA = isInventoryCurrent(a.inventory_date, a.last_updated)
    const statusB = isInventoryCurrent(b.inventory_date, b.last_updated)

    // Sort by currency status first (overdue > due > current)
    const statusOrder = { overdue: 0, due: 1, current: 2 }
    if (statusOrder[statusA.status] !== statusOrder[statusB.status]) {
      return statusOrder[statusA.status] - statusOrder[statusB.status]
    }

    // Then by health score (higher = worse, so descending)
    const scoreA = a.health_score || 0
    const scoreB = b.health_score || 0
    if (scoreA !== scoreB) {
      return scoreB - scoreA
    }

    // Then by total value descending
    return (b.latest_total || 0) - (a.latest_total || 0)
  })

  return (
    <div className="space-y-8 animate-page-in">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-head tracking-tight text-foreground">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">Operations overview and site health</p>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-1 p-1.5 bg-muted/60 rounded-xl border border-border/50">
          <Button
            variant={activeTab === 'overview' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => handleTabChange('overview')}
            className={cn(
              "gap-2 rounded-lg transition-all",
              activeTab === 'overview'
                ? "shadow-md"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <LayoutGrid className="h-4 w-4" />
            Overview
          </Button>
          <Button
            variant={activeTab === 'match' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => handleTabChange('match')}
            className={cn(
              "gap-2 rounded-lg transition-all",
              activeTab === 'match'
                ? "shadow-md"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <ArrowRightLeft className="h-4 w-4" />
            Purchase Match
          </Button>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'match' ? (
        <PurchaseMatchPage />
      ) : (
        <>
          {/* KPI Section */}
          <section>
            <KPIGrid
              totalSites={data.sites.length}
              totalIssues={data.total_issues}
              totalValue={data.global_value}
            />
          </section>

          {/* Site List */}
          <section>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold font-head tracking-tight">Sites</h2>
              <div className="text-sm text-muted-foreground bg-muted px-4 py-1.5 rounded-full border border-border/50 font-medium">
                {data.sites.length} Active
              </div>
            </div>
            <div className="space-y-3">
              {sortedSites.map((site: SiteSummary, index: number) => {
                const currency = isInventoryCurrent(site.inventory_date, site.last_updated)
                const healthStatus = site.health_status || 'clean'
                const healthScore = site.health_score || 0

                // Determine ribbon status class
                let ribbonClass = ""
                if (currency.status === 'overdue' || healthStatus === 'critical') {
                  ribbonClass = "status-ribbon-error"
                } else if (currency.status === 'due' || healthStatus === 'warning') {
                  ribbonClass = "status-ribbon-warning"
                } else if (currency.status === 'current' && healthStatus === 'clean') {
                  ribbonClass = "status-ribbon-success"
                }

                return (
                  <Card
                    key={site.site}
                    className={cn(
                      "status-ribbon overflow-hidden card-hover cursor-pointer bg-card/80 border-border/50 animate-list-item",
                      ribbonClass
                    )}
                    style={{ animationDelay: `${Math.min(index * 50, 300)}ms` }}
                    onClick={() => handleSiteClick(site.site)}
                  >
                    <CardContent className="p-5 pl-6 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div>
                          <div className="font-semibold font-head text-foreground">{formatSiteName(site.site)}</div>
                          <div className="text-sm text-muted-foreground mt-0.5">
                            {site.inventory_date ? (
                              <>Counted {formatShortDate(site.inventory_date)}</>
                            ) : (
                              <>Uploaded {formatShortDate(site.last_updated)}</>
                            )}
                            {currency.daysOld > 0 && (
                              <span className="text-muted-foreground/70"> · {currency.daysOld}d ago</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        {/* Currency Status */}
                        {currency.status === 'overdue' ? (
                          <Badge variant="destructive" className="gap-1.5 px-2.5 py-1">
                            <AlertTriangle className="h-3.5 w-3.5" />
                            Overdue
                          </Badge>
                        ) : currency.status === 'due' ? (
                          <Badge className="gap-1.5 px-2.5 py-1 bg-warning/15 text-warning border-warning/30 hover:bg-warning/20">
                            <Clock className="h-3.5 w-3.5" />
                            Due
                          </Badge>
                        ) : null}

                        {/* Health Status */}
                        {healthStatus === 'critical' ? (
                          <Badge variant="destructive" className="px-2.5 py-1">
                            {healthScore} issues
                          </Badge>
                        ) : healthStatus === 'warning' ? (
                          <Badge className="px-2.5 py-1 bg-warning/15 text-warning border-warning/30 hover:bg-warning/20">
                            {healthScore} issues
                          </Badge>
                        ) : healthStatus === 'healthy' ? (
                          <Badge variant="outline" className="px-2.5 py-1 text-info border-info/30 bg-info/10">
                            {healthScore} minor
                          </Badge>
                        ) : currency.status === 'current' ? (
                          <Badge variant="outline" className="gap-1.5 px-2.5 py-1 text-success border-success/30 bg-success/10">
                            <CheckCircle className="h-3.5 w-3.5" />
                            Clean
                          </Badge>
                        ) : null}

                        {/* Inventory Value */}
                        <div className="text-right min-w-[110px] pl-2 border-l border-border/50">
                          <div className="data-value-sm text-foreground">
                            ${(site.latest_total || 0).toLocaleString()}
                          </div>
                          <div className="text-xs text-muted-foreground mt-0.5">inventory value</div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
