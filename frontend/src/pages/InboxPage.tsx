import { useState, useCallback, useEffect } from 'react'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FolderOpen, RefreshCw, Unplug, FileSpreadsheet, Radio, Book, Utensils, Brain } from 'lucide-react'
import { DropZone, FileCard, FileStatus } from '@/components/inbox'
import { useFolderPicker } from '@/hooks'
import { uploadFile, fetchCollections, CollectionInfo } from '@/lib/api'
import { cn } from '@/lib/utils'

const COLLECTION_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  culinart_bible: Book,
  food_knowledge: Utensils,
  living_memory: Brain,
}

interface PendingFile {
  id: string
  file: File
  status: FileStatus
  errorMessage?: string
  backendId?: string  // ID from backend after upload
}

function getFileType(filename: string): 'xlsx' | 'xls' | 'pdf' | 'csv' {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (ext === 'xlsx') return 'xlsx'
  if (ext === 'xls') return 'xls'
  if (ext === 'pdf') return 'pdf'
  return 'csv'
}

export function InboxPage() {
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
      status: 'pending' as FileStatus
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
      prev.map(f => f.id === id ? { ...f, status: 'processing' as FileStatus } : f)
    )

    try {
      const fileRecord = await uploadFile(pendingFile.file)

      // Map backend status to UI status
      const uiStatus: FileStatus =
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
          status: 'error' as FileStatus,
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
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-head">Inbox</h1>
          <p className="text-muted-foreground">
            Drop files or connect a synced folder
          </p>
        </div>
        {pendingCount > 0 && (
          <Button onClick={handleProcessAll}>
            Process All ({pendingCount})
          </Button>
        )}
      </div>

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
            <h2 className="font-semibold">Files ({pendingFiles.length})</h2>
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
