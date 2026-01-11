import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

import { SiteSummary, UnitScore, ScoreStatus, formatSiteName } from "@/lib/api"
import { StatusIndicator } from "@/components/ui/status-indicator"

interface SiteMatrixProps {
    sites: SiteSummary[]
    scores?: UnitScore[]
    onSiteClick?: (siteId: string) => void
}

// Map site IDs to their scores
function getScoreMap(scores?: UnitScore[]): Map<string, UnitScore> {
    const map = new Map<string, UnitScore>()
    if (scores) {
        for (const score of scores) {
            map.set(score.site_id, score)
        }
    }
    return map
}

// Get border color based on status or legacy logic
function getBorderColor(status?: ScoreStatus, isCrit?: boolean, isWarn?: boolean): string {
    if (status) {
        switch (status) {
            case 'critical': return "border-red-500/50"
            case 'warning': return "border-amber-500/50"
            case 'healthy': return "border-green-500/30"
            case 'clean': return "border-border"
        }
    }
    // Legacy fallback
    if (isCrit) return "border-destructive/50"
    if (isWarn) return "border-amber-500/50"
    return "border-border"
}

export function SiteMatrix({ sites, scores, onSiteClick }: SiteMatrixProps) {
    const scoreMap = getScoreMap(scores)

    // Sort sites by score status (critical first) when scores are available
    const sortedSites = scores && scores.length > 0
        ? [...sites].sort((a, b) => {
            const scoreA = scoreMap.get(a.site)
            const scoreB = scoreMap.get(b.site)
            if (!scoreA && !scoreB) return 0
            if (!scoreA) return 1
            if (!scoreB) return -1
            const order: Record<ScoreStatus, number> = { critical: 0, warning: 1, healthy: 2, clean: 3 }
            return order[scoreA.status] - order[scoreB.status]
        })
        : sites

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {sortedSites.map((site, index) => {
                const score = scoreMap.get(site.site)
                const isCrit = site.delta_pct < -5 || site.issue_count > 10
                const isWarn = site.delta_pct < 0

                const borderColor = getBorderColor(score?.status, isCrit, isWarn)

                let statusColor = "text-emerald-500"
                if (score) {
                    switch (score.status) {
                        case 'critical': statusColor = "text-red-500"; break
                        case 'warning': statusColor = "text-amber-500"; break
                        case 'healthy': statusColor = "text-green-500"; break
                        case 'clean': statusColor = "text-emerald-500"; break
                    }
                } else {
                    if (isCrit) statusColor = "text-destructive"
                    else if (isWarn) statusColor = "text-amber-500"
                }

                return (
                    <Card
                        key={site.site}
                        className={`overflow-hidden card-hover cursor-pointer ${borderColor} bg-card/50 animate-list-item`}
                        style={{ animationDelay: `${Math.min(index * 30, 300)}ms` }}
                        onClick={() => onSiteClick?.(site.site)}
                    >
                        <CardContent className="p-4 flex flex-col gap-3">
                            <div className="flex justify-between items-start">
                                <span className="text-xs font-medium truncate max-w-[80%]">
                                    {formatSiteName(site.site)}
                                </span>
                                {/* Show status indicator if score available, otherwise show issue badge */}
                                {score ? (
                                    <StatusIndicator status={score.status} size="sm" />
                                ) : (
                                    site.issue_count > 0 && (
                                        <Badge variant={isCrit ? "destructive" : "secondary"} className="h-5 px-1.5 text-[10px]">
                                            {site.issue_count}
                                        </Badge>
                                    )
                                )}
                            </div>

                            <div>
                                <div className={`text-xl font-bold font-head animate-count ${statusColor}`}>
                                    {site.delta_pct > 0 ? "+" : ""}
                                    {site.delta_pct.toFixed(1)}%
                                </div>
                                <div className="text-[10px] text-muted-foreground uppercase font-semibold">
                                    Variance
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                )
            })}
        </div>
    )
}
