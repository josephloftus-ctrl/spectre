import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  ArrowLeft, CheckCircle2, Loader2, ChevronDown, ChevronUp,
  EyeOff, Undo2, Lightbulb, ShoppingCart, HelpCircle, PackageCheck, Download
} from 'lucide-react'
import {
  runPurchaseMatch, formatSiteName, MatchedItem,
  addIgnoredItem, removeIgnoredItem, fetchIgnoredItems
} from '@/lib/api'
import { cn } from '@/lib/utils'

const IGNORE_REASONS = [
  { value: 'house-made', label: 'House-made' },
  { value: 'transfer', label: 'Transfer from other location' },
  { value: 'sample', label: 'Sample / One-off' },
  { value: 'other', label: 'Other' },
]

export function PurchaseMatchDetailPage() {
  const { unit } = useParams<{ unit: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showAllTypos, setShowAllTypos] = useState(false)
  const [showAllOrderable, setShowAllOrderable] = useState(false)
  const [showAllUnknown, setShowAllUnknown] = useState(false)
  const [showAllIgnored, setShowAllIgnored] = useState(false)
  const [ignoringItem, setIgnoringItem] = useState<MatchedItem | null>(null)
  const [ignoreReason, setIgnoreReason] = useState('house-made')

  const { data: result, isLoading, error } = useQuery({
    queryKey: ['purchase-match-run', unit],
    queryFn: () => runPurchaseMatch(unit!, false),
    enabled: !!unit
  })

  const { data: ignoredData } = useQuery({
    queryKey: ['ignored-items', unit],
    queryFn: () => fetchIgnoredItems(unit!),
    enabled: !!unit
  })

  const addIgnoreMutation = useMutation({
    mutationFn: ({ sku, reason }: { sku: string; reason: string }) =>
      addIgnoredItem(unit!, sku, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-match-run', unit] })
      queryClient.invalidateQueries({ queryKey: ['ignored-items', unit] })
      setIgnoringItem(null)
    }
  })

  const removeIgnoreMutation = useMutation({
    mutationFn: (sku: string) => removeIgnoredItem(unit!, sku),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-match-run', unit] })
      queryClient.invalidateQueries({ queryKey: ['ignored-items', unit] })
    }
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="flex flex-col items-center gap-4 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span>Analyzing inventory against purchases & catalogs...</span>
        </div>
      </div>
    )
  }

  if (error || !result) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => navigate('/inventory?tab=match')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Units
        </Button>
        <Card className="border-destructive/50">
          <CardContent className="py-12 text-center">
            <HelpCircle className="h-12 w-12 mx-auto text-destructive mb-4" />
            <h2 className="text-lg font-semibold mb-2">Failed to Load</h2>
            <p className="text-muted-foreground">
              Could not run analysis for "{unit}"
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const { summary, likely_typos, orderable, unknown, ignored } = result
  const displayTypos = showAllTypos ? likely_typos : likely_typos.slice(0, 10)
  const displayOrderable = showAllOrderable ? orderable : orderable.slice(0, 10)
  const displayUnknown = showAllUnknown ? unknown : unknown.slice(0, 10)
  const displayIgnored = showAllIgnored ? ignored : ignored.slice(0, 5)

  const hasIssues = summary.actionable > 0

  return (
    <div className="space-y-6">
      {/* Ignore Modal */}
      {ignoringItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <Card className="w-full max-w-md mx-4">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <EyeOff className="h-5 w-5" />
                Ignore Item
              </CardTitle>
              <CardDescription>
                This item will be marked as expected and won't appear in future reports.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3 rounded-lg bg-muted">
                <p className="font-medium truncate">{ignoringItem.description || 'Unknown Item'}</p>
                <p className="text-xs text-muted-foreground">SKU: {ignoringItem.sku}</p>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Reason</label>
                <select
                  value={ignoreReason}
                  onChange={(e) => setIgnoreReason(e.target.value)}
                  className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm"
                >
                  {IGNORE_REASONS.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2 pt-2">
                <Button variant="outline" className="flex-1" onClick={() => setIgnoringItem(null)}>
                  Cancel
                </Button>
                <Button
                  className="flex-1"
                  onClick={() => addIgnoreMutation.mutate({ sku: ignoringItem.sku, reason: ignoreReason })}
                  disabled={addIgnoreMutation.isPending}
                >
                  {addIgnoreMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Confirm'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/inventory?tab=match')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-3">
            <div className={cn(
              "h-10 w-10 rounded-full flex items-center justify-center",
              hasIssues ? "bg-amber-500/10" : "bg-emerald-500/10"
            )}>
              {hasIssues ? (
                <Lightbulb className="h-5 w-5 text-amber-500" />
              ) : (
                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
              )}
            </div>
            <div>
              <h1 className="text-2xl font-bold font-head">{formatSiteName(unit || '')}</h1>
              <p className="text-muted-foreground">{summary.total} items analyzed</p>
            </div>
          </div>
        </div>
        <a
          href={`/api/templates/${encodeURIComponent(unit || '')}/download`}
          download
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Download className="h-4 w-4" />
          Count Sheet
        </a>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-3 grid-cols-2 md:grid-cols-5">
        <StatCard icon={<CheckCircle2 className="h-4 w-4" />} label="Clean" value={summary.clean} color="emerald" />
        <StatCard icon={<ShoppingCart className="h-4 w-4" />} label="Orderable" value={summary.orderable} color="blue" />
        <StatCard icon={<Lightbulb className="h-4 w-4" />} label="Likely Typos" value={summary.likely_typo} color="amber" />
        <StatCard icon={<HelpCircle className="h-4 w-4" />} label="Needs Review" value={summary.unknown} color="red" />
        <StatCard icon={<EyeOff className="h-4 w-4" />} label="Ignored" value={summary.ignored} color="slate" />
      </div>

      {/* All Clear Message */}
      {!hasIssues && (
        <Card className="border-emerald-500/30">
          <CardContent className="py-10 text-center">
            <PackageCheck className="h-12 w-12 mx-auto text-emerald-500 mb-4" />
            <h2 className="text-lg font-semibold mb-2">All Items Verified</h2>
            <p className="text-muted-foreground">
              {summary.clean} items match purchase records
              {summary.orderable > 0 && `, ${summary.orderable} are orderable`}
              {summary.ignored > 0 && `, ${summary.ignored} ignored`}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Likely Typos - with light suggestions */}
      {likely_typos.length > 0 && (
        <Card className="border-amber-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-600">
              <Lightbulb className="h-5 w-5" />
              Likely Typos ({likely_typos.length})
            </CardTitle>
            <CardDescription>
              These SKUs weren't found, but we found similar items in vendor catalogs.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {displayTypos.map((item, i) => (
                <TypoItem key={`${item.sku}-${i}`} item={item} onIgnore={() => setIgnoringItem(item)} />
              ))}
            </div>
            {likely_typos.length > 10 && (
              <ExpandButton
                expanded={showAllTypos}
                onClick={() => setShowAllTypos(!showAllTypos)}
                remaining={likely_typos.length - 10}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Orderable - valid SKUs not purchased */}
      {orderable.length > 0 && (
        <Card className="border-blue-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-blue-600">
              <ShoppingCart className="h-5 w-5" />
              Orderable ({orderable.length})
            </CardTitle>
            <CardDescription>
              Valid SKUs in vendor catalogs, just not purchased recently.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {displayOrderable.map((item, i) => (
                <OrderableItem key={`${item.sku}-${i}`} item={item} onIgnore={() => setIgnoringItem(item)} />
              ))}
            </div>
            {orderable.length > 10 && (
              <ExpandButton
                expanded={showAllOrderable}
                onClick={() => setShowAllOrderable(!showAllOrderable)}
                remaining={orderable.length - 10}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Needs Review - needs investigation */}
      {unknown.length > 0 && (
        <Card className="border-red-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600">
              <HelpCircle className="h-5 w-5" />
              Needs Review ({unknown.length})
            </CardTitle>
            <CardDescription>
              Not found in purchases or vendor catalogs. May be house-made, transfers, or errors.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {displayUnknown.map((item, i) => (
                <UnknownItem key={`${item.sku}-${i}`} item={item} onIgnore={() => setIgnoringItem(item)} />
              ))}
            </div>
            {unknown.length > 10 && (
              <ExpandButton
                expanded={showAllUnknown}
                onClick={() => setShowAllUnknown(!showAllUnknown)}
                remaining={unknown.length - 10}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Ignored Items */}
      {ignored.length > 0 && (
        <Card className="border-slate-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-600">
              <EyeOff className="h-5 w-5" />
              Ignored ({ignored.length})
            </CardTitle>
            <CardDescription>
              Items marked as expected - won't appear as issues.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {displayIgnored.map((item, i) => {
                const info = ignoredData?.items.find(ig => ig.sku === item.sku)
                return (
                  <IgnoredItem
                    key={`${item.sku}-${i}`}
                    item={item}
                    reason={info?.reason}
                    onRestore={() => removeIgnoreMutation.mutate(item.sku)}
                    isRestoring={removeIgnoreMutation.isPending}
                  />
                )
              })}
            </div>
            {ignored.length > 5 && (
              <ExpandButton
                expanded={showAllIgnored}
                onClick={() => setShowAllIgnored(!showAllIgnored)}
                remaining={ignored.length - 5}
              />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// Stat Card Component
function StatCard({ icon, label, value, color }: {
  icon: React.ReactNode; label: string; value: number; color: string
}) {
  const colorClasses: Record<string, string> = {
    emerald: value > 0 ? 'text-emerald-600 border-emerald-500/30' : '',
    blue: value > 0 ? 'text-blue-600 border-blue-500/30' : '',
    amber: value > 0 ? 'text-amber-600 border-amber-500/30' : '',
    red: value > 0 ? 'text-red-600 border-red-500/30' : '',
    slate: value > 0 ? 'text-slate-600 border-slate-500/30' : '',
  }

  return (
    <Card className={cn("", colorClasses[color])}>
      <CardContent className="py-3 px-4">
        <div className="flex items-center gap-2 text-muted-foreground mb-1">
          {icon}
          <span className="text-xs">{label}</span>
        </div>
        <p className={cn("text-xl font-bold font-mono", value > 0 && colorClasses[color])}>
          {value}
        </p>
      </CardContent>
    </Card>
  )
}

// Expand Button
function ExpandButton({ expanded, onClick, remaining }: {
  expanded: boolean; onClick: () => void; remaining: number
}) {
  return (
    <Button variant="ghost" size="sm" className="w-full mt-4" onClick={onClick}>
      {expanded ? (
        <><ChevronUp className="h-4 w-4 mr-2" /> Show Less</>
      ) : (
        <><ChevronDown className="h-4 w-4 mr-2" /> Show {remaining} More</>
      )}
    </Button>
  )
}

// Typo Item with light suggestion
function TypoItem({ item, onIgnore }: { item: MatchedItem; onIgnore: () => void }) {
  return (
    <div className="p-3 rounded-lg bg-muted/50 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{item.description || 'Unknown Item'}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>SKU: {item.sku}</span>
            {item.quantity && <><span>·</span><span>Qty: {item.quantity}</span></>}
            {item.price && <><span>·</span><span>${item.price.toFixed(2)}</span></>}
          </div>
        </div>
        <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={onIgnore}>
          <EyeOff className="h-3 w-3 mr-1" />Ignore
        </Button>
      </div>

      {/* Light suggestion */}
      {item.suggestion && (
        <div className="mt-2 p-2 rounded bg-amber-50 dark:bg-amber-950/20 border border-amber-200/50 dark:border-amber-800/30">
          <div className="flex items-start gap-2">
            <Lightbulb className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-amber-700 dark:text-amber-300 mb-1">
                Did you mean this item? ({item.suggestion.similarity}% match)
              </p>
              <p className="text-sm font-medium truncate">{item.suggestion.description}</p>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                <Badge variant="secondary" className="font-mono text-xs h-5">
                  {item.suggestion.sku}
                </Badge>
                <span className="capitalize">{item.suggestion.vendor}</span>
                {item.suggestion.price && <span>${item.suggestion.price.toFixed(2)}</span>}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Orderable Item
function OrderableItem({ item, onIgnore }: { item: MatchedItem; onIgnore: () => void }) {
  return (
    <div className="p-3 rounded-lg bg-muted/50">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{item.description || 'Unknown Item'}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>SKU: {item.sku}</span>
            {item.quantity && <><span>·</span><span>Qty: {item.quantity}</span></>}
          </div>
          {item.catalog && (
            <p className="text-xs text-blue-600 mt-1">
              Available from {item.catalog.vendor}
              {item.catalog.price && ` • $${item.catalog.price.toFixed(2)}`}
            </p>
          )}
        </div>
        <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={onIgnore}>
          <EyeOff className="h-3 w-3 mr-1" />Ignore
        </Button>
      </div>
    </div>
  )
}

// Unknown Item
function UnknownItem({ item, onIgnore }: { item: MatchedItem; onIgnore: () => void }) {
  return (
    <div className="p-3 rounded-lg bg-muted/50">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{item.description || 'Unknown Item'}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>SKU: {item.sku}</span>
            {item.quantity && <><span>·</span><span>Qty: {item.quantity}</span></>}
            {item.price && <><span>·</span><span>${item.price.toFixed(2)}</span></>}
          </div>
          <p className="text-xs text-red-500/80 mt-1">{item.reason}</p>
        </div>
        <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={onIgnore}>
          <EyeOff className="h-3 w-3 mr-1" />Ignore
        </Button>
      </div>
    </div>
  )
}

// Ignored Item
function IgnoredItem({ item, reason, onRestore, isRestoring }: {
  item: MatchedItem; reason?: string | null; onRestore: () => void; isRestoring: boolean
}) {
  const reasonLabel = IGNORE_REASONS.find(r => r.value === reason)?.label || reason || 'Unknown'

  return (
    <div className="p-3 rounded-lg bg-muted/50">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{item.description || 'Unknown Item'}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>SKU: {item.sku}</span>
            {item.quantity && <><span>·</span><span>Qty: {item.quantity}</span></>}
          </div>
          <p className="text-xs text-slate-500 mt-1">Reason: {reasonLabel}</p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-muted-foreground"
          onClick={onRestore}
          disabled={isRestoring}
        >
          {isRestoring ? <Loader2 className="h-3 w-3 animate-spin" /> : <><Undo2 className="h-3 w-3 mr-1" />Restore</>}
        </Button>
      </div>
    </div>
  )
}
