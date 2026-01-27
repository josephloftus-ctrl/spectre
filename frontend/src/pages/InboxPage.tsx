import { useState, useEffect, useRef, useCallback } from 'react'
import { Upload, FileText, CheckCircle, AlertCircle, Clock, Trash2, RotateCcw, Download, Loader2, Calendar, List } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { FileTimeline } from '@/components/inbox/FileTimeline'
import {
  fetchFiles,
  uploadFile,
  deleteFile,
  retryFile,
  type FileRecord,
  type FileStatus,
  formatSiteName,
} from '@/lib/api'

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

  // Initial load
  useEffect(() => {
    loadFiles()
  }, [loadFiles])

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

  const handleFileUpload = async (file: File) => {
    setUploading(true)
    setError(null)
    try {
      const newFile = await uploadFile(file)
      setFiles(prev => [newFile, ...prev])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
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
    <div className="h-[calc(100vh-7rem)]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Inbox</h1>
          <p className="text-muted-foreground">Upload and validate files before processing</p>
        </div>
        <div className="flex items-center gap-2">
          {/* View Toggle */}
          <div className="flex items-center rounded-lg border p-1">
            <Button
              variant={viewMode === 'queue' ? 'secondary' : 'ghost'}
              size="sm"
              className="gap-2"
              onClick={() => setViewMode('queue')}
            >
              <List className="h-4 w-4" />
              Queue
            </Button>
            <Button
              variant={viewMode === 'timeline' ? 'secondary' : 'ghost'}
              size="sm"
              className="gap-2"
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
          <Button className="gap-2" onClick={handleUploadClick} disabled={uploading}>
            {uploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            {uploading ? 'Uploading...' : 'Upload Files'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}

      {viewMode === 'timeline' ? (
        <Card className="p-6 h-[calc(100%-5rem)] overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mr-2" />
              Loading files...
            </div>
          ) : (
            <FileTimeline files={files} onFileUpdated={handleFileUpdated} />
          )}
        </Card>
      ) : (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100%-5rem)]">
        {/* File Queue */}
        <Card
          className={`p-4 overflow-hidden flex flex-col transition-colors ${
            isDragging ? 'border-primary border-2 bg-primary/5' : ''
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <h2 className="font-medium mb-4">File Queue ({files.length})</h2>

          {loading ? (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mr-2" />
              Loading...
            </div>
          ) : files.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
              <FileText className="h-12 w-12 mb-4 opacity-50" />
              <p>No files in queue</p>
              <p className="text-sm">Upload files or drag & drop to get started</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto space-y-2">
              {files.map((file) => {
                const statusConfig = STATUS_CONFIG[file.status]
                const StatusIcon = statusConfig.icon
                return (
                  <button
                    key={file.id}
                    onClick={() => setSelectedFile(file)}
                    className={`w-full p-3 rounded-lg border text-left transition-colors ${
                      selectedFile?.id === file.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{file.filename}</p>
                        <p className="text-sm text-muted-foreground">
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
        <Card className="p-4 overflow-hidden flex flex-col">
          <h2 className="font-medium mb-4">Preview</h2>

          {!selectedFile ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
              <p>Select a file to preview</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto">
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-muted-foreground">File Name</label>
                  <p className="font-medium">{selectedFile.filename}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-muted-foreground">Site</label>
                    <p className="font-medium">
                      {selectedFile.site_id ? formatSiteName(selectedFile.site_id) : 'Unknown'}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Type</label>
                    <p className="font-medium uppercase">{selectedFile.file_type}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-muted-foreground">Size</label>
                    <p className="font-medium">{formatFileSize(selectedFile.file_size)}</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Uploaded</label>
                    <p className="font-medium">{formatDate(selectedFile.created_at)}</p>
                  </div>
                </div>

                <div>
                  <label className="text-sm text-muted-foreground">Status</label>
                  <div className="flex items-center gap-2 mt-1">
                    {(() => {
                      const config = STATUS_CONFIG[selectedFile.status]
                      const Icon = config.icon
                      return (
                        <>
                          <Icon className={`h-4 w-4 ${config.className}`} />
                          <span className={config.className}>{config.label}</span>
                        </>
                      )
                    })()}
                  </div>
                </div>

                {selectedFile.error_message && (
                  <div>
                    <label className="text-sm text-muted-foreground">Error</label>
                    <p className="text-sm text-destructive mt-1">{selectedFile.error_message}</p>
                  </div>
                )}

                {(() => {
                  const parsed = getParsedData(selectedFile)
                  if (!parsed) return null
                  return (
                    <div>
                      <label className="text-sm text-muted-foreground">Parsed Data</label>
                      <div className="mt-1 p-3 rounded-lg bg-muted text-sm">
                        <p className="font-medium">
                          {parsed.metadata?.row_count || parsed.rows?.length || 0} rows, {parsed.headers?.length || 0} columns
                        </p>
                        {parsed.headers && (
                          <p className="text-muted-foreground truncate mt-1">
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
                      className="flex-1 gap-2"
                      onClick={() => handleRetry(selectedFile.id)}
                    >
                      <RotateCcw className="h-4 w-4" />
                      Retry
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    className="flex-1 gap-2"
                    onClick={() => window.open(`/api/files/${selectedFile.id}/download`)}
                  >
                    <Download className="h-4 w-4" />
                    Download
                  </Button>
                  <Button
                    variant="destructive"
                    size="icon"
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
