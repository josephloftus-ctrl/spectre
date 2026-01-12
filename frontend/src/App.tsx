import { Routes, Route, Navigate } from 'react-router-dom'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { DashboardPage, DocumentsPage, NotesPage, SettingsPage, SitePage, AssistantPage, SearchPage, InventoryPage, PurchaseMatchDetailPage, PurchaseMatchCategoryPage, CartPage, CountSessionPage } from '@/pages'

function App() {
  return (
    <DashboardLayout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />

        {/* Inventory - consolidated view with tabs */}
        <Route path="/inventory" element={<InventoryPage />} />
        <Route path="/inventory/site/:siteId" element={<SitePage />} />
        <Route path="/inventory/match/:unit" element={<PurchaseMatchDetailPage />} />
        <Route path="/inventory/match/category/:category" element={<PurchaseMatchCategoryPage />} />

        {/* Redirects for old routes */}
        <Route path="/scores" element={<Navigate to="/inventory?tab=health" replace />} />
        <Route path="/history" element={<Navigate to="/inventory?tab=history" replace />} />
        <Route path="/purchase-match" element={<Navigate to="/inventory?tab=match" replace />} />
        <Route path="/purchase-match/category/:category" element={<Navigate to="/inventory/match/category/:category" replace />} />
        <Route path="/purchase-match/:unit" element={<Navigate to="/inventory/match/:unit" replace />} />
        <Route path="/system" element={<Navigate to="/settings?debug=1" replace />} />

        {/* Legacy site routes - redirect to new location */}
        <Route path="/site/:siteId" element={<SitePage />} />
        <Route path="/:siteId" element={<SitePage />} />

        {/* Cart and Count Sessions */}
        <Route path="/cart" element={<CartPage />} />
        <Route path="/count" element={<CountSessionPage />} />

        {/* Standard pages */}
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/inbox" element={<Navigate to="/documents?tab=upload" replace />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/notes" element={<NotesPage />} />
        <Route path="/assistant" element={<AssistantPage />} />
        <Route path="/settings" element={<SettingsPage />} />

        {/* Redirect for consolidated pages */}
        <Route path="/collections" element={<Navigate to="/search?tab=collections" replace />} />

        {/* Redirects for consolidated pages */}
        <Route path="/ai" element={<Navigate to="/assistant" replace />} />
        <Route path="/standup" element={<Navigate to="/assistant" replace />} />
        <Route path="/glance" element={<Navigate to="/" replace />} />
      </Routes>
    </DashboardLayout>
  )
}

export default App
