import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  ArrowLeft, ArrowRight, Loader2, Lightbulb, HelpCircle, Building2
} from 'lucide-react'
import {
  fetchPurchaseMatchStatus,
  runPurchaseMatch,
  formatSiteName,
  MatchedItem
} from '@/lib/api'
import { cn } from '@/lib/utils'

type CategoryType = 'mismatches' | 'needs-review'

interface CategoryItem extends MatchedItem {
  unit: string
}

export function PurchaseMatchCategoryPage() {
  const { category } = useParams<{ category: string }>()
  const navigate = useNavigate()
  const [allItems, setAllItems] = useState<CategoryItem[]>([])
  const [loadingUnits, setLoadingUnits] = useState<Set<string>>(new Set())

  const categoryType = category as CategoryType
  const isTypos = categoryType === 'mismatches'
  const title = isTypos ? 'SKU Mismatches' : 'Needs Review'
  const description = isTypos
    ? 'Items where the SKU doesn\'t match, but we found a likely correct item'
    : 'Items not found in purchases or vendor catalogs - may need investigation'

  // Fetch system status to get available units
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['purchase-match-status'],
    queryFn: fetchPurchaseMatchStatus,
  })

  // Load data for all units
  useEffect(() => {
    if (!status?.available_units) return

    const loadAllUnits = async () => {
      const units = status.available_units
      setLoadingUnits(new Set(units))

      const results: CategoryItem[] = []

      await Promise.all(units.map(async (unit) => {
        try {
          const result = await runPurchaseMatch(unit, false)
          const items = isTypos ? result.likely_typos : result.unknown
          items.forEach(item => {
            results.push({ ...item, unit })
          })
        } catch (err) {
          console.error(`Failed to load ${unit}:`, err)
        } finally {
          setLoadingUnits(prev => {
            const next = new Set(prev)
            next.delete(unit)
            return next
          })
        }
      }))

      setAllItems(results)
    }

    loadAllUnits()
  }, [status?.available_units, isTypos])

  const isLoading = statusLoading || loadingUnits.size > 0

  // Group by unit for display
  const groupedByUnit = allItems.reduce((acc, item) => {
    if (!acc[item.unit]) acc[item.unit] = []
    acc[item.unit].push(item)
    return acc
  }, {} as Record<string, CategoryItem[]>)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/inventory?tab=match')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex items-center gap-3">
          <div className={cn(
            "h-10 w-10 rounded-full flex items-center justify-center",
            isTypos ? "bg-amber-500/10" : "bg-red-500/10"
          )}>
            {isTypos ? (
              <Lightbulb className="h-5 w-5 text-amber-500" />
            ) : (
              <HelpCircle className="h-5 w-5 text-red-500" />
            )}
          </div>
          <div>
            <h1 className="text-2xl font-bold font-head">{title}</h1>
            <p className="text-muted-foreground">
              {isLoading ? 'Loading...' : `${allItems.length} items across all sites`}
            </p>
          </div>
        </div>
      </div>

      {/* Description */}
      <Card>
        <CardContent className="py-4">
          <p className="text-sm text-muted-foreground">{description}</p>
        </CardContent>
      </Card>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="flex flex-col items-center gap-3 text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="text-sm">
              Loading {loadingUnits.size} unit{loadingUnits.size !== 1 ? 's' : ''}...
            </span>
          </div>
        </div>
      )}

      {/* Results by unit */}
      {!isLoading && allItems.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <div className={cn(
              "mx-auto mb-4 h-12 w-12 rounded-full flex items-center justify-center",
              isTypos ? "bg-amber-500/10" : "bg-red-500/10"
            )}>
              {isTypos ? (
                <Lightbulb className="h-6 w-6 text-amber-500" />
              ) : (
                <HelpCircle className="h-6 w-6 text-red-500" />
              )}
            </div>
            <h2 className="text-lg font-semibold mb-2">No Items Found</h2>
            <p className="text-muted-foreground">
              {isTypos
                ? 'No SKU mismatches detected across any sites.'
                : 'No unrecognized items found across any sites.'}
            </p>
          </CardContent>
        </Card>
      )}

      {!isLoading && allItems.length > 0 && (
        <div className="space-y-4">
          {Object.entries(groupedByUnit).map(([unit, items]) => (
            <Card key={unit} className={cn(
              isTypos ? "border-amber-500/30" : "border-red-500/30"
            )}>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Building2 className="h-4 w-4 text-muted-foreground" />
                  {formatSiteName(unit)}
                  <Badge variant="secondary" className="ml-auto">
                    {items.length} item{items.length !== 1 ? 's' : ''}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {items.map((item, i) => (
                  isTypos ? (
                    <SwapItem key={`${item.sku}-${i}`} item={item} />
                  ) : (
                    <ReviewItem key={`${item.sku}-${i}`} item={item} />
                  )
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

// Swap visualization for mismatches - shows "this → that"
function SwapItem({ item }: { item: CategoryItem }) {
  return (
    <div className="p-3 rounded-lg bg-muted/50 space-y-3">
      {/* Current inventory item */}
      <div className="flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="font-mono text-xs bg-red-500/10 text-red-500 border-red-500/30">
              {item.sku}
            </Badge>
            <span className="text-xs text-red-500">In Inventory</span>
          </div>
          <p className="text-sm truncate">{item.description || 'No description'}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
            {item.quantity && <span>Qty: {item.quantity}</span>}
            {item.price && <><span>·</span><span>${item.price.toFixed(2)}</span></>}
            {item.vendor && <><span>·</span><span className="capitalize">{item.vendor}</span></>}
          </div>
        </div>
      </div>

      {/* Arrow and suggestion */}
      {item.suggestion && (
        <div className="flex items-start gap-3 pl-2">
          <div className="flex items-center gap-2 text-amber-500">
            <ArrowRight className="h-4 w-4" />
            <span className="text-xs font-medium">Should be</span>
          </div>
          <div className="flex-1 min-w-0 p-2 rounded bg-amber-50 dark:bg-amber-950/30 border border-amber-200/50 dark:border-amber-800/30">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="outline" className="font-mono text-xs bg-emerald-500/10 text-emerald-600 border-emerald-500/30">
                {item.suggestion.sku}
              </Badge>
              <span className="text-xs text-emerald-600">{item.suggestion.similarity}% match</span>
            </div>
            <p className="text-sm truncate">{item.suggestion.description}</p>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
              <span className="capitalize">{item.suggestion.vendor}</span>
              {item.suggestion.price && <><span>·</span><span>${item.suggestion.price.toFixed(2)}</span></>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Review item for unknowns
function ReviewItem({ item }: { item: CategoryItem }) {
  return (
    <div className="p-3 rounded-lg bg-muted/50">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="font-mono text-xs">
              {item.sku}
            </Badge>
          </div>
          <p className="text-sm truncate">{item.description || 'No description'}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
            {item.quantity && <span>Qty: {item.quantity}</span>}
            {item.price && <><span>·</span><span>${item.price.toFixed(2)}</span></>}
            {item.vendor && <><span>·</span><span className="capitalize">{item.vendor}</span></>}
          </div>
          <p className="text-xs text-red-500/80 mt-1">
            Not found in purchases or vendor catalogs
          </p>
        </div>
      </div>
    </div>
  )
}
