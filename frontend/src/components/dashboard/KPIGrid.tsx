import { Card, CardContent } from "@/components/ui/card"
import { Building2, AlertTriangle, DollarSign } from "lucide-react"
import { cn } from "@/lib/utils"

interface KPIGridProps {
    totalSites: number
    totalIssues: number
    totalValue: number
}

export function KPIGrid({ totalSites, totalIssues, totalValue }: KPIGridProps) {
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
            {/* Total Sites */}
            <Card className="bg-card/50">
                <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-primary/10">
                            <Building2 className="h-4 w-4 text-primary" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold font-head">{totalSites}</p>
                            <p className="text-xs text-muted-foreground">Active Sites</p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Total Issues */}
            <Card className={cn(
                "bg-card/50",
                totalIssues > 0 && "border-amber-500/30"
            )}>
                <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                        <div className={cn(
                            "p-2 rounded-lg",
                            totalIssues > 0 ? "bg-amber-500/10" : "bg-emerald-500/10"
                        )}>
                            <AlertTriangle className={cn(
                                "h-4 w-4",
                                totalIssues > 0 ? "text-amber-500" : "text-emerald-500"
                            )} />
                        </div>
                        <div>
                            <p className={cn(
                                "text-2xl font-bold font-head",
                                totalIssues > 0 ? "text-amber-500" : ""
                            )}>{totalIssues}</p>
                            <p className="text-xs text-muted-foreground">Issues Found</p>
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
                        <div className="min-w-0">
                            <p className="text-2xl font-bold font-head truncate">{formatCurrency(totalValue)}</p>
                            <p className="text-xs text-muted-foreground">Total Value</p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
