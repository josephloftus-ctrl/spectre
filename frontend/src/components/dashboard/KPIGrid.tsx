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
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
            {/* Total Sites */}
            <Card className="kpi-card bg-card border-border/50 card-hover">
                <CardContent className="p-5">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-muted-foreground mb-1">Active Sites</p>
                            <p className="data-value text-foreground">{totalSites}</p>
                        </div>
                        <div className="p-3 rounded-xl bg-primary/10 ring-1 ring-primary/20">
                            <Building2 className="h-5 w-5 text-primary" />
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Total Issues */}
            <Card className={cn(
                "kpi-card bg-card border-border/50 card-hover",
                totalIssues > 0 && "border-warning/40"
            )}>
                <CardContent className="p-5">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-muted-foreground mb-1">Issues Found</p>
                            <p className={cn(
                                "data-value",
                                totalIssues > 0 ? "text-warning" : "text-success"
                            )}>{totalIssues}</p>
                        </div>
                        <div className={cn(
                            "p-3 rounded-xl ring-1",
                            totalIssues > 0
                                ? "bg-warning/10 ring-warning/20"
                                : "bg-success/10 ring-success/20"
                        )}>
                            <AlertTriangle className={cn(
                                "h-5 w-5",
                                totalIssues > 0 ? "text-warning" : "text-success"
                            )} />
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Total Inventory Value */}
            <Card className="kpi-card bg-card border-border/50 card-hover">
                <CardContent className="p-5">
                    <div className="flex items-center justify-between">
                        <div className="min-w-0">
                            <p className="text-sm font-medium text-muted-foreground mb-1">Total Value</p>
                            <p className="data-value text-foreground truncate">{formatCurrency(totalValue)}</p>
                        </div>
                        <div className="p-3 rounded-xl bg-primary/10 ring-1 ring-primary/20">
                            <DollarSign className="h-5 w-5 text-primary" />
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
