import { useState, useEffect, useRef, useCallback } from 'react'
import { Upload, FileText, CheckCircle, AlertCircle, Clock, Trash2, RotateCcw, Download, Loader2, Calendar, List, MapPin } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { FileTimeline } from '@/components/inbox/FileTimeline'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  fetchFiles,
  fetchSites,
  uploadFile,
  deleteFile,
  retryFile,
  type FileRecord,
  type FileStatus,
  type SiteInfo,
  formatSiteName,
} from '@/lib/api'
import { cn } from '@/lib/utils'

type ViewMode = 'queue' | 'timeline'

const STATUS_CONFIG: Record<FileStatus, { icon: typeof Clock; label: string; className: string }> = {
  pending: { icon: Clock, label: 'Pending', className: 'text-muted-foreground' },
  processing: { icon: Loader2, label: 'Processing', className: 'text-primary animate-spin' },
  completed: { icon: CheckCircle, label: 'Complete', className: 'text-success' },
  failed: { icon: AlertCircle, label: 'Failed', className: 'text-destructive' },
}

export function InboxPage() {
  const [files, setFiles] = useState<FileRecord[]>([])
  const [selectedFile, setSelectedFile] = useState<FileRecord | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>('queue')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Site selection for ambiguous filenames
  const [sites, setSites] = useState<SiteInfo[]>([])
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [selectedSiteId, setSelectedSiteId] = useState<string>('')
  const [showSiteSelector, setShowSiteSelector] = useState(false)

  const loadFiles = useCallback(async () => {
    try {
      const response = await fetchFiles()
      setFiles(response.files)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch files')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadSites = useCallback(async () => {
    try {
      const response = await fetchSites()
      setSites(response.sites)
    } catch (err) {
      console.error('Failed to load sites:', err)
    }
  }, [])

  // Initial load
  useEffect(() => {
    loadFiles()
    loadSites()
  }, [loadFiles, loadSites])

  // Poll for updates when there are pending/processing files
  useEffect(() => {
    const hasPendingFiles = files.some(f => f.status === 'pending' || f.status === 'processing')
    if (!hasPendingFiles) return

    const interval = setInterval(loadFiles, 3000)
    return () => clearInterval(interval)
  }, [files, loadFiles])

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileUpload = async (file: File, siteId?: string) => {
    setUploading(true)
    setError(null)
    try {
      const newFile = await uploadFile(file, siteId)
      setFiles(prev => [newFile, ...prev])
      // Clear site selection state on success
      setPendingFile(null)
      setSelectedSiteId('')
      setShowSiteSelector(false)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Upload failed'
      // Check if error is about ambiguous filename
      if (errorMsg.includes('Cannot determine site')) {
        setPendingFile(file)
        setShowSiteSelector(true)
        setError('Please select a site for this file')
      } else {
        setError(errorMsg)
      }
    } finally {
      setUploading(false)
    }
  }

  const handleSiteSelectedUpload = async () => {
    if (!pendingFile || !selectedSiteId) return
    await handleFileUpload(pendingFile, selectedSiteId)
  }

  const cancelSiteSelection = () => {
    setPendingFile(null)
    setSelectedSiteId('')
    setShowSiteSelector(false)
    setError(null)
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    await handleFileUpload(file)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (!file) return
    await handleFileUpload(file)
  }

  const handleDelete = async (fileId: string) => {
    if (!confirm('Delete this file?')) return
    try {
      await deleteFile(fileId)
      setFiles(prev => prev.filter(f => f.id !== fileId))
      if (selectedFile?.id === fileId) {
        setSelectedFile(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  const handleRetry = async (fileId: string) => {
    try {
      const updatedFile = await retryFile(fileId)
      setFiles(prev => prev.map(f => f.id === fileId ? updatedFile : f))
      if (selectedFile?.id === fileId) {
        setSelectedFile(updatedFile)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Retry failed')
    }
  }

  const handleFileUpdated = (updatedFile: FileRecord) => {
    setFiles(prev => prev.map(f => f.id === updatedFile.id ? updatedFile : f))
    if (selectedFile?.id === updatedFile.id) {
      setSelectedFile(updatedFile)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  const getParsedData = (file: FileRecord) => {
    if (!file.parsed_data) return null
    try {
      return JSON.parse(file.parsed_data)
    } catch {
      return null
    }
  }

  return (
    <div className="h-[calc(100vh-8rem)] animate-page-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold font-head tracking-tight text-foreground">Inbox</h1>
          <p className="text-sm text-muted-foreground mt-1">Upload and validate files before processing</p>
        </div>
        <div className="flex items-center gap-3">
          {/* View Toggle */}
          <div className="flex items-center rounded-xl border border-border/50 bg-muted/60 p-1.5">
            <Button
              variant={viewMode === 'queue' ? 'default' : 'ghost'}
              size="sm"
              className={cn(
                "gap-2 rounded-lg transition-all",
                viewMode === 'queue'
                  ? "shadow-md"
                  : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => setViewMode('queue')}
            >
              <List className="h-4 w-4" />
              Queue
            </Button>
            <Button
              variant={viewMode === 'timeline' ? 'default' : 'ghost'}
              size="sm"
              className={cn(
                "gap-2 rounded-lg transition-all",
                viewMode === 'timeline'
                  ? "shadow-md"
                  : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => setViewMode('timeline')}
            >
              <Calendar className="h-4 w-4" />
              Timeline
            </Button>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".xlsx,.xls,.csv,.pdf"
            onChange={handleFileChange}
          />
          <Button
            className="gap-2 shadow-md btn-press"
            onClick={handleUploadClick}
            disabled={uploading}
          >
            {uploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            {uploading ? 'Uploading...' : 'Upload Files'}
          </Button>
        </div>
      </div>

      {error && !showSiteSelector && (
        <div className="mb-4 p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center gap-3">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {showSiteSelector && pendingFile && (
        <Card className="mb-5 p-5 border-warning/30 bg-warning/5">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-xl bg-warning/15 ring-1 ring-warning/30">
              <MapPin className="h-5 w-5 text-warning" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold font-head text-foreground">Site Required</h3>
              <p className="text-sm text-muted-foreground mb-4 mt-1">
                Cannot determine site from filename "{pendingFile.name}". Please select a site:
              </p>
              <div className="flex items-center gap-3">
                <Select value={selectedSiteId} onValueChange={setSelectedSiteId}>
                  <SelectTrigger className="w-[260px]">
                    <SelectValue placeholder="Select a site..." />
                  </SelectTrigger>
                  <SelectContent>
                    {sites.map((site) => (
                      <SelectItem key={site.site_id} value={site.site_id}>
                        {site.display_name || formatSiteName(site.site_id)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  onClick={handleSiteSelectedUpload}
                  disabled={!selectedSiteId || uploading}
                  className="btn-press"
                >
                  {uploading ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Upload className="h-4 w-4 mr-2" />
                  )}
                  Upload
                </Button>
                <Button variant="ghost" onClick={cancelSiteSelection}>
                  Cancel
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                Tip: Use naming format "MM.DD.YY - Site Name.xlsx" for automatic detection
              </p>
            </div>
          </div>
        </Card>
      )}

      {viewMode === 'timeline' ? (
        <Card className="p-6 h-[calc(100%-5rem)] overflow-y-auto bg-card/80 border-border/50">
          {loading ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mr-3" />
              Loading files...
            </div>
          ) : (
            <FileTimeline files={files} onFileUpdated={handleFileUpdated} />
          )}
        </Card>
      ) : (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 h-[calc(100%-5rem)]">
        {/* File Queue */}
        <Card
          className={cn(
            "p-5 overflow-hidden flex flex-col transition-all duration-200 bg-card/80 border-border/50",
            isDragging && "border-primary border-2 bg-primary/5 shadow-lg shadow-primary/10"
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold font-head tracking-tight">File Queue</h2>
            <span className="text-sm text-muted-foreground bg-muted px-3 py-1 rounded-full border border-border/50 font-medium">
              {files.length} files
            </span>
          </div>

          {loading ? (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mr-3" />
              Loading files...
            </div>
          ) : files.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground border-2 border-dashed border-border/50 rounded-xl bg-muted/30">
              <div className="p-4 rounded-full bg-muted/50 mb-4">
                <FileText className="h-8 w-8 opacity-50" />
              </div>
              <p className="font-medium text-foreground/70">No files in queue</p>
              <p className="text-sm mt-1">Drag & drop files or click Upload to get started</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto space-y-2">
              {files.map((file, index) => {
                const statusConfig = STATUS_CONFIG[file.status]
                const StatusIcon = statusConfig.icon
                return (
                  <button
                    key={file.id}
                    onClick={() => setSelectedFile(file)}
                    className={cn(
                      "w-full p-4 rounded-xl border text-left transition-all duration-150 animate-list-item",
                      selectedFile?.id === file.id
                        ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                        : "border-border/50 hover:border-primary/50 hover:bg-muted/50"
                    )}
                    style={{ animationDelay: `${Math.min(index * 40, 200)}ms` }}
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-muted">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate text-foreground">{file.filename}</p>
                        <p className="text-sm text-muted-foreground mt-0.5">
                          {file.site_id ? formatSiteName(file.site_id) : 'Unknown'} • {formatFileSize(file.file_size)}
                        </p>
                      </div>
                      <StatusIcon className={`h-5 w-5 flex-shrink-0 ${statusConfig.className}`} />
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </Card>

        {/* Preview Pane */}
        <Card className="p-5 overflow-hidden flex flex-col bg-card/80 border-border/50">
          <h2 className="font-semibold font-head tracking-tight mb-4">Preview</h2>

          {!selectedFile ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground border-2 border-dashed border-border/50 rounded-xl bg-muted/30">
              <p className="text-foreground/70">Select a file to preview</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto">
              <div className="space-y-5">
                <div className="p-4 rounded-xl bg-muted/50 border border-border/50">
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">File Name</label>
                  <p className="font-semibold text-foreground mt-1">{selectedFile.filename}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-muted/50 border border-border/50">
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Site</label>
                    <p className="font-semibold text-foreground mt-1">
                      {selectedFile.site_id ? formatSiteName(selectedFile.site_id) : 'Unknown'}
                    </p>
                  </div>
                  <div className="p-4 rounded-xl bg-muted/50 border border-border/50">
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Type</label>
                    <p className="font-semibold text-foreground mt-1 uppercase">{selectedFile.file_type}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-muted/50 border border-border/50">
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Size</label>
                    <p className="font-semibold text-foreground mt-1 font-mono">{formatFileSize(selectedFile.file_size)}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-muted/50 border border-border/50">
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Uploaded</label>
                    <p className="font-semibold text-foreground mt-1">{formatDate(selectedFile.created_at)}</p>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-muted/50 border border-border/50">
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Status</label>
                  <div className="flex items-center gap-2 mt-2">
                    {(() => {
                      const config = STATUS_CONFIG[selectedFile.status]
                      const Icon = config.icon
                      return (
                        <>
                          <Icon className={`h-5 w-5 ${config.className}`} />
                          <span className={cn("font-semibold", config.className)}>{config.label}</span>
                        </>
                      )
                    })()}
                  </div>
                </div>

                {selectedFile.error_message && (
                  <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20">
                    <label className="text-xs font-medium text-destructive uppercase tracking-wide">Error</label>
                    <p className="text-sm text-destructive mt-1">{selectedFile.error_message}</p>
                  </div>
                )}

                {(() => {
                  const parsed = getParsedData(selectedFile)
                  if (!parsed) return null
                  return (
                    <div className="p-4 rounded-xl bg-success/10 border border-success/20">
                      <label className="text-xs font-medium text-success uppercase tracking-wide">Parsed Data</label>
                      <div className="mt-2">
                        <p className="font-semibold text-foreground">
                          <span className="font-mono">{parsed.metadata?.row_count || parsed.rows?.length || 0}</span> rows, <span className="font-mono">{parsed.headers?.length || 0}</span> columns
                        </p>
                        {parsed.headers && (
                          <p className="text-sm text-muted-foreground truncate mt-1">
                            {parsed.headers.slice(0, 5).join(', ')}
                            {parsed.headers.length > 5 && ` +${parsed.headers.length - 5} more`}
                          </p>
                        )}
                      </div>
                    </div>
                  )
                })()}

                <div className="pt-4 flex gap-2">
                  {selectedFile.status === 'failed' && (
                    <Button
                      variant="outline"
                      className="flex-1 gap-2 btn-press"
                      onClick={() => handleRetry(selectedFile.id)}
                    >
                      <RotateCcw className="h-4 w-4" />
                      Retry
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    className="flex-1 gap-2 btn-press"
                    onClick={() => window.open(`/api/files/${selectedFile.id}/download`)}
                  >
                    <Download className="h-4 w-4" />
                    Download
                  </Button>
                  <Button
                    variant="destructive"
                    size="icon"
                    className="btn-press"
                    onClick={() => handleDelete(selectedFile.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
      )}
    </div>
  )
}
