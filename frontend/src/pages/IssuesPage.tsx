import { useState, useEffect, useCallback } from 'react'
import { AlertTriangle, TrendingUp, DollarSign, Loader2, MapPin } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  fetchScores,
  fetchSiteFlaggedItems,
  fetchClassifications,
  type FlaggedItem,
  formatSiteName,
} from '@/lib/api'
import { cn } from '@/lib/utils'

interface IssueItem extends FlaggedItem {
  siteId: string
  siteName: string
}

const FLAG_LABELS: Record<string, { label: string; variant: 'destructive' | 'secondary' | 'outline'; className?: string }> = {
  uom_error: { label: 'UOM Error', variant: 'secondary', className: 'bg-warning/10 text-warning border-warning/20' },
  big_dollar: { label: 'High Value', variant: 'destructive' },
  flagged_distributor: { label: 'Distributor', variant: 'outline', className: 'bg-blue-500/10 text-blue-500 border-blue-500/20' },
}

const DEFAULT_FLAG = { label: 'Flag', variant: 'outline' as const, className: '' }

const ABC_BADGE_STYLES: Record<string, string> = {
  A: 'bg-red-500/15 text-red-600 border-red-500/30',
  B: 'bg-amber-500/15 text-amber-600 border-amber-500/30',
  C: 'bg-slate-400/15 text-slate-500 border-slate-400/30',
}

type IssueFilter = 'all' | 'big_dollar' | 'uom_error' | 'a_class' | 'flagged_distributor'

export function IssuesPage() {
  const [issues, setIssues] = useState<IssueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<IssueFilter>('all')

  const loadIssues = useCallback(async () => {
    try {
      // First get all sites with their scores
      const scoresResponse = await fetchScores()

      // Then fetch flagged items for each site that has issues
      const sitesWithIssues = scoresResponse.units.filter(s => s.item_flags > 0)

      const allIssues: IssueItem[] = []

      for (const site of sitesWithIssues) {
        try {
          // Fetch flagged items and classifications in parallel
          const [flaggedResponse, classResponse] = await Promise.all([
            fetchSiteFlaggedItems(site.site_id),
            fetchClassifications(site.site_id).catch(() => null),
          ])

          // Build SKU -> ABC class lookup
          const abcLookup: Record<string, string> = {}
          if (classResponse?.items) {
            for (const c of classResponse.items) {
              if (c.sku && c.abc_class) {
                abcLookup[c.sku] = c.abc_class
              }
            }
          }

          const siteIssues = flaggedResponse.items.map(item => ({
            ...item,
            siteId: site.site_id,
            siteName: formatSiteName(site.site_id),
            abc_class: item.sku ? (abcLookup[item.sku] as 'A' | 'B' | 'C' | null) ?? null : null,
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

  const bigDollarCount = issues.filter(i => i.flags.includes('big_dollar')).length
  const uomErrors = issues.filter(i => i.flags.includes('uom_error')).length
  const aClassIssues = issues.filter(i => i.abc_class === 'A').length
  const distributorCount = issues.filter(i => i.flags.includes('flagged_distributor')).length

  const filteredIssues = filter === 'all' ? issues
    : filter === 'big_dollar' ? issues.filter(i => i.flags.includes('big_dollar'))
    : filter === 'uom_error' ? issues.filter(i => i.flags.includes('uom_error'))
    : filter === 'a_class' ? issues.filter(i => i.abc_class === 'A')
    : filter === 'flagged_distributor' ? issues.filter(i => i.flags.includes('flagged_distributor'))
    : issues

  const totalImpact = filteredIssues.reduce((sum, i) => sum + i.total, 0)
  const sitesWithIssues = new Set(filteredIssues.map(i => i.siteId)).size

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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-destructive/10">
              <AlertTriangle className="h-5 w-5 text-destructive" />
            </div>
            <div>
              <p className="text-2xl font-semibold">
                {loading ? '—' : filteredIssues.length}
              </p>
              <p className="text-sm text-muted-foreground">
                {filter === 'all' ? 'Flagged Items' : 'Showing'}
              </p>
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
              <p className="text-sm text-muted-foreground">Value at Risk</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-500/10">
              <TrendingUp className="h-5 w-5 text-red-500" />
            </div>
            <div>
              <p className="text-2xl font-semibold">
                {loading ? '—' : aClassIssues}
              </p>
              <p className="text-sm text-muted-foreground">A-Class Flags</p>
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
      <div className="flex gap-2 mb-4 flex-wrap">
        <Badge
          variant="outline"
          className={cn('cursor-pointer hover:bg-muted', filter === 'all' && 'bg-muted ring-1 ring-primary')}
          onClick={() => setFilter('all')}
        >
          All ({issues.length})
        </Badge>
        <Badge
          variant="destructive"
          className={cn('cursor-pointer', filter === 'big_dollar' ? 'opacity-100 ring-1 ring-destructive' : 'opacity-70 hover:opacity-100')}
          onClick={() => setFilter(filter === 'big_dollar' ? 'all' : 'big_dollar')}
        >
          High Value ({bigDollarCount})
        </Badge>
        <Badge
          variant="secondary"
          className={cn(
            'cursor-pointer bg-warning/10 text-warning',
            filter === 'uom_error' ? 'opacity-100 ring-1 ring-warning' : 'opacity-70 hover:opacity-100'
          )}
          onClick={() => setFilter(filter === 'uom_error' ? 'all' : 'uom_error')}
        >
          UOM Errors ({uomErrors})
        </Badge>
        {aClassIssues > 0 && (
          <Badge
            variant="outline"
            className={cn(
              'cursor-pointer', ABC_BADGE_STYLES.A,
              filter === 'a_class' ? 'opacity-100 ring-1 ring-red-500' : 'opacity-70 hover:opacity-100'
            )}
            onClick={() => setFilter(filter === 'a_class' ? 'all' : 'a_class')}
          >
            A-Class ({aClassIssues})
          </Badge>
        )}
        {distributorCount > 0 && (
          <Badge
            variant="outline"
            className={cn(
              'cursor-pointer bg-blue-500/10 text-blue-500 border-blue-500/20',
              filter === 'flagged_distributor' ? 'opacity-100 ring-1 ring-blue-500' : 'opacity-70 hover:opacity-100'
            )}
            onClick={() => setFilter(filter === 'flagged_distributor' ? 'all' : 'flagged_distributor')}
          >
            Distributor ({distributorCount})
          </Badge>
        )}
      </div>

      {/* Issue List */}
      <Card className="divide-y divide-border">
        {loading ? (
          <div className="p-8 flex items-center justify-center text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin mr-2" />
            Loading issues...
          </div>
        ) : filteredIssues.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>{filter === 'all' ? 'No flagged items' : 'No matching items'}</p>
            <p className="text-sm">
              {filter === 'all'
                ? 'Items will appear here when issues are detected'
                : 'Try a different filter or view all items'}
            </p>
          </div>
        ) : (
          filteredIssues.map((issue, index) => (
            <div
              key={`${issue.siteId}-${issue.item}-${index}`}
              className="p-4 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    {issue.abc_class && (
                      <Badge
                        variant="outline"
                        className={cn('text-[10px] px-1.5 py-0 font-bold', ABC_BADGE_STYLES[issue.abc_class])}
                      >
                        {issue.abc_class}
                      </Badge>
                    )}
                    <p className="font-medium">{issue.item}</p>
                    {issue.flags.map(flag => {
                      const flagConfig = FLAG_LABELS[flag] || DEFAULT_FLAG
                      return (
                        <Badge key={flag} variant={flagConfig.variant} className={`text-xs ${flagConfig.className || ''}`}>
                          {flagConfig.label}
                        </Badge>
                      )
                    })}
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-1">
                    {issue.qty} {issue.uom}
                    {issue.sku && <span className="ml-2 text-xs opacity-60">SKU: {issue.sku}</span>}
                  </p>
                  <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
                    <MapPin className="h-3 w-3" />
                    <span>{issue.siteName}</span>
                    {issue.location && (
                      <>
                        <span>·</span>
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
                    {issue.points} pts
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
