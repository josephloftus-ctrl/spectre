import { useState, useCallback } from 'react'
import { Upload, FileSpreadsheet, FileText, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface DropZoneProps {
  onFilesDropped: (files: File[]) => void
  accept?: string[]
  className?: string
}

const ACCEPTED_TYPES = [
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // xlsx
  'application/vnd.ms-excel', // xls
  'application/pdf',
  'text/csv'
]

const ACCEPTED_EXTENSIONS = ['.xlsx', '.xls', '.pdf', '.csv']

export function DropZone({ onFilesDropped, className }: DropZoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [dragError, setDragError] = useState<string | null>(null)

  const validateFiles = useCallback((files: File[]): File[] => {
    const valid: File[] = []
    const invalid: string[] = []

    files.forEach(file => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase()
      if (ACCEPTED_TYPES.includes(file.type) || ACCEPTED_EXTENSIONS.includes(ext)) {
        valid.push(file)
      } else {
        invalid.push(file.name)
      }
    })

    if (invalid.length > 0) {
      setDragError(`Unsupported files: ${invalid.join(', ')}`)
      setTimeout(() => setDragError(null), 3000)
    }

    return valid
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    const validFiles = validateFiles(files)

    if (validFiles.length > 0) {
      onFilesDropped(validFiles)
    }
  }, [onFilesDropped, validateFiles])

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files)
      const validFiles = validateFiles(files)

      if (validFiles.length > 0) {
        onFilesDropped(validFiles)
      }
    }
    // Reset input
    e.target.value = ''
  }, [onFilesDropped, validateFiles])

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        "relative border-2 border-dashed rounded-lg p-8 transition-colors",
        isDragging
          ? "border-primary bg-primary/5"
          : "border-muted-foreground/25 hover:border-muted-foreground/50",
        className
      )}
    >
      <input
        type="file"
        multiple
        accept={ACCEPTED_EXTENSIONS.join(',')}
        onChange={handleFileInput}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
      />

      <div className="flex flex-col items-center gap-4 pointer-events-none">
        <div className={cn(
          "h-16 w-16 rounded-full flex items-center justify-center transition-colors",
          isDragging ? "bg-primary/10" : "bg-muted"
        )}>
          <Upload className={cn(
            "h-8 w-8 transition-colors",
            isDragging ? "text-primary" : "text-muted-foreground"
          )} />
        </div>

        <div className="text-center">
          <p className="font-medium">
            {isDragging ? "Drop files here" : "Drag and drop files"}
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            or click to browse
          </p>
        </div>

        <div className="flex gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <FileSpreadsheet className="h-3.5 w-3.5" />
            Excel
          </span>
          <span className="flex items-center gap-1">
            <FileText className="h-3.5 w-3.5" />
            PDF
          </span>
          <span className="flex items-center gap-1">
            <FileText className="h-3.5 w-3.5" />
            CSV
          </span>
        </div>
      </div>

      {dragError && (
        <div className="absolute bottom-2 left-2 right-2 bg-destructive/10 text-destructive text-sm p-2 rounded flex items-center justify-between">
          <span>{dragError}</span>
          <button onClick={() => setDragError(null)}>
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  )
}
