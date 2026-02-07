import { useState, useCallback } from 'react'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Search, Loader2, FileSpreadsheet, Calendar, ArrowUpDown
} from 'lucide-react'
import { SearchResult, searchDocuments } from '@/lib/api'
import { cn } from '@/lib/utils'

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

// ============ Main Search Page ============

export function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [limit, setLimit] = useState(10)
  const [sortBy, setSortBy] = useState<'relevance' | 'date_desc' | 'date_asc' | 'site'>('relevance')

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return

    setLoading(true)
    setSearched(true)
    try {
      const { results: searchResults } = await searchDocuments(
        query, limit, undefined, undefined, undefined, sortBy
      )
      setResults(searchResults)
    } catch (error) {
      console.error('Search failed:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [query, limit, sortBy])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold font-head flex items-center gap-2">
          <Search className="h-6 w-6 text-primary" />
          Search
        </h1>
        <p className="text-muted-foreground">Search across your documents and product catalog</p>
      </div>

      {/* Search input */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search documents, products, SKUs..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full pl-9 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <Button onClick={handleSearch} disabled={loading || !query.trim()}>
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              <span className="ml-2">Search</span>
            </Button>
          </div>

          {/* Filters row */}
          <div className="flex flex-wrap items-center gap-3 text-sm">
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
              Try a different search query or upload more documents.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {!loading && results.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Found {results.length} results for "{query}"
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
              <Search className="h-6 w-6 text-primary" />
            </div>
            <CardTitle>Product & Document Search</CardTitle>
            <CardDescription className="max-w-md mx-auto">
              Search your MOG product catalog and uploaded documents by keyword.
              Try searching for a product name, SKU, or vendor.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  )
}
