import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Book, Utensils, Brain, Database, RefreshCw, Loader2,
  ArrowRight, CheckCircle, AlertTriangle, FileText, Calendar
} from 'lucide-react'
import {
  fetchCollections, fetchCollectionStats, migrateCollections, initCollections,
  CollectionInfo
} from '@/lib/api'
import { cn } from '@/lib/utils'

const COLLECTION_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  knowledge_base: Book,
  food_knowledge: Utensils,
  living_memory: Brain,
}

const COLLECTION_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  knowledge_base: {
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    text: 'text-amber-600 dark:text-amber-400',
    border: 'border-amber-200 dark:border-amber-800'
  },
  food_knowledge: {
    bg: 'bg-green-50 dark:bg-green-900/20',
    text: 'text-green-600 dark:text-green-400',
    border: 'border-green-200 dark:border-green-800'
  },
  living_memory: {
    bg: 'bg-purple-50 dark:bg-purple-900/20',
    text: 'text-purple-600 dark:text-purple-400',
    border: 'border-purple-200 dark:border-purple-800'
  },
}

const COLLECTION_DESCRIPTIONS: Record<string, string> = {
  knowledge_base: 'Your company knowledge base - SOPs, training materials, inventory docs. Rarely changes.',
  food_knowledge: 'Expandable reference library - recipes, food science, vendor info. Grows over time.',
  living_memory: 'Personal work files - schedules, notes, drafts. Changes frequently.',
}

function CollectionCard({ collection }: { collection: CollectionInfo }) {
  const [expanded, setExpanded] = useState(false)
  const Icon = COLLECTION_ICONS[collection.name] || Database
  const colors = COLLECTION_COLORS[collection.name] || {
    bg: 'bg-gray-50 dark:bg-gray-900/20',
    text: 'text-gray-600 dark:text-gray-400',
    border: 'border-gray-200 dark:border-gray-800'
  }

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['collection-stats', collection.name],
    queryFn: () => fetchCollectionStats(collection.name),
    enabled: expanded,
  })

  return (
    <Card className={cn("overflow-hidden border-2", colors.border, colors.bg)}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={cn("h-12 w-12 rounded-xl flex items-center justify-center", colors.bg)}>
              <Icon className={cn("h-6 w-6", colors.text)} />
            </div>
            <div>
              <CardTitle className="text-lg capitalize">
                {collection.name.replace(/_/g, ' ')}
              </CardTitle>
              <CardDescription className="mt-1">
                {collection.description}
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {collection.exists ? (
              <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                <CheckCircle className="h-3 w-3" />
                Active
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <AlertTriangle className="h-3 w-3" />
                Empty
              </span>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-3 rounded-lg bg-background/50">
              <div className="text-2xl font-bold">{collection.chunk_count.toLocaleString()}</div>
              <div className="text-xs text-muted-foreground">Chunks</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-background/50">
              <div className={cn("text-sm font-medium px-2 py-1 rounded-full inline-block", colors.bg, colors.text)}>
                {collection.type}
              </div>
              <div className="text-xs text-muted-foreground mt-1">Type</div>
            </div>
          </div>

          {/* Description */}
          <p className="text-sm text-muted-foreground">
            {COLLECTION_DESCRIPTIONS[collection.name] || collection.description}
          </p>

          {/* Expandable Details */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
            className="w-full"
          >
            {expanded ? 'Hide Details' : 'Show Details'}
          </Button>

          {expanded && (
            <div className="space-y-3 pt-3 border-t">
              {statsLoading ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : stats ? (
                <>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span>{stats.file_count} files</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Database className="h-4 w-4 text-muted-foreground" />
                      <span>{stats.chunk_count} chunks</span>
                    </div>
                  </div>

                  {stats.sites?.length > 0 && (
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">Sites</div>
                      <div className="flex flex-wrap gap-1">
                        {stats.sites.map(site => (
                          <span key={site} className="text-xs px-2 py-0.5 bg-primary/10 rounded-full">
                            {site}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {(stats.date_range?.earliest || stats.date_range?.latest) && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-4 w-4" />
                      <span>
                        {stats.date_range.earliest?.split('T')[0] || '?'} to {stats.date_range.latest?.split('T')[0] || '?'}
                      </span>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-2">
                  No detailed stats available
                </p>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function CollectionsPage() {
  const queryClient = useQueryClient()

  const { data: collectionsData, isLoading, refetch } = useQuery({
    queryKey: ['collections'],
    queryFn: fetchCollections,
  })

  const migrateMutation = useMutation({
    mutationFn: migrateCollections,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collections'] })
    },
  })

  const initMutation = useMutation({
    mutationFn: initCollections,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collections'] })
    },
  })

  const collections = collectionsData?.collections || []
  const totalChunks = collections.reduce((sum, c) => sum + c.chunk_count, 0)

  return (
    <div className="space-y-6 animate-page-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-head flex items-center gap-2">
            <Database className="h-6 w-6 text-primary" />
            Knowledge Collections
          </h1>
          <p className="text-muted-foreground">
            Manage your RAG knowledge bases
          </p>
        </div>
        <Button variant="outline" onClick={() => refetch()} disabled={isLoading}>
          <RefreshCw className={cn("h-4 w-4 mr-2", isLoading && "animate-spin")} />
          Refresh
        </Button>
      </div>

      {/* Overview Stats */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <div className="text-2xl font-bold">{collections.length}</div>
                <div className="text-xs text-muted-foreground">Collections</div>
              </div>
              <div className="h-8 w-px bg-border" />
              <div>
                <div className="text-2xl font-bold">{totalChunks.toLocaleString()}</div>
                <div className="text-xs text-muted-foreground">Total Chunks</div>
              </div>
              <div className="h-8 w-px bg-border" />
              <div>
                <div className="text-2xl font-bold">
                  {collections.filter(c => c.exists).length}
                </div>
                <div className="text-xs text-muted-foreground">Active</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Migration Card */}
      <Card className="border-dashed">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <ArrowRight className="h-4 w-4" />
            Migration Tools
          </CardTitle>
          <CardDescription>
            One-time setup actions for your collections
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Button
              variant="outline"
              onClick={() => migrateMutation.mutate()}
              disabled={migrateMutation.isPending}
            >
              {migrateMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4 mr-2" />
              )}
              Migrate spectre_documents → knowledge_base
            </Button>

            <Button
              variant="outline"
              onClick={() => initMutation.mutate()}
              disabled={initMutation.isPending}
            >
              {initMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Database className="h-4 w-4 mr-2" />
              )}
              Initialize All Collections
            </Button>
          </div>

          {migrateMutation.isSuccess && (
            <p className="text-sm text-green-600 mt-3">
              Migration complete: {migrateMutation.data?.message}
            </p>
          )}
          {migrateMutation.isError && (
            <p className="text-sm text-red-600 mt-3">
              Migration failed. Check console for details.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Collection Cards */}
      {isLoading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-64 skeleton rounded-lg" />
          ))}
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {collections.map(collection => (
            <CollectionCard key={collection.name} collection={collection} />
          ))}
        </div>
      )}

      {/* Usage Tips */}
      <Card className="bg-muted/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">How to Use Collections</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <div className="flex items-start gap-3">
            <Book className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-medium text-foreground">Knowledge Base</span> - Upload your SOPs, training docs, and company reference materials. These are your "golden" documents that rarely change.
            </div>
          </div>
          <div className="flex items-start gap-3">
            <Utensils className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-medium text-foreground">Food Knowledge</span> - Add recipes, food science articles, vendor specifications. This collection grows over time as you discover new resources.
            </div>
          </div>
          <div className="flex items-start gap-3">
            <Brain className="h-5 w-5 text-purple-500 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-medium text-foreground">Living Memory</span> - Your personal workspace. Upload schedules, notes, working files. This powers the "Day At A Glance" feature.
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
