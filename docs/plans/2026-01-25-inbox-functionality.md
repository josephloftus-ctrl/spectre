# Inbox Functionality Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Connect InboxPage to backend API for real file upload, status tracking, and processing workflow.

**Architecture:** Create useFiles hook for API integration, update InboxPage to use real data, add polling for status updates.

**Tech Stack:** React, TypeScript, existing API client at `@/lib/api`

---

## Task 1: Create useFiles Hook

**Files:**
- Create: `frontend/src/hooks/useFiles.ts`
- Modify: `frontend/src/hooks/index.ts`

**Step 1: Create the hook with file operations**

```typescript
import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'

export type FileStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface InboxFile {
  id: string
  filename: string
  original_path: string
  current_path?: string
  file_type: string
  file_size: number
  site_id: string
  status: FileStatus
  error_message?: string
  parsed_data?: string
  created_at: string
  updated_at: string
  processed_at?: string
}

interface FilesResponse {
  files: InboxFile[]
  count: number
}

interface UploadResponse {
  success: boolean
  file: InboxFile
}

export function useFiles(pollInterval = 5000) {
  const [files, setFiles] = useState<InboxFile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchFiles = useCallback(async () => {
    try {
      const response = await api.get<FilesResponse>('/api/files')
      setFiles(response.files)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch files')
    } finally {
      setLoading(false)
    }
  }, [])

  const uploadFile = useCallback(async (file: File, siteId?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (siteId) {
      formData.append('site_id', siteId)
    }

    const response = await api.post<UploadResponse>('/api/files/upload', formData)
    if (response.success) {
      setFiles(prev => [response.file, ...prev])
    }
    return response
  }, [])

  const deleteFile = useCallback(async (fileId: string) => {
    await api.delete(`/api/files/${fileId}`)
    setFiles(prev => prev.filter(f => f.id !== fileId))
  }, [])

  const retryFile = useCallback(async (fileId: string) => {
    const response = await api.post<{ success: boolean; file: InboxFile }>(`/api/files/${fileId}/retry`)
    if (response.success) {
      setFiles(prev => prev.map(f => f.id === fileId ? response.file : f))
    }
    return response
  }, [])

  const getFile = useCallback(async (fileId: string) => {
    return api.get<InboxFile>(`/api/files/${fileId}`)
  }, [])

  // Initial fetch
  useEffect(() => {
    fetchFiles()
  }, [fetchFiles])

  // Poll for updates when there are pending/processing files
  useEffect(() => {
    const hasPendingFiles = files.some(f => f.status === 'pending' || f.status === 'processing')
    if (!hasPendingFiles) return

    const interval = setInterval(fetchFiles, pollInterval)
    return () => clearInterval(interval)
  }, [files, fetchFiles, pollInterval])

  return {
    files,
    loading,
    error,
    uploadFile,
    deleteFile,
    retryFile,
    getFile,
    refresh: fetchFiles,
  }
}
```

**Step 2: Export from hooks index**

Add to `frontend/src/hooks/index.ts`:
```ts
export { useFiles } from './useFiles'
export type { InboxFile, FileStatus } from './useFiles'
```

**Step 3: Commit**

```bash
git add frontend/src/hooks/useFiles.ts frontend/src/hooks/index.ts
git commit -m "feat: add useFiles hook for inbox file management"
```

---

## Task 2: Update InboxPage with Real Data

**Files:**
- Modify: `frontend/src/pages/InboxPage.tsx`

**Step 1: Replace mock data with useFiles hook**

Update InboxPage to use the hook and display real files:

```tsx
import { useState, useRef } from 'react'
import { Upload, FileText, CheckCircle, AlertCircle, Clock, Trash2, RotateCcw, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useFiles, type InboxFile, type FileStatus } from '@/hooks'

const STATUS_CONFIG: Record<FileStatus, { icon: typeof Clock; label: string; className: string }> = {
  pending: { icon: Clock, label: 'Pending', className: 'text-muted-foreground' },
  processing: { icon: Clock, label: 'Processing', className: 'text-primary animate-pulse' },
  completed: { icon: CheckCircle, label: 'Complete', className: 'text-success' },
  failed: { icon: AlertCircle, label: 'Failed', className: 'text-destructive' },
}

export function InboxPage() {
  const { files, loading, error, uploadFile, deleteFile, retryFile } = useFiles()
  const [selectedFile, setSelectedFile] = useState<InboxFile | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      await uploadFile(file)
    } catch (err) {
      console.error('Upload failed:', err)
    } finally {
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDelete = async (fileId: string) => {
    if (!confirm('Delete this file?')) return
    try {
      await deleteFile(fileId)
      if (selectedFile?.id === fileId) {
        setSelectedFile(null)
      }
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  const handleRetry = async (fileId: string) => {
    try {
      await retryFile(fileId)
    } catch (err) {
      console.error('Retry failed:', err)
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

  const getParsedData = (file: InboxFile) => {
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
        <div>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".xlsx,.xls,.csv,.pdf"
            onChange={handleFileChange}
          />
          <Button className="gap-2" onClick={handleUploadClick} disabled={uploading}>
            <Upload className="h-4 w-4" />
            {uploading ? 'Uploading...' : 'Upload Files'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100%-5rem)]">
        {/* File Queue */}
        <Card className="p-4 overflow-hidden flex flex-col">
          <h2 className="font-medium mb-4">File Queue ({files.length})</h2>

          {loading ? (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">
              <Clock className="h-6 w-6 animate-spin mr-2" />
              Loading...
            </div>
          ) : files.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
              <FileText className="h-12 w-12 mb-4 opacity-50" />
              <p>No files in queue</p>
              <p className="text-sm">Upload files to get started</p>
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
                          {file.site_id} • {formatFileSize(file.file_size)}
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
                    <p className="font-medium">{selectedFile.site_id}</p>
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
                  <div className="flex items-center gap-2">
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
                    <p className="text-sm text-destructive">{selectedFile.error_message}</p>
                  </div>
                )}

                {(() => {
                  const parsed = getParsedData(selectedFile)
                  if (!parsed) return null
                  return (
                    <div>
                      <label className="text-sm text-muted-foreground">Parsed Data</label>
                      <div className="mt-1 p-2 rounded bg-muted text-sm">
                        <p>{parsed.metadata?.row_count || 0} rows, {parsed.headers?.length || 0} columns</p>
                        {parsed.headers && (
                          <p className="text-muted-foreground truncate">
                            Columns: {parsed.headers.join(', ')}
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
    </div>
  )
}
```

**Step 2: Verify build**

```bash
npm run build
```

**Step 3: Commit**

```bash
git add frontend/src/pages/InboxPage.tsx
git commit -m "feat: connect InboxPage to backend API with real file operations"
```

---

## Task 3: Add Drag and Drop Upload

**Files:**
- Modify: `frontend/src/pages/InboxPage.tsx`

**Step 1: Add drag and drop zone**

Add drag and drop support to the file queue card:

```tsx
// Add these state variables
const [isDragging, setIsDragging] = useState(false)

// Add these handlers
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

  setUploading(true)
  try {
    await uploadFile(file)
  } catch (err) {
    console.error('Upload failed:', err)
  } finally {
    setUploading(false)
  }
}

// Update the File Queue Card with drag handlers
<Card
  className={`p-4 overflow-hidden flex flex-col transition-colors ${
    isDragging ? 'border-primary border-2 bg-primary/5' : ''
  }`}
  onDragOver={handleDragOver}
  onDragLeave={handleDragLeave}
  onDrop={handleDrop}
>
```

**Step 2: Commit**

```bash
git add frontend/src/pages/InboxPage.tsx
git commit -m "feat: add drag and drop file upload to Inbox"
```

---

## Task 4: Build and Verify

**Step 1: Build frontend**

```bash
cd frontend && npm run build
```

**Step 2: Commit all changes**

```bash
git add -A
git commit -m "feat: complete Phase 3 - Inbox functionality"
```

---

## Summary

**Phase 3 Tasks:**
- Task 1: Create useFiles hook for API integration
- Task 2: Update InboxPage with real data and operations
- Task 3: Add drag and drop upload
- Task 4: Build and verify

**API Integration:**
- GET /api/files - List files
- POST /api/files/upload - Upload file
- DELETE /api/files/{id} - Delete file
- POST /api/files/{id}/retry - Retry failed file
- GET /api/files/{id}/download - Download file
