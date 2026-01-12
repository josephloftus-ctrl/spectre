import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  ShoppingCart, Loader2, Trash2, Download, Plus, Minus, Package, RefreshCw,
  AlertCircle, Search, Filter, X
} from 'lucide-react'
import {
  fetchCart, updateCartItemQuantity, removeFromCart, clearCart, exportCart,
  addToCart, fetchInventoryItems, CartItem, CartResponse, fetchSummary, InventoryItem
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

// Cart item row component
interface CartItemRowProps {
  item: CartItem
  onUpdateQuantity: (sku: string, quantity: number) => Promise<void>
  onRemove: (sku: string) => Promise<void>
  updating: boolean
}

function CartItemRow({ item, onUpdateQuantity, onRemove, updating }: CartItemRowProps) {
  const [localQty, setLocalQty] = useState(item.quantity.toString())

  useEffect(() => {
    setLocalQty(item.quantity.toString())
  }, [item.quantity])

  const handleQuantityBlur = async () => {
    const newQty = parseFloat(localQty)
    if (!isNaN(newQty) && newQty !== item.quantity && newQty > 0) {
      await onUpdateQuantity(item.sku, newQty)
    } else {
      setLocalQty(item.quantity.toString())
    }
  }

  const handleIncrement = () => {
    const newQty = item.quantity + 1
    setLocalQty(newQty.toString())
    onUpdateQuantity(item.sku, newQty)
  }

  const handleDecrement = () => {
    if (item.quantity > 1) {
      const newQty = item.quantity - 1
      setLocalQty(newQty.toString())
      onUpdateQuantity(item.sku, newQty)
    }
  }

  const total = item.quantity * (item.unit_price || 0)

  return (
    <div className={cn(
      "flex items-center gap-4 p-4 rounded-lg border bg-card",
      updating && "opacity-50 pointer-events-none"
    )}>
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate" title={item.description}>
          {item.description}
        </p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-mono">{item.sku}</span>
          {item.vendor && (
            <>
              <span>•</span>
              <Badge variant="outline" className="text-xs py-0">{item.vendor}</Badge>
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

      <div className="flex items-center gap-1">
        <Button variant="outline" size="icon" className="h-8 w-8" onClick={handleDecrement} disabled={item.quantity <= 1}>
          <Minus className="h-3 w-3" />
        </Button>
        <Input
          value={localQty}
          onChange={(e) => setLocalQty(e.target.value)}
          onBlur={handleQuantityBlur}
          onKeyDown={(e) => e.key === 'Enter' && handleQuantityBlur()}
          className="w-16 h-8 text-center font-mono"
        />
        <Button variant="outline" size="icon" className="h-8 w-8" onClick={handleIncrement}>
          <Plus className="h-3 w-3" />
        </Button>
      </div>

      <div className="text-right min-w-[80px]">
        {item.unit_price ? (
          <>
            <p className="font-mono font-medium">${total.toFixed(2)}</p>
            <p className="text-xs text-muted-foreground">${item.unit_price.toFixed(2)} ea</p>
          </>
        ) : (
          <p className="text-muted-foreground">-</p>
        )}
      </div>

      <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10" onClick={() => onRemove(item.sku)}>
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  )
}

// Inventory item row for adding to cart
interface InventoryItemRowProps {
  item: InventoryItem
  inCart: boolean
  onAdd: (item: InventoryItem) => void
  adding: boolean
}

function InventoryItemRow({ item, inCart, onAdd, adding }: InventoryItemRowProps) {
  return (
    <div className={cn(
      "flex items-center gap-4 p-3 rounded-lg border bg-card",
      inCart && "border-primary/50 bg-primary/5"
    )}>
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate text-sm" title={item.description}>
          {item.description}
        </p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-mono">{item.sku}</span>
          {item.vendor && (
            <>
              <span>•</span>
              <span>{item.vendor}</span>
            </>
          )}
        </div>
      </div>
      {item.unit_price && (
        <span className="text-sm font-mono">${item.unit_price.toFixed(2)}</span>
      )}
      <Button
        size="sm"
        variant={inCart ? "secondary" : "default"}
        onClick={() => onAdd(item)}
        disabled={adding || inCart}
      >
        {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : inCart ? 'In Cart' : <Plus className="h-4 w-4" />}
      </Button>
    </div>
  )
}

export function CartPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const siteId = searchParams.get('site') || ''

  const [sites, setSites] = useState<string[]>([])
  const [cart, setCart] = useState<CartResponse | null>(null)
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingInventory, setLoadingInventory] = useState(false)
  const [updating, setUpdating] = useState<string | null>(null)
  const [clearing, setClearing] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [addingItem, setAddingItem] = useState<string | null>(null)

  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [vendorFilter, setVendorFilter] = useState<string>('all')
  const [showAddItems, setShowAddItems] = useState(false)

  // Load available sites
  useEffect(() => {
    fetchSummary().then(summary => {
      const siteIds = summary.sites.map(s => s.site)
      setSites(siteIds)
      if (!siteId && siteIds.length > 0) {
        setSearchParams({ site: siteIds[0] })
      }
    }).catch(err => {
      console.error('Failed to fetch sites:', err)
    })
  }, [])

  const loadCart = useCallback(async () => {
    if (!siteId) return
    try {
      setLoading(true)
      const data = await fetchCart(siteId)
      setCart(data)
    } catch (error) {
      console.error('Failed to fetch cart:', error)
      setCart(null)
    } finally {
      setLoading(false)
    }
  }, [siteId])

  const loadInventory = useCallback(async () => {
    if (!siteId) return
    try {
      setLoadingInventory(true)
      const response = await fetchInventoryItems(siteId)
      setInventoryItems(response.items || [])
    } catch (error) {
      console.error('Failed to fetch inventory:', error)
      setInventoryItems([])
    } finally {
      setLoadingInventory(false)
    }
  }, [siteId])

  useEffect(() => {
    loadCart()
    loadInventory()
  }, [loadCart, loadInventory])

  // Get unique vendors from cart items
  const vendors = useMemo(() => {
    if (!cart?.items) return []
    const vendorSet = new Set(cart.items.map(i => i.vendor).filter(Boolean))
    return Array.from(vendorSet).sort() as string[]
  }, [cart?.items])

  // Get unique vendors from inventory
  const inventoryVendors = useMemo(() => {
    const vendorSet = new Set(inventoryItems.map(i => i.vendor).filter(Boolean))
    return Array.from(vendorSet).sort() as string[]
  }, [inventoryItems])

  // Filter cart items
  const filteredCartItems = useMemo(() => {
    if (!cart?.items) return []
    return cart.items.filter(item => {
      if (vendorFilter !== 'all' && item.vendor !== vendorFilter) return false
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        return (
          item.description.toLowerCase().includes(query) ||
          item.sku.toLowerCase().includes(query) ||
          item.vendor?.toLowerCase().includes(query)
        )
      }
      return true
    })
  }, [cart?.items, vendorFilter, searchQuery])

  // Filter inventory items for adding
  const filteredInventoryItems = useMemo(() => {
    const cartSkus = new Set(cart?.items.map(i => i.sku) || [])
    return inventoryItems.filter(item => {
      if (vendorFilter !== 'all' && item.vendor !== vendorFilter) return false
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        return (
          item.description.toLowerCase().includes(query) ||
          item.sku.toLowerCase().includes(query) ||
          item.vendor?.toLowerCase().includes(query)
        )
      }
      return true
    }).map(item => ({
      ...item,
      inCart: cartSkus.has(item.sku)
    }))
  }, [inventoryItems, cart?.items, vendorFilter, searchQuery])

  const handleSiteChange = (site: string) => {
    setSearchParams({ site })
    setVendorFilter('all')
    setSearchQuery('')
  }

  const handleUpdateQuantity = async (sku: string, quantity: number) => {
    if (!siteId) return
    try {
      setUpdating(sku)
      await updateCartItemQuantity(siteId, sku, quantity)
      await loadCart()
    } catch (error) {
      console.error('Failed to update quantity:', error)
    } finally {
      setUpdating(null)
    }
  }

  const handleRemove = async (sku: string) => {
    if (!siteId) return
    try {
      setUpdating(sku)
      await removeFromCart(siteId, sku)
      await loadCart()
    } catch (error) {
      console.error('Failed to remove item:', error)
    } finally {
      setUpdating(null)
    }
  }

  const handleClearCart = async () => {
    if (!siteId) return
    try {
      setClearing(true)
      await clearCart(siteId)
      await loadCart()
    } catch (error) {
      console.error('Failed to clear cart:', error)
    } finally {
      setClearing(false)
    }
  }

  const handleExport = () => {
    if (!siteId) return
    setExporting(true)
    window.location.href = exportCart(siteId)
    setTimeout(() => setExporting(false), 2000)
  }

  const handleAddItem = async (item: InventoryItem) => {
    if (!siteId) return
    try {
      setAddingItem(item.sku)
      await addToCart(siteId, {
        sku: item.sku,
        description: item.description,
        quantity: 1,
        unit_price: item.unit_price || undefined,
        uom: item.uom || undefined,
        vendor: item.vendor || undefined
      })
      await loadCart()
    } catch (error) {
      console.error('Failed to add item:', error)
    } finally {
      setAddingItem(null)
    }
  }

  const itemCount = cart?.summary.item_count || 0
  const totalValue = cart?.summary.total_value || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-head flex items-center gap-2">
            <ShoppingCart className="h-6 w-6" />
            Order Builder
          </h1>
          <p className="text-muted-foreground">
            {itemCount > 0 ? (
              <>
                {itemCount} item{itemCount !== 1 ? 's' : ''} •
                <span className="font-mono ml-1">${totalValue.toFixed(2)}</span>
              </>
            ) : (
              'Build your order from inventory'
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={siteId} onValueChange={handleSiteChange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select site" />
            </SelectTrigger>
            <SelectContent>
              {sites.map(site => (
                <SelectItem key={site} value={site}>{site}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={loadCart} disabled={loading || !siteId}>
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {/* No site selected */}
      {!siteId && sites.length === 0 && !loading && (
        <Card className="border-dashed">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-muted flex items-center justify-center">
              <AlertCircle className="h-6 w-6 text-muted-foreground" />
            </div>
            <CardTitle>No Sites Available</CardTitle>
            <CardDescription>Upload inventory files to create sites and start building orders.</CardDescription>
          </CardHeader>
        </Card>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Main content */}
      {!loading && siteId && cart && (
        <>
          {/* Search and filter bar */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search items..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
              {searchQuery && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                  onClick={() => setSearchQuery('')}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
            <Select value={vendorFilter} onValueChange={setVendorFilter}>
              <SelectTrigger className="w-[180px]">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="All vendors" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Vendors</SelectItem>
                {(showAddItems ? inventoryVendors : vendors).map(vendor => (
                  <SelectItem key={vendor} value={vendor}>{vendor}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant={showAddItems ? "secondary" : "outline"}
              onClick={() => setShowAddItems(!showAddItems)}
            >
              <Plus className="h-4 w-4 mr-2" />
              {showAddItems ? 'Hide Inventory' : 'Add Items'}
            </Button>
          </div>

          {/* Add items from inventory panel */}
          {showAddItems && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Package className="h-4 w-4" />
                  Add from Inventory
                </CardTitle>
                <CardDescription>
                  {loadingInventory ? 'Loading...' : `${filteredInventoryItems.length} items available`}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loadingInventory ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : filteredInventoryItems.length === 0 ? (
                  <p className="text-center text-muted-foreground py-4">
                    {searchQuery || vendorFilter !== 'all' ? 'No items match your filters' : 'No inventory items found'}
                  </p>
                ) : (
                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {filteredInventoryItems.slice(0, 50).map(item => (
                      <InventoryItemRow
                        key={item.sku}
                        item={item}
                        inCart={item.inCart}
                        onAdd={handleAddItem}
                        adding={addingItem === item.sku}
                      />
                    ))}
                    {filteredInventoryItems.length > 50 && (
                      <p className="text-center text-sm text-muted-foreground py-2">
                        Showing 50 of {filteredInventoryItems.length} items. Use search to find more.
                      </p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Cart items */}
          {cart.items.length === 0 ? (
            <Card className="border-dashed">
              <CardHeader className="text-center">
                <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-muted flex items-center justify-center">
                  <Package className="h-6 w-6 text-muted-foreground" />
                </div>
                <CardTitle>Cart is Empty</CardTitle>
                <CardDescription>
                  Click "Add Items" above to start building your order from inventory.
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <>
              {/* Action bar */}
              <div className="flex justify-between items-center">
                <div className="text-sm text-muted-foreground">
                  {filteredCartItems.length !== cart.items.length && (
                    <span>Showing {filteredCartItems.length} of {cart.items.length} items</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="outline" size="sm" disabled={clearing}>
                        {clearing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Trash2 className="h-4 w-4 mr-2" />}
                        Clear
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Clear Order?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This will remove all {itemCount} items. This action cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={handleClearCart}>Clear</AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                  <Button size="sm" onClick={handleExport} disabled={exporting}>
                    {exporting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Download className="h-4 w-4 mr-2" />}
                    Export Order
                  </Button>
                </div>
              </div>

              {/* Items list grouped by vendor when filtered */}
              {vendorFilter !== 'all' ? (
                <div className="space-y-2">
                  {filteredCartItems.map(item => (
                    <CartItemRow
                      key={item.sku}
                      item={item}
                      onUpdateQuantity={handleUpdateQuantity}
                      onRemove={handleRemove}
                      updating={updating === item.sku}
                    />
                  ))}
                </div>
              ) : (
                // Group by vendor
                <div className="space-y-6">
                  {vendors.length > 0 ? (
                    vendors.map(vendor => {
                      const vendorItems = filteredCartItems.filter(i => i.vendor === vendor)
                      if (vendorItems.length === 0) return null
                      const vendorTotal = vendorItems.reduce((sum, i) => sum + (i.quantity * (i.unit_price || 0)), 0)
                      return (
                        <div key={vendor} className="space-y-2">
                          <div className="flex items-center justify-between">
                            <h3 className="font-medium flex items-center gap-2">
                              <Badge variant="outline">{vendor}</Badge>
                              <span className="text-sm text-muted-foreground">{vendorItems.length} items</span>
                            </h3>
                            <span className="font-mono text-sm">${vendorTotal.toFixed(2)}</span>
                          </div>
                          {vendorItems.map(item => (
                            <CartItemRow
                              key={item.sku}
                              item={item}
                              onUpdateQuantity={handleUpdateQuantity}
                              onRemove={handleRemove}
                              updating={updating === item.sku}
                            />
                          ))}
                        </div>
                      )
                    })
                  ) : (
                    <div className="space-y-2">
                      {filteredCartItems.map(item => (
                        <CartItemRow
                          key={item.sku}
                          item={item}
                          onUpdateQuantity={handleUpdateQuantity}
                          onRemove={handleRemove}
                          updating={updating === item.sku}
                        />
                      ))}
                    </div>
                  )}
                  {/* Items without vendor */}
                  {filteredCartItems.filter(i => !i.vendor).length > 0 && vendors.length > 0 && (
                    <div className="space-y-2">
                      <h3 className="font-medium flex items-center gap-2">
                        <Badge variant="secondary">No Vendor</Badge>
                        <span className="text-sm text-muted-foreground">
                          {filteredCartItems.filter(i => !i.vendor).length} items
                        </span>
                      </h3>
                      {filteredCartItems.filter(i => !i.vendor).map(item => (
                        <CartItemRow
                          key={item.sku}
                          item={item}
                          onUpdateQuantity={handleUpdateQuantity}
                          onRemove={handleRemove}
                          updating={updating === item.sku}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Summary */}
              <Card>
                <CardContent className="pt-6">
                  <div className="flex justify-between items-center text-lg font-semibold">
                    <span>Total ({itemCount} items)</span>
                    <span className="font-mono">${totalValue.toFixed(2)}</span>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </>
      )}
    </div>
  )
}
