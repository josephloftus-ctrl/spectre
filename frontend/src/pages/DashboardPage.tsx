import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { fetchSummary } from '@/lib/api'
import { KPIGrid } from '@/components/dashboard/KPIGrid'
import { SiteMatrix } from '@/components/dashboard/SiteMatrix'
import { SiteCarousel } from '@/components/dashboard/SiteCarousel'
import { RecentNotes } from '@/components/dashboard/RecentNotes'
import { SkeletonKPI, SkeletonGrid } from '@/components/ui/skeleton'
import { Activity } from 'lucide-react'

export function DashboardPage() {
  const navigate = useNavigate()

  const { data, isLoading, error } = useQuery({
    queryKey: ['summary'],
    queryFn: fetchSummary,
    refetchInterval: 5000
  })

  if (isLoading) {
    return (
      <div className="space-y-6 animate-page-in">
        <SkeletonKPI />
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <div className="h-6 w-24 skeleton mb-3 rounded" />
            <div className="h-48 skeleton rounded-lg" />
          </div>
          <div>
            <div className="h-6 w-24 skeleton mb-3 rounded" />
            <div className="h-48 skeleton rounded-lg" />
          </div>
        </div>
        <SkeletonGrid count={6} />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4 animate-page-in">
        <div className="h-16 w-16 rounded-full bg-destructive/10 flex items-center justify-center">
          <Activity className="h-8 w-8 text-destructive" />
        </div>
        <div className="text-lg font-semibold">Connection Lost</div>
        <p className="text-muted-foreground text-center max-w-sm">
          Unable to reach the backend API. Check that the server is running.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="mt-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg btn-press hover:bg-primary/90 transition-colors"
        >
          Try Again
        </button>
      </div>
    )
  }

  const handleSiteClick = (siteId: string) => {
    navigate(`/site/${encodeURIComponent(siteId)}`)
  }

  return (
    <div className="space-y-6 animate-page-in">
      {/* KPI Section */}
      <section>
        <KPIGrid
          unitsOk={data.sites.filter((s: { issue_count?: number }) => !s.issue_count || s.issue_count === 0).length}
          unitsNeedReview={data.sites.filter((s: { issue_count?: number }) => s.issue_count && s.issue_count > 0).length}
          totalUnits={data.sites.length}
        />
      </section>

      {/* Main Content Grid */}
      <section className="grid gap-6 lg:grid-cols-3">
        {/* Site Carousel - Takes 2 columns */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold font-head">Site Focus</h2>
            <span className="text-xs text-muted-foreground">
              Auto-rotating • Click for details
            </span>
          </div>
          <SiteCarousel sites={data.sites} onSiteClick={handleSiteClick} />
        </div>

        {/* Recent Notes - Takes 1 column */}
        <div>
          <RecentNotes />
        </div>
      </section>

      {/* Site Health Matrix */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold font-head">All Sites</h2>
          <div className="text-sm text-muted-foreground bg-muted/50 px-3 py-1 rounded-full border border-border">
            {data.sites.length} Active
          </div>
        </div>
        <SiteMatrix sites={data.sites} onSiteClick={handleSiteClick} />
      </section>
    </div>
  )
}
