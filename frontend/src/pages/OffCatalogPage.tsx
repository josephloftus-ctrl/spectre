import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Package, Loader2, Trash2, Plus, Search, Edit2, X, Check, AlertCircle
} from 'lucide-react'
import {
  fetchOffCatalogItems, createOffCatalogItem, updateOffCatalogItem,
  deleteOffCatalogItem, fetchSummary, OffCatalogItem, OffCatalogItemRequest
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

// Off-catalog item row
interface ItemRowProps {
  item: OffCatalogItem
  onEdit: (item: OffCatalogItem) => void
  onDelete: (custNum: string) => Promise<void>
  deleting: boolean
}

function ItemRow({ item, onEdit, onDelete, deleting }: ItemRowProps) {
  return (
    <div className={cn(
      "flex items-center gap-4 p-4 rounded-lg border bg-card",
      deleting && "opacity-50 pointer-events-none"
    )}>
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate" title={item.description}>
          {item.description || 'No description'}
        </p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
          <span className="font-mono">Dist# {item.dist_num}</span>
          <span>•</span>
          <span className="font-mono">Cust# {item.cust_num}</span>
          {item.distributor && (
            <>
              <span>•</span>
              <Badge variant="outline" className="text-xs py-0">{item.distributor}</Badge>
            </>
          )}
          {item.pack && (
            <>
              <span>•</span>
              <span>{item.pack}</span>
            </>
          )}
          {item.uom && (
            <>
              <span>•</span>
              <span>{item.uom}</span>
            </>
          )}
        </div>
      </div>

      <div className="text-right">
        {item.unit_price ? (
          <p className="font-semibold">${item.unit_price.toFixed(2)}</p>
        ) : (
          <p className="text-muted-foreground">No price</p>
        )}
      </div>

      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => onEdit(item)}
        >
          <Edit2 className="h-4 w-4" />
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Item?</AlertDialogTitle>
              <AlertDialogDescription>
                This will remove "{item.description}" from off-catalog items.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => onDelete(item.cust_num)}>
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  )
}

// Add/Edit form
interface ItemFormProps {
  item?: OffCatalogItem
  onSave: (data: OffCatalogItemRequest) => Promise<void>
  onCancel: () => void
  saving: boolean
}

function ItemForm({ item, onSave, onCancel, saving }: ItemFormProps) {
  const [formData, setFormData] = useState<OffCatalogItemRequest>({
    dist_num: item?.dist_num || '',
    cust_num: item?.cust_num || '',
    description: item?.description || '',
    pack: item?.pack || '',
    uom: item?.uom || '',
    unit_price: item?.unit_price || undefined,
    distributor: item?.distributor || '',
    notes: item?.notes || '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSave(formData)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 p-4 border rounded-lg bg-muted/30">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{item ? 'Edit Item' : 'Add New Item'}</h3>
        <Button type="button" variant="ghost" size="icon" onClick={onCancel}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm text-muted-foreground">Dist # *</label>
          <Input
            value={formData.dist_num}
            onChange={e => setFormData({ ...formData, dist_num: e.target.value })}
            placeholder="Distributor number"
            required
          />
        </div>
        <div>
          <label className="text-sm text-muted-foreground">Cust # (auto if blank)</label>
          <Input
            value={formData.cust_num || ''}
            onChange={e => setFormData({ ...formData, cust_num: e.target.value })}
            placeholder="Customer number"
            disabled={!!item}
          />
        </div>
      </div>

      <div>
        <label className="text-sm text-muted-foreground">Description</label>
        <Input
          value={formData.description || ''}
          onChange={e => setFormData({ ...formData, description: e.target.value })}
          placeholder="Item description"
        />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="text-sm text-muted-foreground">Pack</label>
          <Input
            value={formData.pack || ''}
            onChange={e => setFormData({ ...formData, pack: e.target.value })}
            placeholder="e.g., 6/10 OZ"
          />
        </div>
        <div>
          <label className="text-sm text-muted-foreground">UOM</label>
          <Input
            value={formData.uom || ''}
            onChange={e => setFormData({ ...formData, uom: e.target.value })}
            placeholder="e.g., CS"
          />
        </div>
        <div>
          <label className="text-sm text-muted-foreground">Unit Price</label>
          <Input
            type="number"
            step="0.01"
            value={formData.unit_price || ''}
            onChange={e => setFormData({ ...formData, unit_price: parseFloat(e.target.value) || undefined })}
            placeholder="0.00"
          />
        </div>
      </div>

      <div>
        <label className="text-sm text-muted-foreground">Distributor</label>
        <Input
          value={formData.distributor || ''}
          onChange={e => setFormData({ ...formData, distributor: e.target.value })}
          placeholder="e.g., Sysco"
        />
      </div>

      <div>
        <label className="text-sm text-muted-foreground">Notes</label>
        <Input
          value={formData.notes || ''}
          onChange={e => setFormData({ ...formData, notes: e.target.value })}
          placeholder="Optional notes"
        />
      </div>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving || !formData.dist_num}>
          {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Check className="h-4 w-4 mr-2" />}
          {item ? 'Update' : 'Add Item'}
        </Button>
      </div>
    </form>
  )
}

export function OffCatalogPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [sites, setSites] = useState<string[]>([])
  const [selectedSite, setSelectedSite] = useState<string>(searchParams.get('site') || '')
  const [items, setItems] = useState<OffCatalogItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingItem, setEditingItem] = useState<OffCatalogItem | undefined>()
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // Load sites
  useEffect(() => {
    const loadSites = async () => {
      try {
        const data = await fetchSummary()
        const siteIds = data.sites.map(s => s.site)
        setSites(siteIds)
        if (!selectedSite && siteIds.length > 0) {
          setSelectedSite(siteIds[0])
        }
      } catch (err) {
        console.error('Failed to load sites:', err)
      }
    }
    loadSites()
  }, [])

  // Load items when site changes
  const loadItems = useCallback(async () => {
    if (!selectedSite) return
    setLoading(true)
    setError(null)
    try {
      const data = await fetchOffCatalogItems(selectedSite, true)
      setItems(data.items)
    } catch (err: any) {
      setError(err.message || 'Failed to load off-catalog items')
    } finally {
      setLoading(false)
    }
  }, [selectedSite])

  useEffect(() => {
    loadItems()
    if (selectedSite) {
      setSearchParams({ site: selectedSite })
    }
  }, [selectedSite, loadItems, setSearchParams])

  const handleSave = async (data: OffCatalogItemRequest) => {
    setSaving(true)
    try {
      if (editingItem) {
        await updateOffCatalogItem(selectedSite, editingItem.cust_num, data)
      } else {
        await createOffCatalogItem(selectedSite, data)
      }
      setShowForm(false)
      setEditingItem(undefined)
      await loadItems()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to save item')
    } finally {
      setSaving(false)
    }
  }

  const handleEdit = (item: OffCatalogItem) => {
    setEditingItem(item)
    setShowForm(true)
  }

  const handleDelete = async (custNum: string) => {
    setDeletingId(custNum)
    try {
      await deleteOffCatalogItem(selectedSite, custNum)
      await loadItems()
    } catch (err: any) {
      setError(err.message || 'Failed to delete item')
    } finally {
      setDeletingId(null)
    }
  }

  const handleCancel = () => {
    setShowForm(false)
    setEditingItem(undefined)
  }

  // Filter items by search
  const filteredItems = items.filter(item => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      item.description?.toLowerCase().includes(q) ||
      item.dist_num?.toLowerCase().includes(q) ||
      item.cust_num?.toLowerCase().includes(q) ||
      item.distributor?.toLowerCase().includes(q)
    )
  })

  const activeItems = filteredItems.filter(i => i.is_active)
  const inactiveItems = filteredItems.filter(i => !i.is_active)

  return (
    <div className="space-y-6 animate-page-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-head flex items-center gap-2">
            <Package className="h-6 w-6" />
            Off-Catalog Items
          </h1>
          <p className="text-muted-foreground">
            Custom items not in the Master Order Guide
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Select value={selectedSite} onValueChange={setSelectedSite}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Select site" />
            </SelectTrigger>
            <SelectContent>
              {sites.map(site => (
                <SelectItem key={site} value={site}>
                  {site.replace(/_/g, ' ')}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button onClick={() => { setEditingItem(undefined); setShowForm(true) }}>
            <Plus className="h-4 w-4 mr-2" />
            Add Item
          </Button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 rounded-lg bg-destructive/10 text-destructive flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          {error}
          <Button variant="ghost" size="sm" className="ml-auto" onClick={() => setError(null)}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Add/Edit Form */}
      {showForm && (
        <ItemForm
          item={editingItem}
          onSave={handleSave}
          onCancel={handleCancel}
          saving={saving}
        />
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search items..."
          className="pl-9"
        />
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Items List */}
      {!loading && selectedSite && (
        <>
          {filteredItems.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No off-catalog items found</p>
                <p className="text-sm">Add custom items that aren't in the Master Order Guide</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {/* Active Items */}
              {activeItems.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-muted-foreground">
                    Active Items ({activeItems.length})
                  </h3>
                  {activeItems.map(item => (
                    <ItemRow
                      key={item.cust_num}
                      item={item}
                      onEdit={handleEdit}
                      onDelete={handleDelete}
                      deleting={deletingId === item.cust_num}
                    />
                  ))}
                </div>
              )}

              {/* Inactive Items */}
              {inactiveItems.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-muted-foreground">
                    Inactive Items ({inactiveItems.length})
                  </h3>
                  {inactiveItems.map(item => (
                    <div key={item.cust_num} className="opacity-50">
                      <ItemRow
                        item={item}
                        onEdit={handleEdit}
                        onDelete={handleDelete}
                        deleting={deletingId === item.cust_num}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* No site selected */}
      {!selectedSite && !loading && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Select a site to view off-catalog items</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
