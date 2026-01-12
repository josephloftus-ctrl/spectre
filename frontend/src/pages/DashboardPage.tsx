import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { fetchSummary, SiteSummary, formatSiteName } from '@/lib/api'
import { KPIGrid } from '@/components/dashboard/KPIGrid'
import { SkeletonKPI } from '@/components/ui/skeleton'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Activity, CheckCircle, AlertTriangle, Clock } from 'lucide-react'

// Check if inventory is current (deadline: Friday 8am)
function isInventoryCurrent(lastUpdated?: string): { current: boolean; daysOld: number; status: 'current' | 'due' | 'overdue' } {
  if (!lastUpdated) return { current: false, daysOld: 999, status: 'overdue' }

  const now = new Date()
  const updated = new Date(lastUpdated)
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

  const { data, isLoading, error } = useQuery({
    queryKey: ['summary'],
    queryFn: fetchSummary,
    staleTime: 2000,
    refetchInterval: 5000
  })

  if (isLoading) {
    return (
      <div className="space-y-6 animate-page-in">
        <SkeletonKPI />
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
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4 animate-page-in">
        <div className="h-16 w-16 rounded-full bg-destructive/10 flex items-center justify-center">
          <Activity className="h-8 w-8 text-destructive" />
        </div>
        <div className="text-lg font-semibold">Connection Lost</div>
        <p className="text-muted-foreground text-center max-w-sm">
          Unable to reach the backend API. Check that the server is running.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="mt-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg btn-press hover:bg-primary/90 transition-colors"
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
    const statusA = isInventoryCurrent(a.last_updated)
    const statusB = isInventoryCurrent(b.last_updated)

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

  // Count sites by status
  const currentCount = data.sites.filter((s: SiteSummary) => isInventoryCurrent(s.last_updated).status === 'current').length
  const overdueCount = data.sites.filter((s: SiteSummary) => isInventoryCurrent(s.last_updated).status !== 'current').length

  return (
    <div className="space-y-6 animate-page-in">
      {/* KPI Section */}
      <section>
        <KPIGrid
          unitsOk={currentCount}
          unitsNeedReview={overdueCount}
          totalUnits={data.sites.length}
        />
      </section>

      {/* Site List */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold font-head">Sites</h2>
          <div className="text-sm text-muted-foreground bg-muted/50 px-3 py-1 rounded-full border border-border">
            {data.sites.length} Active
          </div>
        </div>
        <div className="space-y-3">
          {sortedSites.map((site: SiteSummary, index: number) => {
            const currency = isInventoryCurrent(site.last_updated)
            const healthStatus = site.health_status || 'clean'
            const healthScore = site.health_score || 0

            // Border color based on worst status (currency or health)
            let borderColor = "border-border"
            if (currency.status === 'overdue' || healthStatus === 'critical') {
              borderColor = "border-red-500/50"
            } else if (currency.status === 'due' || healthStatus === 'warning') {
              borderColor = "border-amber-500/50"
            }

            return (
              <Card
                key={site.site}
                className={`overflow-hidden card-hover cursor-pointer ${borderColor} bg-card/50 animate-list-item`}
                style={{ animationDelay: `${Math.min(index * 50, 300)}ms` }}
                onClick={() => handleSiteClick(site.site)}
              >
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div>
                      <div className="font-medium">{formatSiteName(site.site)}</div>
                      <div className="text-sm text-muted-foreground">
                        {currency.daysOld === 0 ? 'Updated today' : `Updated ${currency.daysOld} day${currency.daysOld === 1 ? '' : 's'} ago`}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {/* Currency Status */}
                    {currency.status === 'overdue' ? (
                      <Badge variant="destructive">
                        <AlertTriangle className="h-3 w-3 mr-1" />
                        Overdue
                      </Badge>
                    ) : currency.status === 'due' ? (
                      <Badge variant="secondary" className="text-amber-600 border-amber-300 bg-amber-50 dark:bg-amber-900/20">
                        <Clock className="h-3 w-3 mr-1" />
                        Due
                      </Badge>
                    ) : null}

                    {/* Health Status */}
                    {healthStatus === 'critical' ? (
                      <Badge variant="destructive">
                        {healthScore} issues
                      </Badge>
                    ) : healthStatus === 'warning' ? (
                      <Badge variant="secondary" className="text-amber-600 border-amber-300 bg-amber-50 dark:bg-amber-900/20">
                        {healthScore} issues
                      </Badge>
                    ) : healthStatus === 'healthy' ? (
                      <Badge variant="outline" className="text-blue-600 border-blue-300 bg-blue-50 dark:bg-blue-900/20">
                        {healthScore} minor
                      </Badge>
                    ) : currency.status === 'current' ? (
                      <Badge variant="outline" className="text-emerald-600 border-emerald-300 bg-emerald-50 dark:bg-emerald-900/20">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Clean
                      </Badge>
                    ) : null}

                    {/* Inventory Value */}
                    <div className="text-right min-w-[100px]">
                      <div className="text-lg font-bold font-head text-foreground">
                        ${(site.latest_total || 0).toLocaleString()}
                      </div>
                      <div className="text-xs text-muted-foreground">inventory value</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </section>
    </div>
  )
}
