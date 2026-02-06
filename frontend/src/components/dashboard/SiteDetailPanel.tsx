import { useState, useEffect } from 'react'
import { Loader2, AlertTriangle, FileText, MapPin, DollarSign, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import {
  fetchSiteScore,
  fetchSiteFiles,
  type UnitScoreDetail,
  type FileRecord,
  formatSiteName,
} from '@/lib/api'
import {
  StatusIndicator,
  getStatusLabel,
  getTrendColor,
} from '@/components/ui/status-indicator'
import { cn } from '@/lib/utils'
import { ClassificationPanel } from './ClassificationPanel'

interface SiteDetailPanelProps {
  siteId: string
}

const FLAG_LABELS: Record<string, { label: string; className: string }> = {
  uom_error: { label: 'UOM Error', className: 'bg-warning/10 text-warning border-warning/20' },
  big_dollar: { label: 'High Value', className: 'bg-destructive/10 text-destructive border-destructive/20' },
  flagged_distributor: { label: 'Distributor', className: 'bg-blue-500/10 text-blue-500 border-blue-500/20' },
}

const DEFAULT_FLAG = { label: 'Flag', className: 'bg-muted text-muted-foreground' }

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function SiteDetailPanel({ siteId }: SiteDetailPanelProps) {
  const [score, setScore] = useState<UnitScoreDetail | null>(null)
  const [files, setFiles] = useState<FileRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadData() {
      setLoading(true)
      setError(null)
      try {
        const [scoreData, filesData] = await Promise.all([
          fetchSiteScore(siteId),
          fetchSiteFiles(siteId),
        ])
        setScore(scoreData)
        setFiles(filesData.files.slice(0, 5)) // Show recent 5 files
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load site details')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [siteId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 rounded-lg bg-destructive/10 text-destructive text-sm">
        {error}
      </div>
    )
  }

  if (!score) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Site not found
      </div>
    )
  }

  const TrendIcon = score.trend === 'up' ? TrendingUp :
    score.trend === 'down' ? TrendingDown : Minus

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold">{formatSiteName(siteId)}</h3>
        <div className="flex items-center gap-2 mt-1">
          <StatusIndicator status={score.status} size="sm" />
          <span className="text-sm text-muted-foreground">
            {getStatusLabel(score.status)}
          </span>
          {score.trend && (
            <span className={cn('flex items-center gap-0.5 text-xs', getTrendColor(score.trend))}>
              <TrendIcon className="h-3 w-3" />
            </span>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <Card className="p-3">
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-lg font-semibold">{formatCurrency(score.total_value)}</p>
              <p className="text-xs text-muted-foreground">Total Value</p>
            </div>
          </div>
        </Card>
        <Card className="p-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-lg font-semibold">{score.item_flags}</p>
              <p className="text-xs text-muted-foreground">Flagged Items</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Flagged Items */}
      {score.flagged_items && score.flagged_items.length > 0 && (
        <div>
          <h4 className="font-medium mb-3">Flagged Items</h4>
          <div className="space-y-2">
            {score.flagged_items.map((item, index) => (
              <Card key={`${item.item}-${index}`} className="p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-sm truncate">{item.item}</p>
                    <div className="flex items-center gap-1 mt-1 flex-wrap">
                      {item.flags.map(flag => {
                        const config = FLAG_LABELS[flag] || DEFAULT_FLAG
                        return (
                          <Badge
                            key={flag}
                            variant="outline"
                            className={cn('text-xs', config.className)}
                          >
                            {config.label}
                          </Badge>
                        )
                      })}
                    </div>
                    <div className="flex items-center gap-2 mt-1.5 text-xs text-muted-foreground">
                      <span>{item.qty} {item.uom}</span>
                      {item.location && (
                        <>
                          <span>•</span>
                          <span className="flex items-center gap-0.5">
                            <MapPin className="h-3 w-3" />
                            {item.location}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="font-semibold text-sm text-destructive">
                      {formatCurrency(item.total)}
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* No flagged items */}
      {(!score.flagged_items || score.flagged_items.length === 0) && (
        <div className="text-center py-4 text-muted-foreground text-sm">
          No flagged items for this site
        </div>
      )}

      {/* ABC-XYZ Classification */}
      <ClassificationPanel siteId={siteId} />

      {/* Recent Files */}
      {files.length > 0 && (
        <div>
          <h4 className="font-medium mb-3">Recent Files</h4>
          <div className="space-y-2">
            {files.map(file => (
              <div
                key={file.id}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors"
              >
                <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate">{file.filename}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(file.created_at)}
                  </p>
                </div>
                <Badge
                  variant={file.status === 'completed' ? 'secondary' : 'outline'}
                  className={cn(
                    'text-xs',
                    file.status === 'completed' && 'bg-emerald-500/10 text-emerald-500',
                    file.status === 'failed' && 'bg-destructive/10 text-destructive',
                    file.status === 'processing' && 'bg-primary/10 text-primary'
                  )}
                >
                  {file.status}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
