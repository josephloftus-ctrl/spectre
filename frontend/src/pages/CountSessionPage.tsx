import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  ClipboardList, Loader2, Trash2, Download, Plus, RefreshCw, AlertCircle,
  ChevronRight, Check, X, Package, ArrowLeft, FileSpreadsheet
} from 'lucide-react'
import {
  fetchCountSessions, fetchCountSession, createCountSession, updateCountSession,
  deleteCountSession, addCountItem, exportCountSession, fetchSummary,
  populateCountFromInventory, CountSession, CountItem
} from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'

// Session list view
interface SessionRowProps {
  session: CountSession
  onClick: () => void
}

function SessionRow({ session, onClick }: SessionRowProps) {
  const statusColors = {
    active: 'bg-blue-500/10 text-blue-500 border-blue-500/30',
    completed: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30',
    exported: 'bg-purple-500/10 text-purple-500 border-purple-500/30',
  }

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-4 p-4 rounded-lg border bg-card",
        "hover:border-primary/50 hover:bg-accent/50 transition-all",
        "text-left group"
      )}
    >
      <ClipboardList className="h-5 w-5 text-muted-foreground" />
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{session.name || 'Unnamed Session'}</p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{session.site_id}</span>
          <span>•</span>
          <span>{session.item_count} items</span>
          {session.total_value > 0 && (
            <>
              <span>•</span>
              <span className="font-mono">${session.total_value.toFixed(2)}</span>
            </>
          )}
        </div>
      </div>
      <Badge variant="outline" className={statusColors[session.status]}>
        {session.status}
      </Badge>
      <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
    </button>
  )
}

// Count item row
interface CountItemRowProps {
  item: CountItem
}

function CountItemRow({ item }: CountItemRowProps) {
  const hasVariance = item.variance !== null && item.variance !== 0
  const total = item.counted_qty * (item.unit_price || 0)

  return (
    <div className={cn(
      "flex items-center gap-4 p-3 rounded-lg border bg-card",
      hasVariance && item.variance! < 0 && "border-red-500/30",
      hasVariance && item.variance! > 0 && "border-amber-500/30"
    )}>
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate" title={item.description}>
          {item.description}
        </p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-mono">{item.sku}</span>
          {item.location && (
            <>
              <span>•</span>
              <span>{item.location}</span>
            </>
          )}
        </div>
      </div>

      <div className="text-right">
        <p className="font-mono font-medium">{item.counted_qty} {item.uom || ''}</p>
        {item.expected_qty !== null && (
          <p className="text-xs text-muted-foreground">
            Expected: {item.expected_qty}
          </p>
        )}
      </div>

      {hasVariance && (
        <Badge variant={item.variance! < 0 ? 'destructive' : 'secondary'}>
          {item.variance! > 0 ? '+' : ''}{item.variance}
        </Badge>
      )}

      <div className="text-right min-w-[70px]">
        {item.unit_price ? (
          <p className="font-mono">${total.toFixed(2)}</p>
        ) : (
          <p className="text-muted-foreground">-</p>
        )}
      </div>
    </div>
  )
}

// Add item form
interface AddItemFormProps {
  sessionId: string
  onAdd: () => void
}

function AddItemForm({ sessionId, onAdd }: AddItemFormProps) {
  const [sku, setSku] = useState('')
  const [description, setDescription] = useState('')
  const [qty, setQty] = useState('')
  const [adding, setAdding] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!sku || !description || !qty) return

    try {
      setAdding(true)
      await addCountItem(sessionId, {
        sku,
        description,
        counted_qty: parseFloat(qty)
      })
      setSku('')
      setDescription('')
      setQty('')
      onAdd()
    } catch (error) {
      console.error('Failed to add item:', error)
    } finally {
      setAdding(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 items-end">
      <div className="flex-1">
        <Input
          placeholder="SKU"
          value={sku}
          onChange={(e) => setSku(e.target.value)}
          className="font-mono"
        />
      </div>
      <div className="flex-[2]">
        <Input
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      <div className="w-24">
        <Input
          placeholder="Qty"
          type="number"
          value={qty}
          onChange={(e) => setQty(e.target.value)}
          className="font-mono"
        />
      </div>
      <Button type="submit" disabled={adding || !sku || !description || !qty}>
        {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
      </Button>
    </form>
  )
}

export function CountSessionPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedSessionId = searchParams.get('session')
  const siteFilter = searchParams.get('site') || ''

  const [sites, setSites] = useState<string[]>([])
  const [sessions, setSessions] = useState<CountSession[]>([])
  const [selectedSession, setSelectedSession] = useState<CountSession | null>(null)
  const [sessionItems, setSessionItems] = useState<CountItem[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [newSessionName, setNewSessionName] = useState('')
  const [newSessionSite, setNewSessionSite] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [populating, setPopulating] = useState(false)

  // Load available sites
  useEffect(() => {
    fetchSummary().then(summary => {
      const siteIds = summary.sites.map(s => s.site)
      setSites(siteIds)
    }).catch(err => {
      console.error('Failed to fetch sites:', err)
    })
  }, [])

  // Load sessions list
  const loadSessions = useCallback(async () => {
    try {
      setLoading(true)
      const { sessions } = await fetchCountSessions({
        siteId: siteFilter || undefined,
        limit: 50
      })
      setSessions(sessions)
    } catch (error) {
      console.error('Failed to fetch sessions:', error)
    } finally {
      setLoading(false)
    }
  }, [siteFilter])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  // Load selected session details
  const loadSessionDetails = useCallback(async () => {
    if (!selectedSessionId) {
      setSelectedSession(null)
      setSessionItems([])
      return
    }

    try {
      setLoading(true)
      const { session, items } = await fetchCountSession(selectedSessionId)
      setSelectedSession(session)
      setSessionItems(items)
    } catch (error) {
      console.error('Failed to fetch session:', error)
    } finally {
      setLoading(false)
    }
  }, [selectedSessionId])

  useEffect(() => {
    loadSessionDetails()
  }, [loadSessionDetails])

  const handleSelectSession = (sessionId: string) => {
    const params = new URLSearchParams(searchParams)
    params.set('session', sessionId)
    setSearchParams(params)
  }

  const handleBackToList = () => {
    const params = new URLSearchParams(searchParams)
    params.delete('session')
    setSearchParams(params)
  }

  const handleSiteFilterChange = (site: string) => {
    const params = new URLSearchParams(searchParams)
    if (site === 'all') {
      params.delete('site')
    } else {
      params.set('site', site)
    }
    params.delete('session')
    setSearchParams(params)
  }

  const handleCreateSession = async () => {
    if (!newSessionSite) return

    try {
      setCreating(true)
      const { session } = await createCountSession(newSessionSite, newSessionName || undefined)
      setShowCreateForm(false)
      setNewSessionName('')
      setNewSessionSite('')
      await loadSessions()
      handleSelectSession(session.id)
    } catch (error) {
      console.error('Failed to create session:', error)
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteSession = async () => {
    if (!selectedSessionId) return

    try {
      setDeleting(true)
      await deleteCountSession(selectedSessionId)
      handleBackToList()
      await loadSessions()
    } catch (error) {
      console.error('Failed to delete session:', error)
    } finally {
      setDeleting(false)
    }
  }

  const handleCompleteSession = async () => {
    if (!selectedSessionId) return

    try {
      await updateCountSession(selectedSessionId, { status: 'completed' })
      await loadSessionDetails()
      await loadSessions()
    } catch (error) {
      console.error('Failed to complete session:', error)
    }
  }

  const handleExport = () => {
    if (!selectedSessionId) return
    window.location.href = exportCountSession(selectedSessionId)
  }

  const handlePopulateFromInventory = async () => {
    if (!selectedSessionId) return

    try {
      setPopulating(true)
      const result = await populateCountFromInventory(selectedSessionId)
      setSelectedSession(result.session)
      setSessionItems(result.items)
      await loadSessions()
    } catch (error) {
      console.error('Failed to populate from inventory:', error)
    } finally {
      setPopulating(false)
    }
  }

  // Detail view
  if (selectedSession) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={handleBackToList}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="text-2xl font-bold font-head flex items-center gap-2">
                <ClipboardList className="h-6 w-6" />
                {selectedSession.name || 'Count Session'}
              </h1>
              <p className="text-muted-foreground flex items-center gap-2">
                <span>{selectedSession.site_id}</span>
                <span>•</span>
                <span>{sessionItems.length} items</span>
                {selectedSession.total_value > 0 && (
                  <>
                    <span>•</span>
                    <span className="font-mono">${selectedSession.total_value.toFixed(2)}</span>
                  </>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {selectedSession.status === 'active' && (
              <Button variant="outline" size="sm" onClick={handleCompleteSession}>
                <Check className="h-4 w-4 mr-2" />
                Complete
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="sm" className="text-destructive hover:text-destructive">
                  <Trash2 className="h-4 w-4" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete Count Session?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will permanently delete this count session and all {sessionItems.length} items.
                    This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={handleDeleteSession} disabled={deleting}>
                    {deleting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                    Delete
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>

        {/* Status badge */}
        <div className="flex items-center gap-2">
          <Badge variant={
            selectedSession.status === 'active' ? 'default' :
            selectedSession.status === 'completed' ? 'secondary' : 'outline'
          }>
            {selectedSession.status}
          </Badge>
          <span className="text-sm text-muted-foreground">
            Created {new Date(selectedSession.created_at).toLocaleDateString()}
          </span>
        </div>

        {/* Add item form (only for active sessions) */}
        {selectedSession.status === 'active' && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Add Item</CardTitle>
            </CardHeader>
            <CardContent>
              <AddItemForm sessionId={selectedSession.id} onAdd={loadSessionDetails} />
            </CardContent>
          </Card>
        )}

        {/* Items list */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : sessionItems.length === 0 ? (
          <Card className="border-dashed">
            <CardHeader className="text-center">
              <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-muted flex items-center justify-center">
                <Package className="h-6 w-6 text-muted-foreground" />
              </div>
              <CardTitle>No Items Yet</CardTitle>
              <CardDescription>
                Pre-populate with the last inventory or add items manually.
              </CardDescription>
            </CardHeader>
            {selectedSession.status === 'active' && (
              <CardContent className="text-center pb-6">
                <Button onClick={handlePopulateFromInventory} disabled={populating}>
                  {populating ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <FileSpreadsheet className="h-4 w-4 mr-2" />
                  )}
                  Load from Last Inventory
                </Button>
              </CardContent>
            )}
          </Card>
        ) : (
          <div className="space-y-2">
            {sessionItems.map(item => (
              <CountItemRow key={item.id} item={item} />
            ))}
          </div>
        )}
      </div>
    )
  }

  // List view
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-head flex items-center gap-2">
            <ClipboardList className="h-6 w-6" />
            Count Sessions
          </h1>
          <p className="text-muted-foreground">
            {sessions.length} session{sessions.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={siteFilter || 'all'} onValueChange={handleSiteFilterChange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by site" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sites</SelectItem>
              {sites.map(site => (
                <SelectItem key={site} value={site}>
                  {site}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={loadSessions}
            disabled={loading}
          >
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </Button>
          <Button onClick={() => setShowCreateForm(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Session
          </Button>
        </div>
      </div>

      {/* Create session form */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Session</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2 items-end">
              <div className="flex-1">
                <Select value={newSessionSite} onValueChange={setNewSessionSite}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select site" />
                  </SelectTrigger>
                  <SelectContent>
                    {sites.map(site => (
                      <SelectItem key={site} value={site}>
                        {site}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-[2]">
                <Input
                  placeholder="Session name (optional)"
                  value={newSessionName}
                  onChange={(e) => setNewSessionName(e.target.value)}
                />
              </div>
              <Button onClick={handleCreateSession} disabled={creating || !newSessionSite}>
                {creating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                Create
              </Button>
              <Button variant="ghost" onClick={() => setShowCreateForm(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* No sites available */}
      {sites.length === 0 && !loading && (
        <Card className="border-dashed">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-muted flex items-center justify-center">
              <AlertCircle className="h-6 w-6 text-muted-foreground" />
            </div>
            <CardTitle>No Sites Available</CardTitle>
            <CardDescription>
              Upload inventory files to create sites and start counting.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {/* Loading state */}
      {loading && sessions.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Empty state */}
      {!loading && sites.length > 0 && sessions.length === 0 && (
        <Card className="border-dashed">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-muted flex items-center justify-center">
              <ClipboardList className="h-6 w-6 text-muted-foreground" />
            </div>
            <CardTitle>No Count Sessions</CardTitle>
            <CardDescription>
              Create a new count session to start tracking inventory counts.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center pb-6">
            <Button onClick={() => setShowCreateForm(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Session
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Sessions list */}
      {sessions.length > 0 && (
        <div className="space-y-2">
          {sessions.map(session => (
            <SessionRow
              key={session.id}
              session={session}
              onClick={() => handleSelectSession(session.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
