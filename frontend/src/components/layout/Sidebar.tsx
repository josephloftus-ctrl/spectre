import { useLocation } from 'react-router-dom'

// Helper to get page title from path
export function usePageTitle(): string {
    const location = useLocation()

    // Handle dynamic routes under /inventory
    if (location.pathname.startsWith('/inventory/site/')) {
        return 'Site Details'
    }
    if (location.pathname.startsWith('/inventory/match/')) {
        return 'Purchase Match'
    }
    if (location.pathname.startsWith('/inventory')) {
        return 'Inventory'
    }

    const titles: Record<string, string> = {
        '/': 'Dashboard',
        '/inbox': 'Inbox',
        '/documents': 'Documents',
        '/search': 'Search',
        '/notes': 'Notes',
        '/ai': 'AI Assistant',
        '/standup': 'Daily Standup',
        '/glance': 'Day At A Glance',
        '/collections': 'Collections',
        '/settings': 'Settings'
    }

    // Check for site detail pages (e.g., /pseg_nhq) - legacy routes
    if (location.pathname !== '/' && !titles[location.pathname]) {
        return 'Site Details'
    }

    return titles[location.pathname] || 'Ops Dash'
}
