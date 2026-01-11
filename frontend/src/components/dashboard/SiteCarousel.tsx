import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ChevronLeft, ChevronRight, Pause, Play, TrendingUp, TrendingDown, AlertTriangle, Building2 } from 'lucide-react'
import { SiteSummary, formatSiteName } from '@/lib/api'
import { cn } from '@/lib/utils'

interface SiteCarouselProps {
  sites: SiteSummary[]
  onSiteClick?: (siteId: string) => void
}

export function SiteCarousel({ sites, onSiteClick }: SiteCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(true)

  // Auto-rotate every 5 seconds
  useEffect(() => {
    if (!isPlaying || sites.length <= 1) return

    const interval = setInterval(() => {
      setCurrentIndex(prev => (prev + 1) % sites.length)
    }, 5000)

    return () => clearInterval(interval)
  }, [isPlaying, sites.length])

  if (sites.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-8 text-center">
          <Building2 className="h-8 w-8 mx-auto text-muted-foreground/50 mb-2" />
          <p className="text-muted-foreground">No sites connected</p>
        </CardContent>
      </Card>
    )
  }

  const site = sites[currentIndex]
  const isPositive = site.delta_pct >= 0
  const hasIssues = site.issue_count > 0

  const goToPrev = () => {
    setCurrentIndex(prev => (prev - 1 + sites.length) % sites.length)
  }

  const goToNext = () => {
    setCurrentIndex(prev => (prev + 1) % sites.length)
  }

  return (
    <Card
      className={cn(
        "relative overflow-hidden transition-all cursor-pointer hover:border-primary/50",
        hasIssues && "border-destructive/30"
      )}
      onClick={() => onSiteClick?.(site.site)}
    >
      {/* Progress bar for auto-rotation */}
      {isPlaying && sites.length > 1 && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-muted overflow-hidden">
          <div
            className="h-full bg-primary animate-progress"
            style={{ animationDuration: '5s' }}
          />
        </div>
      )}

      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Site Focus</span>
            </div>
            <h3 className="text-2xl font-bold font-head">{formatSiteName(site.site)}</h3>
          </div>

          {hasIssues && (
            <Badge variant="destructive" className="flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              {site.issue_count} {site.issue_count === 1 ? 'Issue' : 'Issues'}
            </Badge>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Current Value</p>
            <p className="text-xl font-semibold font-mono">
              ${site.latest_total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">Change</p>
            <div className={cn(
              "flex items-center gap-1 text-xl font-semibold",
              isPositive ? "text-emerald-500" : "text-red-500"
            )}>
              {isPositive ? (
                <TrendingUp className="h-5 w-5" />
              ) : (
                <TrendingDown className="h-5 w-5" />
              )}
              <span>{isPositive ? '+' : ''}{site.delta_pct.toFixed(1)}%</span>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Last updated: {site.last_updated || 'Unknown'}</span>
          <span>Click for details →</span>
        </div>
      </CardContent>

      {/* Navigation controls */}
      {sites.length > 1 && (
        <div
          className="absolute bottom-2 right-2 flex items-center gap-1"
          onClick={e => e.stopPropagation()}
        >
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={goToPrev}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setIsPlaying(!isPlaying)}
          >
            {isPlaying ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={goToNext}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>

          <span className="text-xs text-muted-foreground ml-2">
            {currentIndex + 1}/{sites.length}
          </span>
        </div>
      )}
    </Card>
  )
}
