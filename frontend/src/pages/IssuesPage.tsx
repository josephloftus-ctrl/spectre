import { AlertTriangle, TrendingUp, DollarSign } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface Issue {
  id: string
  title: string
  type: 'variance' | 'missing' | 'duplicate' | 'pattern'
  dollarImpact: number
  occurrenceCount: number
  lastSeen: Date
  itemName: string
  location: string
}

export function IssuesPage() {
  // TODO: Connect to real issues API
  const issues: Issue[] = []

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Issues</h1>
        <p className="text-muted-foreground">Ranked by dollar impact and frequency</p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-destructive/10">
              <AlertTriangle className="h-5 w-5 text-destructive" />
            </div>
            <div>
              <p className="text-2xl font-semibold">{issues.length}</p>
              <p className="text-sm text-muted-foreground">Open Issues</p>
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
                {formatCurrency(issues.reduce((sum, i) => sum + i.dollarImpact, 0))}
              </p>
              <p className="text-sm text-muted-foreground">Total Impact</p>
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
                {issues.filter(i => i.occurrenceCount > 1).length}
              </p>
              <p className="text-sm text-muted-foreground">Recurring Patterns</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Issue List */}
      <Card className="divide-y divide-border">
        {issues.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No open issues</p>
            <p className="text-sm">Issues will appear here when detected</p>
          </div>
        ) : (
          issues.map((issue) => (
            <button
              key={issue.id}
              onClick={() => console.log('Selected issue:', issue.id)}
              className="w-full p-4 text-left hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-medium truncate">{issue.itemName}</p>
                    <Badge variant="outline" className="text-xs">
                      {issue.type}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground truncate">
                    {issue.location}
                  </p>
                </div>

                <div className="text-right">
                  <p className="font-semibold text-destructive">
                    {formatCurrency(issue.dollarImpact)}
                  </p>
                  {issue.occurrenceCount > 1 && (
                    <p className="text-xs text-muted-foreground">
                      {issue.occurrenceCount}x this month
                    </p>
                  )}
                </div>
              </div>
            </button>
          ))
        )}
      </Card>
    </div>
  )
}
