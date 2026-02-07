import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { CommandBar } from '@/components/command'
import {
  DashboardPage, InboxPage, IssuesPage, InventoryPage,
  NotesPage, SettingsPage, SitePage, AssistantPage, SearchPage,
  PurchaseMatchDetailPage, PurchaseMatchCategoryPage,
  CartPage, CountSessionPage, OffCatalogPage, RoomsPage,
  MenuPlanningPage
} from '@/pages'

function App() {
  return (
    <>
      <CommandBar />
      <AppShell>
        <Routes>
          {/* Main Views */}
          <Route path="/" element={<DashboardPage />} />
          <Route path="/inbox" element={<InboxPage />} />
          <Route path="/issues" element={<IssuesPage />} />
          <Route path="/inventory" element={<InventoryPage />} />

          {/* Inventory sub-routes */}
          <Route path="/inventory/site/:siteId" element={<SitePage />} />
          <Route path="/inventory/match/:unit" element={<PurchaseMatchDetailPage />} />
          <Route path="/inventory/match/category/:category" element={<PurchaseMatchCategoryPage />} />

          {/* Utility pages */}
          <Route path="/cart" element={<CartPage />} />
          <Route path="/count" element={<CountSessionPage />} />
          <Route path="/off-catalog" element={<OffCatalogPage />} />
          <Route path="/rooms" element={<RoomsPage />} />
          <Route path="/menu-planning" element={<MenuPlanningPage />} />
          <Route path="/notes" element={<NotesPage />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/settings" element={<SettingsPage />} />

          {/* Legacy redirects */}
          <Route path="/dashboard" element={<Navigate to="/" replace />} />
          <Route path="/documents" element={<Navigate to="/inbox" replace />} />
          <Route path="/scores" element={<Navigate to="/inventory" replace />} />
          <Route path="/history" element={<Navigate to="/inventory" replace />} />
          <Route path="/purchase-match" element={<Navigate to="/inventory" replace />} />
          <Route path="/collections" element={<Navigate to="/search" replace />} />
          <Route path="/ai" element={<Navigate to="/assistant" replace />} />
          <Route path="/standup" element={<Navigate to="/assistant" replace />} />
          <Route path="/glance" element={<Navigate to="/issues" replace />} />
          <Route path="/system" element={<Navigate to="/settings" replace />} />

          {/* Legacy site routes */}
          <Route path="/site/:siteId" element={<SitePage />} />
          <Route path="/:siteId" element={<SitePage />} />
        </Routes>
      </AppShell>
    </>
  )
}

export default App
