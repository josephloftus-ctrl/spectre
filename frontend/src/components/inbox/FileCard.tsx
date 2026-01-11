import { FileSpreadsheet, FileText, Loader2, Check, AlertCircle, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export type FileStatus = 'pending' | 'processing' | 'ready' | 'error'

interface FileCardProps {
  filename: string
  fileType: 'xlsx' | 'pdf' | 'csv' | 'xls'
  fileSize: number
  status: FileStatus
  errorMessage?: string
  onProcess?: () => void
  onRemove?: () => void
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const icons = {
  xlsx: FileSpreadsheet,
  xls: FileSpreadsheet,
  csv: FileText,
  pdf: FileText
}

const colors = {
  xlsx: 'text-green-500',
  xls: 'text-green-500',
  csv: 'text-blue-500',
  pdf: 'text-red-500'
}

export function FileCard({
  filename,
  fileType,
  fileSize,
  status,
  errorMessage,
  onProcess,
  onRemove
}: FileCardProps) {
  const Icon = icons[fileType] || FileText
  const iconColor = colors[fileType] || 'text-muted-foreground'

  return (
    <div className={cn(
      "flex items-center gap-3 p-3 rounded-lg border",
      status === 'error' && "border-destructive/50 bg-destructive/5"
    )}>
      {/* Icon */}
      <div className={cn("flex-shrink-0", iconColor)}>
        <Icon className="h-8 w-8" />
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{filename}</p>
        <p className="text-xs text-muted-foreground">
          {formatFileSize(fileSize)} • {fileType.toUpperCase()}
        </p>
        {status === 'error' && errorMessage && (
          <p className="text-xs text-destructive mt-1">{errorMessage}</p>
        )}
      </div>

      {/* Status / Actions */}
      <div className="flex-shrink-0 flex items-center gap-2">
        {status === 'pending' && onProcess && (
          <Button size="sm" onClick={onProcess}>
            Process
          </Button>
        )}

        {status === 'processing' && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Processing...
          </div>
        )}

        {status === 'ready' && (
          <div className="flex items-center gap-2 text-sm text-green-500">
            <Check className="h-4 w-4" />
            Done
          </div>
        )}

        {status === 'error' && (
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
          </div>
        )}

        {onRemove && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-destructive"
            onClick={onRemove}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}
