import { useState, useEffect, useCallback } from 'react'
import { AlertTriangle, TrendingUp, DollarSign, Loader2, MapPin } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  fetchScores,
  fetchSiteFlaggedItems,
  type UnitScore,
  type FlaggedItem,
  type FlagType,
  formatSiteName,
} from '@/lib/api'

interface IssueItem extends FlaggedItem {
  siteId: string
  siteName: string
}

const FLAG_LABELS: Record<FlagType, { label: string; variant: 'destructive' | 'secondary' | 'outline'; className?: string }> = {
  uom_error: { label: 'UOM Error', variant: 'secondary', className: 'bg-warning/10 text-warning border-warning/20' },
  big_dollar: { label: 'High Value', variant: 'destructive' },
}

export function IssuesPage() {
  const [issues, setIssues] = useState<IssueItem[]>([])
  const [sites, setSites] = useState<UnitScore[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadIssues = useCallback(async () => {
    try {
      // First get all sites with their scores
      const scoresResponse = await fetchScores()
      setSites(scoresResponse.units)

      // Then fetch flagged items for each site that has issues
      const sitesWithIssues = scoresResponse.units.filter(s => s.item_flags > 0)

      const allIssues: IssueItem[] = []

      for (const site of sitesWithIssues) {
        try {
          const flaggedResponse = await fetchSiteFlaggedItems(site.site_id)
          const siteIssues = flaggedResponse.items.map(item => ({
            ...item,
            siteId: site.site_id,
            siteName: formatSiteName(site.site_id),
          }))
          allIssues.push(...siteIssues)
        } catch {
          // Skip sites that fail to load
          console.warn(`Failed to load flagged items for ${site.site_id}`)
        }
      }

      // Sort by total value (dollar impact) descending
      allIssues.sort((a, b) => b.total - a.total)

      setIssues(allIssues)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load issues')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadIssues()
  }, [loadIssues])

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  const totalImpact = issues.reduce((sum, i) => sum + i.total, 0)
  const sitesWithIssues = sites.filter(s => s.item_flags > 0).length
  const uomErrors = issues.filter(i => i.flags.includes('uom_error')).length

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Issues</h1>
        <p className="text-muted-foreground">Flagged items ranked by dollar impact</p>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-destructive/10">
              <AlertTriangle className="h-5 w-5 text-destructive" />
            </div>
            <div>
              <p className="text-2xl font-semibold">
                {loading ? '—' : issues.length}
              </p>
              <p className="text-sm text-muted-foreground">Flagged Items</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning/10">
              <DollarSign className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-semibold">
                {loading ? '—' : formatCurrency(totalImpact)}
              </p>
              <p className="text-sm text-muted-foreground">Total Value at Risk</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <TrendingUp className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-semibold">
                {loading ? '—' : sitesWithIssues}
              </p>
              <p className="text-sm text-muted-foreground">Sites Affected</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Quick Filters */}
      <div className="flex gap-2 mb-4">
        <Badge variant="outline" className="cursor-pointer hover:bg-muted">
          All ({issues.length})
        </Badge>
        <Badge variant="destructive" className="cursor-pointer opacity-80 hover:opacity-100">
          High Value ({issues.filter(i => i.flags.includes('big_dollar')).length})
        </Badge>
        <Badge variant="secondary" className="cursor-pointer opacity-80 hover:opacity-100 bg-warning/10 text-warning">
          UOM Errors ({uomErrors})
        </Badge>
      </div>

      {/* Issue List */}
      <Card className="divide-y divide-border">
        {loading ? (
          <div className="p-8 flex items-center justify-center text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin mr-2" />
            Loading issues...
          </div>
        ) : issues.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No flagged items</p>
            <p className="text-sm">Items will appear here when issues are detected</p>
          </div>
        ) : (
          issues.map((issue, index) => (
            <div
              key={`${issue.siteId}-${issue.item}-${index}`}
              className="p-4 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <p className="font-medium">{issue.item}</p>
                    {issue.flags.map(flag => {
                      const flagConfig = FLAG_LABELS[flag]
                      return (
                        <Badge key={flag} variant={flagConfig.variant} className={`text-xs ${flagConfig.className || ''}`}>
                          {flagConfig.label}
                        </Badge>
                      )
                    })}
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-1">
                    {issue.qty} {issue.uom}
                  </p>
                  <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
                    <MapPin className="h-3 w-3" />
                    <span>{issue.siteName}</span>
                    {issue.location && (
                      <>
                        <span>•</span>
                        <span>{issue.location}</span>
                      </>
                    )}
                  </div>
                </div>

                <div className="text-right flex-shrink-0">
                  <p className="font-semibold text-destructive">
                    {formatCurrency(issue.total)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {issue.points} points
                  </p>
                </div>
              </div>
            </div>
          ))
        )}
      </Card>
    </div>
  )
}
