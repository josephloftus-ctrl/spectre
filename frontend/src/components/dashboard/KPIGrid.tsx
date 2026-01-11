import { Card, CardContent } from "@/components/ui/card"
import { CheckCircle, Eye, Clock } from "lucide-react"
import { cn } from "@/lib/utils"

interface KPIGridProps {
    unitsOk: number
    unitsNeedReview: number
    lastSync?: string
    totalUnits: number
}

export function KPIGrid({ unitsOk, unitsNeedReview, lastSync, totalUnits }: KPIGridProps) {
    // Format last sync time
    const formatLastSync = (dateStr?: string) => {
        if (!dateStr) return 'Never'
        const date = new Date(dateStr)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffMins = Math.floor(diffMs / 60000)
        const diffHours = Math.floor(diffMins / 60)
        const diffDays = Math.floor(diffHours / 24)

        if (diffMins < 1) return 'Just now'
        if (diffMins < 60) return `${diffMins}m ago`
        if (diffHours < 24) return `${diffHours}h ago`
        if (diffDays === 1) return 'Yesterday'
        return `${diffDays}d ago`
    }

    const allClear = unitsNeedReview === 0 && totalUnits > 0

    return (
        <div className="grid gap-3 grid-cols-3">
            {/* Units OK */}
            <Card className="bg-card/50">
                <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                        <div className={cn(
                            "p-2 rounded-lg",
                            allClear ? "bg-emerald-500/10" : "bg-muted"
                        )}>
                            <CheckCircle className={cn(
                                "h-4 w-4",
                                allClear ? "text-emerald-500" : "text-muted-foreground"
                            )} />
                        </div>
                        <div>
                            <p className="text-2xl font-bold font-head">{unitsOk}</p>
                            <p className="text-xs text-muted-foreground">Units OK</p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Need Review */}
            <Card className={cn(
                "bg-card/50",
                unitsNeedReview > 0 && "border-amber-500/30"
            )}>
                <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                        <div className={cn(
                            "p-2 rounded-lg",
                            unitsNeedReview > 0 ? "bg-amber-500/10" : "bg-muted"
                        )}>
                            <Eye className={cn(
                                "h-4 w-4",
                                unitsNeedReview > 0 ? "text-amber-500" : "text-muted-foreground"
                            )} />
                        </div>
                        <div>
                            <p className={cn(
                                "text-2xl font-bold font-head",
                                unitsNeedReview > 0 ? "text-amber-500" : ""
                            )}>{unitsNeedReview}</p>
                            <p className="text-xs text-muted-foreground">Need Review</p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Last Sync */}
            <Card className="bg-card/50">
                <CardContent className="p-4">
                    <div className="flex items-center gap-2 min-w-0">
                        <div className="p-2 rounded-lg bg-muted flex-shrink-0">
                            <Clock className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <div className="min-w-0">
                            <p className="text-sm font-semibold font-head truncate">{formatLastSync(lastSync)}</p>
                            <p className="text-xs text-muted-foreground">Last Sync</p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
