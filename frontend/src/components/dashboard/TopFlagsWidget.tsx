import { useNavigate } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ChevronRight, AlertTriangle, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { UnitScore, formatSiteName } from '@/lib/api'
import { cn } from '@/lib/utils'
import { StatusIndicator, getTrendColor } from '@/components/ui/status-indicator'

interface TopFlagsWidgetProps {
  units: UnitScore[]
  loading?: boolean
}

export function TopFlagsWidget({ units, loading }: TopFlagsWidgetProps) {
  const navigate = useNavigate()

  // Get top 5 units needing attention (non-clean, sorted by status severity)
  const statusOrder = { critical: 0, warning: 1, healthy: 2, clean: 3 }
  const needsAttention = units
    .filter(u => u.status !== 'clean')
    .sort((a, b) => statusOrder[a.status] - statusOrder[b.status])
    .slice(0, 5)

  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            Needs Attention
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-10 bg-muted/50 rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (needsAttention.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <StatusIndicator status="clean" showIcon />
            All Clear
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No units need attention. All inventory looks good.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            Needs Attention
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            className="text-xs"
            onClick={() => navigate('/scores')}
          >
            View All
            <ChevronRight className="h-3 w-3 ml-1" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-1">
          {needsAttention.map(unit => {
            const TrendIcon = unit.trend === 'up' ? TrendingUp :
              unit.trend === 'down' ? TrendingDown : Minus

            return (
              <button
                key={unit.site_id}
                onClick={() => navigate(`/${encodeURIComponent(unit.site_id)}`)}
                className={cn(
                  "w-full flex items-center gap-3 px-2 py-2 rounded-md",
                  "hover:bg-accent transition-colors text-left"
                )}
              >
                <StatusIndicator status={unit.status} size="sm" />
                <span className="flex-1 text-sm truncate">
                  {formatSiteName(unit.site_id)}
                </span>
                {unit.trend && (
                  <TrendIcon className={cn("h-3 w-3", getTrendColor(unit.trend))} />
                )}
              </button>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
