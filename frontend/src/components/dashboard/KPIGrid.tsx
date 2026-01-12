import { Card, CardContent } from "@/components/ui/card"
import { CheckCircle, AlertTriangle, DollarSign } from "lucide-react"
import { cn } from "@/lib/utils"

interface KPIGridProps {
    unitsOk: number
    unitsNeedReview: number
    totalValue: number
    totalUnits: number
}

export function KPIGrid({ unitsOk, unitsNeedReview, totalValue, totalUnits }: KPIGridProps) {
    const allClear = unitsNeedReview === 0 && totalUnits > 0

    // Format currency
    const formatCurrency = (value: number) => {
        if (value >= 1000000) {
            return `$${(value / 1000000).toFixed(1)}M`
        }
        if (value >= 1000) {
            return `$${(value / 1000).toFixed(0)}K`
        }
        return `$${value.toLocaleString()}`
    }

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
                            <AlertTriangle className={cn(
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

            {/* Total Inventory Value */}
            <Card className="bg-card/50">
                <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-primary/10">
                            <DollarSign className="h-4 w-4 text-primary" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold font-head">{formatCurrency(totalValue)}</p>
                            <p className="text-xs text-muted-foreground">Total Value</p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
