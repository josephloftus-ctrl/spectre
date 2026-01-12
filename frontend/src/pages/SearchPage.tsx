import { useState, useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Search, Loader2, FileSpreadsheet, Sparkles, Calendar, RefreshCw, ArrowUpDown,
  Book, Utensils, Brain, Layers, Database, ArrowRight, CheckCircle, AlertTriangle
} from 'lucide-react'
import {
  SearchResult, fetchEmbeddingStats, EmbeddingStats, resetEmbeddings, reindexEmbeddings,
  searchUnified, searchCollection, fetchCollections, fetchCollectionStats,
  migrateCollections, initCollections, CollectionInfo
} from '@/lib/api'
import { cn } from '@/lib/utils'

// ============ Shared Constants ============

const COLLECTION_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  knowledge_base: Book,
  food_knowledge: Utensils,
  living_memory: Brain,
}

const COLLECTION_COLORS: Record<string, string> = {
  knowledge_base: 'text-amber-500 bg-amber-100 dark:bg-amber-900/30',
  food_knowledge: 'text-green-500 bg-green-100 dark:bg-green-900/30',
  living_memory: 'text-purple-500 bg-purple-100 dark:bg-purple-900/30',
}

const COLLECTION_STYLES: Record<string, { bg: string; text: string; border: string }> = {
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

// ============ Utility Functions ============

function formatScore(score: number): string {
  return (score * 100).toFixed(1) + '%'
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return ''
  }
}

// ============ Result Card Component ============

interface ResultCardProps {
  result: SearchResult
  index: number
}

function ResultCard({ result, index }: ResultCardProps) {
  const metadata = result.metadata as Record<string, string | number>
  const resultDate = (result as { date?: string }).date || metadata.date as string
  const collectionName = (result as { collection?: string }).collection || metadata.collection as string
  const CollectionIcon = collectionName ? COLLECTION_ICONS[collectionName] || FileSpreadsheet : FileSpreadsheet
  const collectionColor = collectionName ? COLLECTION_COLORS[collectionName] : ''

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium text-primary">
            {index + 1}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <FileSpreadsheet className="h-4 w-4 text-green-500" />
              <span className="text-sm font-medium truncate">
                {metadata.filename || 'Unknown file'}
              </span>
              <span className={cn(
                "text-xs px-2 py-0.5 rounded-full",
                result.score > 0.7 ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
                result.score > 0.5 ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400" :
                "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400"
              )}>
                {formatScore(result.score)} match
              </span>
              {collectionName && (
                <span className={cn("text-xs px-2 py-0.5 rounded-full flex items-center gap-1", collectionColor)}>
                  <CollectionIcon className="h-3 w-3" />
                  {collectionName.replace(/_/g, ' ')}
                </span>
              )}
              {resultDate && (
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  {formatDate(resultDate)}
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground line-clamp-3">
              {result.text}
            </p>
            <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
              {metadata.chunk_index !== undefined && (
                <span>Chunk {Number(metadata.chunk_index) + 1}</span>
              )}
              {metadata.row_count && (
                <span>{metadata.row_count} rows</span>
              )}
              {metadata.site_id && (
                <span className="text-primary">{metadata.site_id}</span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ============ Collection Card Component ============

function CollectionCard({ collection }: { collection: CollectionInfo }) {
  const [expanded, setExpanded] = useState(false)
  const Icon = COLLECTION_ICONS[collection.name] || Database
  const colors = COLLECTION_STYLES[collection.name] || {
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

          <p className="text-sm text-muted-foreground">
            {COLLECTION_DESCRIPTIONS[collection.name] || collection.description}
          </p>

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
                      <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
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

// ============ Search Tab ============

function SearchTab() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [limit, setLimit] = useState(10)
  const [embeddingStats, setEmbeddingStats] = useState<EmbeddingStats | null>(null)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [sortBy, setSortBy] = useState<'relevance' | 'date_desc' | 'date_asc' | 'site'>('relevance')
  const [reindexing, setReindexing] = useState(false)
  const [reindexMessage, setReindexMessage] = useState('')
  const [collections, setCollections] = useState<CollectionInfo[]>([])
  const [selectedCollection, setSelectedCollection] = useState<string>('all')

  useEffect(() => {
    fetchEmbeddingStats()
      .then(setEmbeddingStats)
      .catch(console.error)

    fetchCollections()
      .then(({ collections }) => setCollections(collections))
      .catch(console.error)
  }, [])

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return

    setLoading(true)
    setSearched(true)
    try {
      let searchResults: SearchResult[]

      if (selectedCollection === 'all') {
        const { results } = await searchUnified(query, {
          limit,
          dateFrom: dateFrom || undefined,
          dateTo: dateTo || undefined,
        })
        searchResults = results
      } else {
        const { results } = await searchCollection(selectedCollection, query, {
          limit,
          dateFrom: dateFrom || undefined,
          dateTo: dateTo || undefined,
          sortBy,
        })
        searchResults = results
      }

      setResults(searchResults)
    } catch (error) {
      console.error('Search failed:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [query, limit, dateFrom, dateTo, sortBy, selectedCollection])

  const handleReindex = useCallback(async () => {
    if (!confirm('This will reset all embeddings and re-index all files. Continue?')) return

    setReindexing(true)
    setReindexMessage('Resetting embeddings...')
    try {
      await resetEmbeddings()
      setReindexMessage('Queueing re-index jobs...')
      const result = await reindexEmbeddings()
      setReindexMessage(`Queued ${result.queued_count} files for re-indexing`)
      setTimeout(() => {
        fetchEmbeddingStats().then(setEmbeddingStats).catch(console.error)
        setReindexMessage('')
      }, 3000)
    } catch (error) {
      console.error('Reindex failed:', error)
      setReindexMessage('Reindex failed')
    } finally {
      setReindexing(false)
    }
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const isAvailable = embeddingStats?.available ?? false
  const totalChunks = embeddingStats?.total_chunks ?? 0

  return (
    <div className="space-y-6">
      {/* Embedding stats */}
      {embeddingStats && (
        <Card className={cn(!isAvailable && 'border-yellow-500/50')}>
          <CardContent className="py-3 px-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className={cn('h-4 w-4', isAvailable ? 'text-primary' : 'text-yellow-500')} />
                {isAvailable ? (
                  <span className="text-sm">
                    <span className="font-medium">{totalChunks}</span> document chunks indexed
                    {embeddingStats.model && <span className="text-muted-foreground"> • {embeddingStats.model}</span>}
                  </span>
                ) : (
                  <span className="text-sm text-yellow-600">
                    Embedding system not available: {embeddingStats.error || 'Unknown error'}
                  </span>
                )}
                {reindexMessage && (
                  <span className="text-sm text-primary ml-2">{reindexMessage}</span>
                )}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleReindex}
                disabled={reindexing}
                className="text-xs"
              >
                {reindexing ? (
                  <Loader2 className="h-3 w-3 animate-spin mr-1" />
                ) : (
                  <RefreshCw className="h-3 w-3 mr-1" />
                )}
                Re-index
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Search input */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Ask a question or describe what you're looking for..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full pl-9 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={!isAvailable}
              />
            </div>
            <Button onClick={handleSearch} disabled={loading || !query.trim() || !isAvailable}>
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              <span className="ml-2">Search</span>
            </Button>
          </div>

          {/* Collection selector */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setSelectedCollection('all')}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-colors",
                selectedCollection === 'all'
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted hover:bg-muted/80"
              )}
            >
              <Layers className="h-3.5 w-3.5" />
              All Collections
            </button>
            {collections.map((coll) => {
              const Icon = COLLECTION_ICONS[coll.name] || FileSpreadsheet
              return (
                <button
                  key={coll.name}
                  onClick={() => setSelectedCollection(coll.name)}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-colors",
                    selectedCollection === coll.name
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted hover:bg-muted/80"
                  )}
                  title={coll.description}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {coll.name.replace(/_/g, ' ')}
                  {coll.chunk_count > 0 && (
                    <span className="text-xs opacity-70">({coll.chunk_count})</span>
                  )}
                </button>
              )
            })}
          </div>

          {/* Filters row */}
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="h-8 px-2 rounded border bg-background text-sm"
                placeholder="From"
              />
              <span className="text-muted-foreground">to</span>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="h-8 px-2 rounded border bg-background text-sm"
                placeholder="To"
              />
              {(dateFrom || dateTo) && (
                <button
                  onClick={() => { setDateFrom(''); setDateTo(''); }}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  Clear
                </button>
              )}
            </div>

            <div className="flex items-center gap-2 ml-auto">
              <ArrowUpDown className="h-4 w-4 text-muted-foreground" />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'relevance' | 'date_desc' | 'date_asc' | 'site')}
                className="h-8 px-2 rounded border bg-background text-sm"
              >
                <option value="relevance">Most Relevant</option>
                <option value="date_desc">Newest First</option>
                <option value="date_asc">Oldest First</option>
                <option value="site">Group by Site</option>
              </select>

              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="h-8 px-2 rounded border bg-background text-sm"
              >
                <option value={5}>5 results</option>
                <option value={10}>10 results</option>
                <option value={20}>20 results</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <Card className="border-dashed">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-muted flex items-center justify-center">
              <Search className="h-6 w-6 text-muted-foreground" />
            </div>
            <CardTitle>No Results Found</CardTitle>
            <CardDescription>
              Try a different search query or upload more documents to expand the search index.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {!loading && results.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Found {results.length} relevant results for "{query}"
          </p>
          {results.map((result, idx) => (
            <ResultCard key={result.id} result={result} index={idx} />
          ))}
        </div>
      )}

      {/* Initial state */}
      {!searched && !loading && (
        <Card className="border-dashed">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
              <Sparkles className="h-6 w-6 text-primary" />
            </div>
            <CardTitle>AI-Powered Search</CardTitle>
            <CardDescription className="max-w-md mx-auto">
              Search using natural language. Ask questions like "What items had the highest value drift?"
              or "Find inventory reports from January" to find relevant documents.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  )
}

// ============ Collections Tab ============

function CollectionsTab() {
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
    <div className="space-y-6">
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
            <Button variant="outline" onClick={() => refetch()} disabled={isLoading}>
              <RefreshCw className={cn("h-4 w-4 mr-2", isLoading && "animate-spin")} />
              Refresh
            </Button>
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
              Migrate spectre_documents
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
    </div>
  )
}

// ============ Main Search Page ============

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const defaultTab = searchParams.get('tab') || 'search'

  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value })
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold font-head flex items-center gap-2">
          <Search className="h-6 w-6 text-primary" />
          Search
        </h1>
        <p className="text-muted-foreground">Semantic search across your knowledge base</p>
      </div>

      <Tabs value={defaultTab} onValueChange={handleTabChange} className="space-y-4">
        <TabsList className="grid w-full grid-cols-2 max-w-xs">
          <TabsTrigger value="search" className="gap-2">
            <Search className="h-4 w-4" />
            Search
          </TabsTrigger>
          <TabsTrigger value="collections" className="gap-2">
            <Database className="h-4 w-4" />
            Collections
          </TabsTrigger>
        </TabsList>

        <TabsContent value="search">
          <SearchTab />
        </TabsContent>

        <TabsContent value="collections">
          <CollectionsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
