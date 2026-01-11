import { useState, useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  FileSpreadsheet, Search, RefreshCw, Loader2,
  CheckCircle2, AlertCircle, Clock, Cog,
  FolderOpen, Unplug, Radio, Book, Utensils, Brain,
  Upload, Files, Trash2, Database, MoreVertical, StopCircle
} from 'lucide-react'
import { DropZone, FileCard, FileStatus as InboxFileStatus } from '@/components/inbox'
import { useFolderPicker } from '@/hooks'
import { uploadFile, fetchFiles, retryFile, deleteFile, reembedFile, fetchCollections, fetchJobs, cancelJob, cancelAllJobs, FileRecord, FileStatus, CollectionInfo, JobRecord } from '@/lib/api'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from '@/lib/utils'

// ============ Shared Constants ============

const COLLECTION_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  culinart_bible: Book,
  food_knowledge: Utensils,
  living_memory: Brain,
}

const statusConfig: Record<FileStatus, { icon: typeof Clock; label: string; color: string }> = {
  pending: { icon: Clock, label: 'Pending', color: 'text-yellow-500' },
  processing: { icon: Cog, label: 'Processing', color: 'text-blue-500' },
  completed: { icon: CheckCircle2, label: 'Completed', color: 'text-green-500' },
  failed: { icon: AlertCircle, label: 'Failed', color: 'text-destructive' }
}

// ============ Utility Functions ============

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function getFileType(filename: string): 'xlsx' | 'xls' | 'pdf' | 'csv' {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (ext === 'xlsx') return 'xlsx'
  if (ext === 'xls') return 'xls'
  if (ext === 'pdf') return 'pdf'
  return 'csv'
}

// ============ Types ============

interface PendingFile {
  id: string
  file: File
  status: InboxFileStatus
  errorMessage?: string
  backendId?: string
}

interface DocumentCardProps {
  file: FileRecord
  onRetry: (id: string) => void
  onDelete: (id: string) => void
  onReembed: (id: string) => void
  onCancel: (id: string) => void
  retrying: boolean
  deleting: boolean
  reembedding: boolean
  cancelling: boolean
}

// ============ Document Card Component ============

function DocumentCard({ file, onRetry, onDelete, onReembed, onCancel, retrying, deleting, reembedding, cancelling }: DocumentCardProps) {
  const status = statusConfig[file.status]
  const StatusIcon = status.icon
  const isLoading = retrying || deleting || reembedding || cancelling

  return (
    <Card className={cn(file.status === 'failed' && 'border-destructive/50')}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 text-green-500">
            <FileSpreadsheet className="h-8 w-8" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate" title={file.filename}>
              {file.filename}
            </p>
            <p className="text-xs text-muted-foreground">
              {formatFileSize(file.file_size)} • {file.file_type.toUpperCase()}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {formatDate(file.created_at)}
            </p>
            {file.error_message && (
              <p className="text-xs text-destructive mt-1 truncate" title={file.error_message}>
                {file.error_message}
              </p>
            )}
          </div>
          <div className="flex-shrink-0 flex flex-col items-end gap-2">
            <div className={cn('flex items-center gap-1 text-xs', status.color)}>
              <StatusIcon className={cn('h-3.5 w-3.5', file.status === 'processing' && 'animate-spin')} />
              {status.label}
            </div>
            <div className="flex items-center gap-1">
              {file.status === 'failed' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onRetry(file.id)}
                  disabled={isLoading}
                >
                  {retrying ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <RefreshCw className="h-3 w-3" />
                  )}
                  <span className="ml-1">Retry</span>
                </Button>
              )}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" disabled={isLoading}>
                    {isLoading && !retrying ? <Loader2 className="h-3 w-3 animate-spin" /> : <MoreVertical className="h-3 w-3" />}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {(file.status === 'pending' || file.status === 'processing') && (
                    <DropdownMenuItem onClick={() => onCancel(file.id)}>
                      <StopCircle className="h-4 w-4 mr-2" />
                      Cancel Jobs
                    </DropdownMenuItem>
                  )}
                  {file.status === 'completed' && (
                    <DropdownMenuItem onClick={() => onReembed(file.id)}>
                      <Database className="h-4 w-4 mr-2" />
                      Re-embed
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuItem
                    onClick={() => onDelete(file.id)}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ============ Upload Tab ============

function UploadTab() {
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([])
  const [collections, setCollections] = useState<CollectionInfo[]>([])
  const [selectedCollection, setSelectedCollection] = useState('culinart_bible')

  useEffect(() => {
    fetchCollections()
      .then(({ collections }) => setCollections(collections))
      .catch(console.error)
  }, [])

  const handleFilesDropped = useCallback((files: File[]) => {
    const newFiles: PendingFile[] = files.map(file => ({
      id: crypto.randomUUID(),
      file,
      status: 'pending' as InboxFileStatus
    }))
    setPendingFiles(prev => [...newFiles, ...prev])
  }, [])

  const {
    isSupported: isFolderPickerSupported,
    isConnected,
    folderName,
    isScanning,
    autoScanEnabled,
    pickFolder,
    disconnect,
    scanFolder,
    toggleAutoScan
  } = useFolderPicker(handleFilesDropped)

  const handleScanFolder = useCallback(async () => {
    try {
      await scanFolder(false)
    } catch (e) {
      console.error('Scan failed:', e)
    }
  }, [scanFolder])

  const handleRemoveFile = useCallback((id: string) => {
    setPendingFiles(prev => prev.filter(f => f.id !== id))
  }, [])

  const handleProcessFile = useCallback(async (id: string) => {
    const pendingFile = pendingFiles.find(f => f.id === id)
    if (!pendingFile) return

    setPendingFiles(prev =>
      prev.map(f => f.id === id ? { ...f, status: 'processing' as InboxFileStatus } : f)
    )

    try {
      const fileRecord = await uploadFile(pendingFile.file)
      const uiStatus: InboxFileStatus =
        fileRecord.status === 'completed' ? 'ready' :
        fileRecord.status === 'failed' ? 'error' :
        fileRecord.status === 'processing' ? 'processing' : 'ready'

      setPendingFiles(prev =>
        prev.map(f => f.id === id ? {
          ...f,
          status: uiStatus,
          backendId: fileRecord.id,
          errorMessage: fileRecord.error_message || undefined
        } : f)
      )
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed'
      setPendingFiles(prev =>
        prev.map(f => f.id === id ? {
          ...f,
          status: 'error' as InboxFileStatus,
          errorMessage
        } : f)
      )
    }
  }, [pendingFiles])

  const handleProcessAll = useCallback(async () => {
    const pending = pendingFiles.filter(f => f.status === 'pending')
    for (const file of pending) {
      await handleProcessFile(file.id)
    }
  }, [pendingFiles, handleProcessFile])

  const pendingCount = pendingFiles.filter(f => f.status === 'pending').length

  return (
    <div className="space-y-6">
      {pendingCount > 0 && (
        <div className="flex justify-end">
          <Button onClick={handleProcessAll}>
            Process All ({pendingCount})
          </Button>
        </div>
      )}

      {/* Collection Selector */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Upload To Collection</CardTitle>
          <CardDescription>
            Select which knowledge base to add files to
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {collections.map((coll) => {
              const Icon = COLLECTION_ICONS[coll.name] || FileSpreadsheet
              return (
                <button
                  key={coll.name}
                  onClick={() => setSelectedCollection(coll.name)}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-lg border-2 transition-colors",
                    selectedCollection === coll.name
                      ? "border-primary bg-primary/5"
                      : "border-muted hover:border-muted-foreground/30"
                  )}
                >
                  <Icon className={cn("h-5 w-5", selectedCollection === coll.name ? "text-primary" : "text-muted-foreground")} />
                  <div className="text-left">
                    <div className={cn("font-medium text-sm", selectedCollection === coll.name ? "text-primary" : "")}>
                      {coll.name.replace(/_/g, ' ')}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {coll.chunk_count} chunks
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Folder Connection */}
      {isFolderPickerSupported && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <FolderOpen className="h-4 w-4" />
              Synced Folder
            </CardTitle>
            <CardDescription>
              Connect to your OneDrive sync folder for quick imports
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isConnected ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <FolderOpen className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium">{folderName}</p>
                      <p className="text-xs text-muted-foreground">
                        {autoScanEnabled ? (
                          <span className="flex items-center gap-1">
                            <Radio className="h-3 w-3 text-primary animate-pulse" />
                            Auto-watching for new files
                          </span>
                        ) : (
                          'Connected'
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant={autoScanEnabled ? "secondary" : "outline"}
                      size="sm"
                      onClick={toggleAutoScan}
                    >
                      <Radio className={`h-4 w-4 mr-2 ${autoScanEnabled ? 'text-primary' : ''}`} />
                      {autoScanEnabled ? 'Auto' : 'Manual'}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleScanFolder}
                      disabled={isScanning}
                    >
                      <RefreshCw className={`h-4 w-4 mr-2 ${isScanning ? 'animate-spin' : ''}`} />
                      {isScanning ? 'Scanning...' : 'Scan'}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={disconnect}
                    >
                      <Unplug className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <Button variant="outline" onClick={pickFolder}>
                <FolderOpen className="h-4 w-4 mr-2" />
                Connect Folder
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Drop Zone */}
      <DropZone onFilesDropped={handleFilesDropped} />

      {/* Pending Files */}
      {pendingFiles.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Pending ({pendingFiles.length})</h2>
            {pendingFiles.some(f => f.status === 'ready') && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPendingFiles(prev => prev.filter(f => f.status !== 'ready'))}
              >
                Clear completed
              </Button>
            )}
          </div>

          <div className="space-y-2">
            {pendingFiles.map(pf => (
              <FileCard
                key={pf.id}
                filename={pf.file.name}
                fileType={getFileType(pf.file.name)}
                fileSize={pf.file.size}
                status={pf.status}
                errorMessage={pf.errorMessage}
                onProcess={pf.status === 'pending' ? () => handleProcessFile(pf.id) : undefined}
                onRemove={() => handleRemoveFile(pf.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {pendingFiles.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <FileSpreadsheet className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground">
              No files yet. Drop Excel or PDF files above, or connect a synced folder.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// ============ Files Tab ============

type FilterStatus = FileStatus | 'all'

function FilesTab() {
  const [files, setFiles] = useState<FileRecord[]>([])
  const [activeJobs, setActiveJobs] = useState<JobRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<FilterStatus>('all')
  const [retryingIds, setRetryingIds] = useState<Set<string>>(new Set())
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set())
  const [reembeddingIds, setReembeddingIds] = useState<Set<string>>(new Set())
  const [cancellingIds, setCancellingIds] = useState<Set<string>>(new Set())
  const [cancellingAll, setCancellingAll] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showSearch, setShowSearch] = useState(false)

  const loadFiles = useCallback(async () => {
    try {
      setLoading(true)
      const statusFilter = filter === 'all' ? undefined : filter
      const [{ files: fetchedFiles }, { jobs }] = await Promise.all([
        fetchFiles({ status: statusFilter, limit: 200 }),
        fetchJobs({ limit: 100 })
      ])
      setFiles(fetchedFiles)
      // Track active jobs (queued or running)
      setActiveJobs(jobs.filter(j => j.status === 'queued' || j.status === 'running'))
    } catch (error) {
      console.error('Failed to fetch files:', error)
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    loadFiles()
  }, [loadFiles])

  useEffect(() => {
    const hasProcessing = files.some(f => f.status === 'processing' || f.status === 'pending')
    const pollInterval = hasProcessing ? 3000 : 10000

    const interval = setInterval(loadFiles, pollInterval)
    return () => clearInterval(interval)
  }, [files, loadFiles])

  const handleRetry = async (fileId: string) => {
    setRetryingIds(prev => new Set(prev).add(fileId))
    try {
      await retryFile(fileId)
      await loadFiles()
    } catch (error) {
      console.error('Failed to retry file:', error)
    } finally {
      setRetryingIds(prev => {
        const next = new Set(prev)
        next.delete(fileId)
        return next
      })
    }
  }

  const handleDelete = async (fileId: string) => {
    if (!confirm('Are you sure you want to delete this file? This will remove the file, its embeddings, and all associated data.')) {
      return
    }
    setDeletingIds(prev => new Set(prev).add(fileId))
    try {
      await deleteFile(fileId)
      await loadFiles()
    } catch (error) {
      console.error('Failed to delete file:', error)
    } finally {
      setDeletingIds(prev => {
        const next = new Set(prev)
        next.delete(fileId)
        return next
      })
    }
  }

  const handleReembed = async (fileId: string) => {
    setReembeddingIds(prev => new Set(prev).add(fileId))
    try {
      await reembedFile(fileId)
      await loadFiles()
    } catch (error) {
      console.error('Failed to reembed file:', error)
    } finally {
      setReembeddingIds(prev => {
        const next = new Set(prev)
        next.delete(fileId)
        return next
      })
    }
  }

  const handleCancel = async (fileId: string) => {
    setCancellingIds(prev => new Set(prev).add(fileId))
    try {
      // Cancel all jobs for this file
      const jobsForFile = activeJobs.filter(j => j.file_id === fileId)
      await Promise.all(jobsForFile.map(j => cancelJob(j.id)))
      await loadFiles()
    } catch (error) {
      console.error('Failed to cancel jobs:', error)
    } finally {
      setCancellingIds(prev => {
        const next = new Set(prev)
        next.delete(fileId)
        return next
      })
    }
  }

  const handleCancelAll = async () => {
    if (!confirm(`Cancel all ${activeJobs.length} active jobs?`)) {
      return
    }
    setCancellingAll(true)
    try {
      await cancelAllJobs()
      await loadFiles()
    } catch (error) {
      console.error('Failed to cancel all jobs:', error)
    } finally {
      setCancellingAll(false)
    }
  }

  const filteredFiles = files.filter(f => {
    if (searchQuery) {
      return f.filename.toLowerCase().includes(searchQuery.toLowerCase())
    }
    return true
  })

  const statusCounts = files.reduce((acc, f) => {
    acc[f.status] = (acc[f.status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <p className="text-muted-foreground">
          {files.length} files • {statusCounts.completed || 0} processed
        </p>
        <div className="flex gap-2">
          {activeJobs.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancelAll}
              disabled={cancellingAll}
              className="text-destructive hover:text-destructive"
            >
              {cancellingAll ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <StopCircle className="h-4 w-4 mr-2" />
              )}
              Cancel All ({activeJobs.length})
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={loadFiles}
            disabled={loading}
          >
            <RefreshCw className={cn('h-4 w-4 mr-2', loading && 'animate-spin')} />
            Refresh
          </Button>
          <Button
            variant={showSearch ? 'secondary' : 'outline'}
            size="sm"
            onClick={() => setShowSearch(!showSearch)}
          >
            <Search className="h-4 w-4 mr-2" />
            Search
          </Button>
        </div>
      </div>

      {showSearch && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            autoFocus
          />
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        {(['all', 'pending', 'processing', 'completed', 'failed'] as FilterStatus[]).map(status => (
          <Button
            key={status}
            variant={filter === status ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setFilter(status)}
          >
            {status === 'all' ? 'All' : statusConfig[status].label}
            {status !== 'all' && statusCounts[status] ? ` (${statusCounts[status]})` : ''}
          </Button>
        ))}
      </div>

      {loading && files.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {!loading && files.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <FileSpreadsheet className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
            <h3 className="font-semibold mb-2">No Documents Yet</h3>
            <p className="text-muted-foreground">
              Upload files using the Upload tab to get started.
            </p>
          </CardContent>
        </Card>
      )}

      {filteredFiles.length > 0 && (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {filteredFiles.map(file => (
            <DocumentCard
              key={file.id}
              file={file}
              onRetry={handleRetry}
              onDelete={handleDelete}
              onReembed={handleReembed}
              onCancel={handleCancel}
              retrying={retryingIds.has(file.id)}
              deleting={deletingIds.has(file.id)}
              reembedding={reembeddingIds.has(file.id)}
              cancelling={cancellingIds.has(file.id)}
            />
          ))}
        </div>
      )}

      {!loading && files.length > 0 && filteredFiles.length === 0 && searchQuery && (
        <div className="text-center py-12 text-muted-foreground">
          No files matching "{searchQuery}"
        </div>
      )}
    </div>
  )
}

// ============ Main Documents Page ============

export function DocumentsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const defaultTab = searchParams.get('tab') || 'files'

  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value })
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold font-head flex items-center gap-2">
          <Files className="h-6 w-6 text-primary" />
          Documents
        </h1>
        <p className="text-muted-foreground">Upload and manage your files</p>
      </div>

      <Tabs value={defaultTab} onValueChange={handleTabChange} className="space-y-4">
        <TabsList className="grid w-full grid-cols-2 max-w-xs">
          <TabsTrigger value="files" className="gap-2">
            <FileSpreadsheet className="h-4 w-4" />
            Files
          </TabsTrigger>
          <TabsTrigger value="upload" className="gap-2">
            <Upload className="h-4 w-4" />
            Upload
          </TabsTrigger>
        </TabsList>

        <TabsContent value="files">
          <FilesTab />
        </TabsContent>

        <TabsContent value="upload">
          <UploadTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
