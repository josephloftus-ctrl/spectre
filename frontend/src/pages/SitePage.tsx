import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, fetchSiteScore, fetchSite, updateSiteName, formatSiteName, FlaggedItem, fetchSiteFiles, exportInventory, exportCart, saveBlobAsFile } from '@/lib/api'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, TrendingUp, TrendingDown, AlertTriangle, Package, DollarSign, Calendar, Loader2, MapPin, Pencil, Check, X, FileText, Download, ShoppingCart } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { StatusIndicator, getStatusLabel, getTrendIcon, getTrendColor } from '@/components/ui/status-indicator'
import { FlagBadgeList, FlagType } from '@/components/flags/FlagBadge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface SiteDetail {
  site: string
  latest_total: number
  delta_pct: number
  latest_date: string
  total_drifts: Array<{
    item: string
    prev: string
    curr: string
    prev_total: number
    curr_total: number
    ratio: number
  }>
  qty_drifts: Array<{
    item: string
    prev: string
    curr: string
    prev_qty: number
    curr_qty: number
    ratio: number
  }>
  file_summaries: Array<{ path: string; total_sum: number; mtime: number }>
}

export function SitePage() {
  const { siteId } = useParams<{ siteId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Edit state
  const [isEditing, setIsEditing] = useState(false)
  const [editName, setEditName] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  // Export state
  const [isExporting, setIsExporting] = useState(false)

  const { data: site, isLoading, error } = useQuery({
    queryKey: ['site', siteId],
    queryFn: async () => {
      const { data } = await api.get<SiteDetail>(`/inventory/sites/${siteId}`)
      return data
    },
    enabled: !!siteId
  })

  // Fetch score data for this site
  const { data: scoreData } = useQuery({
    queryKey: ['siteScore', siteId],
    queryFn: () => fetchSiteScore(siteId!),
    enabled: !!siteId,
    retry: false // Don't retry if score doesn't exist yet
  })

  // Fetch site display name
  const { data: siteInfo } = useQuery({
    queryKey: ['siteInfo', siteId],
    queryFn: () => fetchSite(siteId!),
    enabled: !!siteId
  })

  // Fetch files processed for this site
  const { data: siteFilesData } = useQuery({
    queryKey: ['siteFiles', siteId],
    queryFn: () => fetchSiteFiles(siteId!),
    enabled: !!siteId,
    retry: false
  })

  // Get display name: custom name > fetched display name > formatted site id
  const displayName = siteInfo?.display_name || formatSiteName(siteId || '')

  const startEditing = () => {
    setEditName(displayName)
    setIsEditing(true)
  }

  const cancelEditing = () => {
    setIsEditing(false)
    setEditName('')
  }

  const saveName = async () => {
    if (!siteId) return
    setIsSaving(true)
    try {
      // Pass null to reset to auto-formatted, or the custom name
      const nameToSave = editName.trim() === formatSiteName(siteId) ? null : editName.trim()
      await updateSiteName(siteId, nameToSave || null)
      queryClient.invalidateQueries({ queryKey: ['siteInfo', siteId] })
      setIsEditing(false)
    } catch (err) {
      console.error('Failed to save site name:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleExportInventory = async () => {
    if (!siteId) return
    setIsExporting(true)
    try {
      const blob = await exportInventory(siteId)
      const today = new Date().toISOString().split('T')[0]
      saveBlobAsFile(blob, `inventory_${siteId}_${today}.xlsx`)
    } catch (err) {
      console.error('Failed to export inventory:', err)
    } finally {
      setIsExporting(false)
    }
  }

  const handleExportCart = () => {
    if (!siteId) return
    // exportCart returns a direct URL for download
    window.location.href = exportCart(siteId)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="flex flex-col items-center gap-4 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span>Loading site data...</span>
        </div>
      </div>
    )
  }

  if (error || !site) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => navigate('/')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </Button>
        <Card className="border-destructive/50">
          <CardContent className="py-12 text-center">
            <AlertTriangle className="h-12 w-12 mx-auto text-destructive mb-4" />
            <h2 className="text-lg font-semibold mb-2">Site Not Found</h2>
            <p className="text-muted-foreground">
              Could not load data for site "{siteId}"
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const isPositive = site.delta_pct >= 0
  const totalIssues = (site.total_drifts?.length || 0) + (site.qty_drifts?.length || 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-3">
            {scoreData && (
              <StatusIndicator status={scoreData.status} size="lg" showIcon />
            )}
            <div>
              {isEditing ? (
                <div className="flex items-center gap-2">
                  <Input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="text-xl font-bold font-head h-9 w-64"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') saveName()
                      if (e.key === 'Escape') cancelEditing()
                    }}
                  />
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={saveName}
                    disabled={isSaving || !editName.trim()}
                    className="h-8 w-8"
                  >
                    {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4 text-emerald-500" />}
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={cancelEditing}
                    disabled={isSaving}
                    className="h-8 w-8"
                  >
                    <X className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-2 group">
                  <h1 className="text-2xl font-bold font-head">{displayName}</h1>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={startEditing}
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Pencil className="h-3 w-3 text-muted-foreground" />
                  </Button>
                </div>
              )}
              <p className="text-muted-foreground">
                {scoreData ? getStatusLabel(scoreData.status) : 'Site inventory analysis'}
                {scoreData?.trend && (
                  <span className={cn("ml-2", getTrendColor(scoreData.trend))}>
                    {getTrendIcon(scoreData.trend)}
                  </span>
                )}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {scoreData && scoreData.item_flags > 0 && (
            <div className="text-sm text-muted-foreground">
              {scoreData.item_flags} item flag{scoreData.item_flags !== 1 ? 's' : ''}
            </div>
          )}
          {!scoreData && totalIssues > 0 && (
            <Badge variant="destructive" className="text-sm">
              <AlertTriangle className="h-3 w-3 mr-1" />
              {totalIssues} Active {totalIssues === 1 ? 'Issue' : 'Issues'}
            </Badge>
          )}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" disabled={isExporting}>
                {isExporting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                Export
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Export Options</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleExportInventory}>
                <Package className="h-4 w-4 mr-2" />
                Export Inventory
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleExportCart}>
                <ShoppingCart className="h-4 w-4 mr-2" />
                Export Cart
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              Current Value
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold font-mono">
              ${site.latest_total.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              {isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
              Period Change
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className={cn(
              "text-2xl font-bold",
              isPositive ? "text-emerald-500" : "text-red-500"
            )}>
              {isPositive ? '+' : ''}{site.delta_pct.toFixed(2)}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Last Updated
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {site.latest_date || 'Unknown'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Flagged Items */}
      {scoreData && scoreData.flagged_items && scoreData.flagged_items.length > 0 && (
        <Card className="border-red-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5 text-red-500" />
              Flagged Items
            </CardTitle>
            <CardDescription>
              Items requiring attention based on quantity or value thresholds
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {scoreData.flagged_items.map((item: FlaggedItem, i: number) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{item.item}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{item.qty} {item.uom}</span>
                      <span>·</span>
                      <span>${item.total.toFixed(2)}</span>
                      {item.location && (
                        <>
                          <span>·</span>
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {item.location}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <FlagBadgeList flags={item.flags as FlagType[]} className="ml-2" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Value Drifts */}
      {site.total_drifts && site.total_drifts.length > 0 && (
        <Card className="border-amber-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-amber-500" />
              Value Variances
            </CardTitle>
            <CardDescription>
              Significant changes in item values between reports
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {site.total_drifts.slice(0, 10).map((drift, i) => {
                const change = drift.curr_total - drift.prev_total
                const pctChange = ((drift.ratio - 1) * 100)
                return (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{drift.item}</p>
                      <p className="text-xs text-muted-foreground truncate">
                        ${drift.prev_total.toFixed(2)} → ${drift.curr_total.toFixed(2)}
                      </p>
                    </div>
                    <p className={cn(
                      "text-sm font-mono font-semibold ml-2",
                      change > 0 ? "text-emerald-500" : "text-red-500"
                    )}>
                      {pctChange > 0 ? '+' : ''}{pctChange.toFixed(0)}%
                    </p>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quantity Drifts */}
      {site.qty_drifts && site.qty_drifts.length > 0 && (
        <Card className="border-red-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5 text-red-500" />
              Quantity Discrepancies
            </CardTitle>
            <CardDescription>
              Items with significant quantity changes between reports
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {site.qty_drifts.slice(0, 10).map((drift, i) => {
                const change = drift.curr_qty - drift.prev_qty
                return (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{drift.item}</p>
                      <p className="text-xs text-muted-foreground">
                        {drift.prev_qty} → {drift.curr_qty}
                      </p>
                    </div>
                    <Badge variant={change < 0 ? "destructive" : "secondary"}>
                      {change > 0 ? '+' : ''}{change.toFixed(1)}
                    </Badge>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Processed Files */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Processed Files
          </CardTitle>
          <CardDescription>
            Inventory files that have been processed for this site
          </CardDescription>
        </CardHeader>
        <CardContent>
          {siteFilesData && siteFilesData.files.length > 0 ? (
            <div className="space-y-2">
              {siteFilesData.files.map((file) => (
                <div key={file.id} className="flex items-center justify-between text-sm p-3 rounded-lg bg-muted/50">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate" title={file.filename}>
                      {file.filename}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {file.processed_at ? new Date(file.processed_at).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      }) : 'Processing...'}
                    </p>
                  </div>
                  <Badge variant={file.status === 'completed' ? 'secondary' : file.status === 'failed' ? 'destructive' : 'outline'}>
                    {file.status}
                  </Badge>
                </div>
              ))}
            </div>
          ) : site.file_summaries && site.file_summaries.length > 0 ? (
            // Fallback to legacy file_summaries
            <div className="space-y-2">
              {site.file_summaries
                .sort((a, b) => b.mtime - a.mtime)
                .slice(0, 10)
                .map((f, i) => {
                  const filename = f.path.split('/').pop() || f.path
                  return (
                    <div key={i} className="flex justify-between text-sm p-2 rounded hover:bg-muted/50">
                      <span className="text-muted-foreground truncate flex-1" title={filename}>
                        {filename}
                      </span>
                      <span className="font-mono ml-2">
                        ${f.total_sum.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                  )
                })}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-4">
              No files found for this site
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
