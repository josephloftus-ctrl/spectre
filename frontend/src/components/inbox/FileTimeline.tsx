import { useState, useMemo } from 'react'
import { Calendar, AlertTriangle, GripVertical, Check, X } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { type FileRecord, updateFile } from '@/lib/api'

interface FileTimelineProps {
  files: FileRecord[]
  onFileUpdated?: (file: FileRecord) => void
}

interface WeekSlot {
  weekStart: Date
  weekEnd: Date
  label: string
  files: FileRecord[]
  isGap: boolean
  isPast: boolean
}

// Parse date from filename like "12.27.24 - PSEG NHQ.xlsx"
function parseDateFromFilename(filename: string): Date | null {
  // Pattern: MM.DD.YY
  const match = filename.match(/^(\d{1,2})\.(\d{1,2})\.(\d{2})\s*-/)
  if (!match) return null

  const [, month, day, year] = match
  const fullYear = 2000 + parseInt(year, 10)
  return new Date(fullYear, parseInt(month, 10) - 1, parseInt(day, 10))
}

// Get week start (Monday) for a date
function getWeekStart(date: Date): Date {
  const d = new Date(date)
  const day = d.getDay()
  const diff = d.getDate() - day + (day === 0 ? -6 : 1)
  return new Date(d.setDate(diff))
}

// Format date as YYYY-MM-DD for API
function formatDateForApi(date: Date): string {
  return date.toISOString().split('T')[0]
}

// Format date for display
function formatDateDisplay(date: Date): string {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// Check if filename follows expected pattern
function checkFilenameWarnings(filename: string): string[] {
  const warnings: string[] = []

  // Check for date pattern
  if (!filename.match(/^\d{1,2}\.\d{1,2}\.\d{2}\s*-/)) {
    warnings.push('Missing date prefix (expected: MM.DD.YY - Site Name)')
  }

  // Check for site name
  if (!filename.match(/-\s*.+\.(xlsx?|csv)$/i)) {
    warnings.push('Missing site name after date')
  }

  return warnings
}

export function FileTimeline({ files, onFileUpdated }: FileTimelineProps) {
  const [editingFile, setEditingFile] = useState<string | null>(null)
  const [selectedDate, setSelectedDate] = useState<string>('')
  const [saving, setSaving] = useState(false)

  // Build timeline with weeks
  const { weeks, unassignedFiles, warnings } = useMemo(() => {
    const now = new Date()
    const weeksMap = new Map<string, WeekSlot>()
    const unassigned: FileRecord[] = []
    const fileWarnings = new Map<string, string[]>()

    // Generate weeks for past 8 weeks
    for (let i = 7; i >= 0; i--) {
      const weekStart = getWeekStart(new Date(now.getTime() - i * 7 * 24 * 60 * 60 * 1000))
      const weekEnd = new Date(weekStart.getTime() + 6 * 24 * 60 * 60 * 1000)
      const key = formatDateForApi(weekStart)

      weeksMap.set(key, {
        weekStart,
        weekEnd,
        label: `${formatDateDisplay(weekStart)} - ${formatDateDisplay(weekEnd)}`,
        files: [],
        isGap: true,
        isPast: weekEnd < now
      })
    }

    // Sort files into weeks
    for (const file of files) {
      // Check filename warnings
      const warns = checkFilenameWarnings(file.filename)
      if (warns.length > 0) {
        fileWarnings.set(file.id, warns)
      }

      // Determine the inventory date
      let invDate: Date | null = null

      if (file.inventory_date) {
        invDate = new Date(file.inventory_date)
      } else {
        // Try to parse from filename
        invDate = parseDateFromFilename(file.filename)
      }

      if (invDate) {
        const weekKey = formatDateForApi(getWeekStart(invDate))
        const week = weeksMap.get(weekKey)
        if (week) {
          week.files.push(file)
          week.isGap = false
        } else {
          // File is outside our range, treat as unassigned
          unassigned.push(file)
        }
      } else {
        unassigned.push(file)
      }
    }

    return {
      weeks: Array.from(weeksMap.values()).reverse(), // Most recent first
      unassignedFiles: unassigned,
      warnings: fileWarnings
    }
  }, [files])

  const handleAssignDate = async (fileId: string) => {
    if (!selectedDate) return

    setSaving(true)
    try {
      const updated = await updateFile(fileId, { inventory_date: selectedDate })
      onFileUpdated?.(updated)
      setEditingFile(null)
      setSelectedDate('')
    } catch (err) {
      console.error('Failed to update file date:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleQuickAssign = async (fileId: string, date: Date) => {
    setSaving(true)
    try {
      const updated = await updateFile(fileId, { inventory_date: formatDateForApi(date) })
      onFileUpdated?.(updated)
    } catch (err) {
      console.error('Failed to update file date:', err)
    } finally {
      setSaving(false)
    }
  }

  const gaps = weeks.filter(w => w.isGap && w.isPast)

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <span>{files.length} files</span>
        </div>
        {gaps.length > 0 && (
          <div className="flex items-center gap-2 text-warning">
            <AlertTriangle className="h-4 w-4" />
            <span>{gaps.length} missing week{gaps.length !== 1 ? 's' : ''}</span>
          </div>
        )}
        {unassignedFiles.length > 0 && (
          <Badge variant="secondary">{unassignedFiles.length} unassigned</Badge>
        )}
      </div>

      {/* Unassigned Files */}
      {unassignedFiles.length > 0 && (
        <Card className="p-4">
          <h3 className="font-medium mb-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-warning" />
            Unassigned Files
          </h3>
          <div className="space-y-2">
            {unassignedFiles.map(file => (
              <div
                key={file.id}
                className="flex items-center gap-3 p-2 rounded-lg bg-muted/50"
              >
                <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{file.filename}</p>
                  {warnings.get(file.id)?.map((warn, i) => (
                    <p key={i} className="text-xs text-warning">{warn}</p>
                  ))}
                </div>

                {editingFile === file.id ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="date"
                      value={selectedDate}
                      onChange={e => setSelectedDate(e.target.value)}
                      className="text-sm border rounded px-2 py-1"
                    />
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      onClick={() => handleAssignDate(file.id)}
                      disabled={!selectedDate || saving}
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      onClick={() => {
                        setEditingFile(null)
                        setSelectedDate('')
                      }}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setEditingFile(file.id)}
                  >
                    Assign Date
                  </Button>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Timeline */}
      <div className="space-y-2">
        {weeks.map(week => (
          <Card
            key={week.label}
            className={cn(
              "p-3 transition-colors",
              week.isGap && week.isPast && "border-warning/50 bg-warning/5",
              !week.isPast && "opacity-60"
            )}
          >
            <div className="flex items-center gap-3">
              {/* Week label */}
              <div className="w-40 flex-shrink-0">
                <p className="text-sm font-medium">{week.label}</p>
                {week.isGap && week.isPast && (
                  <p className="text-xs text-warning">No inventory file</p>
                )}
                {!week.isPast && (
                  <p className="text-xs text-muted-foreground">Upcoming</p>
                )}
              </div>

              {/* Files in this week */}
              <div className="flex-1 flex flex-wrap gap-2">
                {week.files.map(file => (
                  <div
                    key={file.id}
                    className={cn(
                      "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm",
                      file.status === 'completed' ? "bg-green-500/10 text-green-700 dark:text-green-400" :
                      file.status === 'failed' ? "bg-destructive/10 text-destructive" :
                      "bg-muted"
                    )}
                  >
                    <span className="truncate max-w-[200px]">{file.filename}</span>
                    {warnings.get(file.id) && (
                      <AlertTriangle className="h-3 w-3 text-warning flex-shrink-0" />
                    )}
                  </div>
                ))}

                {/* Drop zone for unassigned files */}
                {week.files.length === 0 && unassignedFiles.length > 0 && (
                  <div className="flex-1 min-h-[32px] border-2 border-dashed rounded-lg flex items-center justify-center text-xs text-muted-foreground">
                    Drag file here or click to assign
                  </div>
                )}
              </div>

              {/* Quick assign buttons for gap weeks */}
              {week.isGap && week.isPast && unassignedFiles.length > 0 && (
                <div className="flex-shrink-0">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-xs"
                    onClick={() => handleQuickAssign(unassignedFiles[0].id, week.weekStart)}
                    disabled={saving}
                  >
                    Assign Latest
                  </Button>
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>

      {/* Naming guide */}
      <Card className="p-4 bg-muted/30">
        <h4 className="text-sm font-medium mb-2">File Naming Guide</h4>
        <p className="text-xs text-muted-foreground">
          Name files as: <code className="px-1 py-0.5 bg-muted rounded">MM.DD.YY - Site Name.xlsx</code>
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Example: <code className="px-1 py-0.5 bg-muted rounded">01.15.25 - PSEG NHQ.xlsx</code>
        </p>
      </Card>
    </div>
  )
}
