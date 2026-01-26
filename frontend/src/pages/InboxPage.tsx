import { useState } from 'react'
import { Upload, FileText, CheckCircle, AlertCircle, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

// Status types for files
type FileStatus = 'pending' | 'processing' | 'needs_review' | 'complete'

interface InboxFile {
  id: string
  name: string
  status: FileStatus
  uploadedAt: Date
  detectedDate?: string
  confidence?: 'high' | 'low'
}

const STATUS_CONFIG = {
  pending: { icon: Clock, label: 'Pending', className: 'text-muted-foreground' },
  processing: { icon: Clock, label: 'Processing', className: 'text-primary animate-pulse' },
  needs_review: { icon: AlertCircle, label: 'Needs Review', className: 'text-warning' },
  complete: { icon: CheckCircle, label: 'Complete', className: 'text-success' },
}

export function InboxPage() {
  // TODO: Connect to real file upload API
  const files: InboxFile[] = []
  const [selectedFile, setSelectedFile] = useState<InboxFile | null>(null)

  return (
    <div className="h-[calc(100vh-7rem)]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Inbox</h1>
          <p className="text-muted-foreground">Upload and validate files before processing</p>
        </div>
        <Button className="gap-2">
          <Upload className="h-4 w-4" />
          Upload Files
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100%-5rem)]">
        {/* File Queue */}
        <Card className="p-4 overflow-hidden flex flex-col">
          <h2 className="font-medium mb-4">File Queue</h2>

          {files.length === 0 ? (
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
                      <FileText className="h-5 w-5 text-muted-foreground" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{file.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {file.detectedDate || 'Processing...'}
                        </p>
                      </div>
                      <StatusIcon className={`h-5 w-5 ${statusConfig.className}`} />
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
                  <p className="font-medium">{selectedFile.name}</p>
                </div>

                <div>
                  <label className="text-sm text-muted-foreground">Detected Date</label>
                  <div className="flex items-center gap-2">
                    <p className="font-medium">{selectedFile.detectedDate || '—'}</p>
                    {selectedFile.confidence === 'low' && (
                      <span className="text-xs px-2 py-0.5 rounded bg-warning/10 text-warning">
                        Please verify
                      </span>
                    )}
                  </div>
                </div>

                <div className="pt-4 flex gap-2">
                  <Button className="flex-1">Accept</Button>
                  <Button variant="outline" className="flex-1">Override Date</Button>
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
