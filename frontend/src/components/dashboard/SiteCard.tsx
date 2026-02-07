import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { UnitScore, formatSiteName } from '@/lib/api'
import {
  StatusIndicator,
  getStatusLabel,
  getTrendColor,
} from '@/components/ui/status-indicator'
import { Sparkline } from '@/components/TrendChart'

interface SiteCardProps {
  site: UnitScore
  onClick?: () => void
  selected?: boolean
  sparklineValues?: number[]
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

function getBorderColor(status: UnitScore['status']): string {
  switch (status) {
    case 'critical':
      return 'border-red-500/50'
    case 'warning':
      return 'border-amber-500/50'
    case 'healthy':
      return 'border-green-500/30'
    case 'clean':
      return 'border-border'
  }
}

function getSparklineColor(status: UnitScore['status']): 'blue' | 'green' | 'amber' | 'red' {
  switch (status) {
    case 'critical': return 'red'
    case 'warning': return 'amber'
    case 'healthy': return 'green'
    case 'clean': return 'green'
  }
}

export function SiteCard({ site, onClick, selected, sparklineValues }: SiteCardProps) {
  const TrendIcon = site.trend === 'up' ? TrendingUp :
    site.trend === 'down' ? TrendingDown : Minus

  return (
    <Card
      className={cn(
        'overflow-hidden cursor-pointer transition-all',
        'hover:border-primary/50 hover:shadow-md',
        getBorderColor(site.status),
        selected && 'border-primary ring-1 ring-primary'
      )}
      onClick={onClick}
    >
      <CardContent className="p-4">
        {/* Header: Site name + Status */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="min-w-0 flex-1">
            <p className="font-medium truncate" title={formatSiteName(site.site_id)}>
              {formatSiteName(site.site_id)}
            </p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <StatusIndicator status={site.status} size="sm" />
              <span className="text-xs text-muted-foreground">
                {getStatusLabel(site.status)}
              </span>
            </div>
          </div>

          {/* Trend indicator */}
          {site.trend && (
            <div className={cn(
              'flex items-center gap-0.5 text-xs px-1.5 py-0.5 rounded',
              getTrendColor(site.trend),
              site.trend === 'up' && 'bg-red-500/10',
              site.trend === 'down' && 'bg-emerald-500/10',
              site.trend === 'stable' && 'bg-muted'
            )}>
              <TrendIcon className="h-3 w-3" />
            </div>
          )}
        </div>

        {/* Value + Sparkline */}
        <div className="flex items-end justify-between gap-2 mb-3">
          <div>
            <p className="text-2xl font-bold font-head">
              {formatCurrency(site.total_value)}
            </p>
            <p className="text-xs text-muted-foreground">Total Value</p>
          </div>
          {sparklineValues && sparklineValues.length >= 2 && (
            <Sparkline
              values={sparklineValues}
              color={getSparklineColor(site.status)}
              width={64}
              height={24}
            />
          )}
        </div>

        {/* Footer: Flags */}
        {site.item_flags > 0 ? (
          <div className="flex items-center gap-1.5">
            <Badge variant="secondary" className="bg-warning/10 text-warning border-warning/20 gap-1">
              <AlertTriangle className="h-3 w-3" />
              {site.item_flags} flag{site.item_flags !== 1 ? 's' : ''}
            </Badge>
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            <Badge variant="outline" className="text-muted-foreground">
              No issues
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
