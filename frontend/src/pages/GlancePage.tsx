import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Calendar, Users, FileText, Tag, Brain, Sparkles,
  ChevronLeft, ChevronRight, Loader2, Plus, Clock,
  AlertTriangle, CheckCircle
} from 'lucide-react'
import { fetchGlance, fetchBriefing, createMemoryNote } from '@/lib/api'

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric'
  })
}

function formatShortDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function getDateOffset(days: number): string {
  const date = new Date()
  date.setDate(date.getDate() + days)
  return date.toISOString().split('T')[0]
}

interface NoteFormProps {
  onSubmit: (content: string, title: string, tags: string[]) => void
  isLoading: boolean
}

function NoteForm({ onSubmit, isLoading }: NoteFormProps) {
  const [content, setContent] = useState('')
  const [title, setTitle] = useState('')
  const [tags, setTags] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!content.trim()) return
    const tagList = tags.split(',').map(t => t.trim()).filter(Boolean)
    onSubmit(content, title, tagList)
    setContent('')
    setTitle('')
    setTags('')
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <input
        type="text"
        placeholder="Note title (optional)"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="w-full px-3 py-2 text-sm border rounded-md bg-background"
      />
      <textarea
        placeholder="What's on your mind?"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={3}
        className="w-full px-3 py-2 text-sm border rounded-md bg-background resize-none"
      />
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Tags (comma-separated)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          className="flex-1 px-3 py-2 text-sm border rounded-md bg-background"
        />
        <Button type="submit" disabled={isLoading || !content.trim()} size="sm">
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          <span className="ml-1">Add</span>
        </Button>
      </div>
    </form>
  )
}

export function GlancePage() {
  const [dateOffset, setDateOffset] = useState(0)
  const currentDate = getDateOffset(dateOffset)

  const { data: glanceData, isLoading: glanceLoading, refetch: refetchGlance } = useQuery({
    queryKey: ['glance', currentDate],
    queryFn: () => fetchGlance(currentDate),
  })

  const { data: briefingData, isLoading: briefingLoading } = useQuery({
    queryKey: ['briefing', currentDate],
    queryFn: () => fetchBriefing(currentDate),
  })

  const noteMutation = useMutation({
    mutationFn: ({ content, title, tags }: { content: string; title: string; tags: string[] }) =>
      createMemoryNote(content, title, tags),
    onSuccess: () => {
      refetchGlance()
    },
  })

  const isToday = dateOffset === 0

  return (
    <div className="space-y-6 animate-page-in">
      {/* Header with Date Navigation */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-head flex items-center gap-2">
            <Calendar className="h-6 w-6 text-primary" />
            Your Day At A Glance
          </h1>
          <p className="text-muted-foreground">
            {isToday ? "Today's briefing" : formatDate(currentDate)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={() => setDateOffset(d => d - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant={isToday ? "default" : "outline"}
            onClick={() => setDateOffset(0)}
          >
            Today
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setDateOffset(d => d + 1)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* AI Briefing Card */}
      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Sparkles className="h-5 w-5 text-primary" />
            Morning Briefing
          </CardTitle>
          <CardDescription>AI-generated summary for {formatShortDate(currentDate)}</CardDescription>
        </CardHeader>
        <CardContent>
          {briefingLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating briefing...
            </div>
          ) : briefingData?.summary ? (
            <p className="text-sm leading-relaxed">{briefingData.summary}</p>
          ) : (
            <p className="text-sm text-muted-foreground italic">
              No briefing available. Add schedules and notes to get personalized summaries.
            </p>
          )}

          {/* Quick Stats */}
          {briefingData && (
            <div className="flex flex-wrap gap-4 mt-4 pt-4 border-t">
              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-amber-500" />
                <span>{briefingData.schedule_count} schedule entries</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <FileText className="h-4 w-4 text-blue-500" />
                <span>{briefingData.note_count} notes</span>
              </div>
              {briefingData.recent_anomalies?.length > 0 && (
                <div className="flex items-center gap-2 text-sm text-amber-600">
                  <AlertTriangle className="h-4 w-4" />
                  <span>{briefingData.recent_anomalies.length} issues to review</span>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Main Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* People Working */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4 text-green-500" />
              Who's Working
            </CardTitle>
          </CardHeader>
          <CardContent>
            {glanceLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-6 skeleton rounded" />
                ))}
              </div>
            ) : glanceData?.people_working?.length ? (
              <div className="flex flex-wrap gap-2">
                {glanceData.people_working.map((person, i) => (
                  <span
                    key={i}
                    className="px-3 py-1 text-sm bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full"
                  >
                    {person}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground italic">No schedule data for this day</p>
            )}
          </CardContent>
        </Card>

        {/* Tags */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Tag className="h-4 w-4 text-purple-500" />
              Tags & Topics
            </CardTitle>
          </CardHeader>
          <CardContent>
            {glanceLoading ? (
              <div className="flex gap-2 flex-wrap">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-6 w-16 skeleton rounded-full" />
                ))}
              </div>
            ) : glanceData?.tags?.length ? (
              <div className="flex flex-wrap gap-2">
                {glanceData.tags.map((tag, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded-full"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground italic">No tags for this day</p>
            )}
          </CardContent>
        </Card>

        {/* Recent Anomalies */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Issues to Review
            </CardTitle>
          </CardHeader>
          <CardContent>
            {briefingLoading ? (
              <div className="space-y-2">
                {[1, 2].map(i => (
                  <div key={i} className="h-12 skeleton rounded" />
                ))}
              </div>
            ) : briefingData?.recent_anomalies?.length ? (
              <div className="space-y-2">
                {briefingData.recent_anomalies.slice(0, 3).map((anomaly, i) => (
                  <div
                    key={i}
                    className="p-2 text-sm bg-amber-50 dark:bg-amber-900/20 rounded border border-amber-200 dark:border-amber-800"
                  >
                    {anomaly.summary || 'Issue detected'}
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-2 text-sm text-green-600">
                <CheckCircle className="h-4 w-4" />
                No issues detected
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Notes and Schedules Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Notes */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-500" />
              Notes
            </CardTitle>
            <CardDescription>Personal notes and reminders</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Add Note Form */}
            <NoteForm
              onSubmit={(content, title, tags) => noteMutation.mutate({ content, title, tags })}
              isLoading={noteMutation.isPending}
            />

            {/* Notes List */}
            <div className="space-y-3 pt-4 border-t">
              {glanceLoading ? (
                <div className="space-y-2">
                  {[1, 2].map(i => (
                    <div key={i} className="h-20 skeleton rounded" />
                  ))}
                </div>
              ) : glanceData?.notes?.length ? (
                glanceData.notes.map((note, i) => (
                  <div
                    key={note.id || i}
                    className="p-3 bg-muted/50 rounded-lg"
                  >
                    {(note.metadata as { title?: string })?.title ? (
                      <div className="font-medium text-sm mb-1">{(note.metadata as { title?: string }).title}</div>
                    ) : null}
                    <p className="text-sm text-muted-foreground line-clamp-3">{note.content}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground italic text-center py-4">
                  No notes for this day. Add one above!
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Schedules */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-amber-500" />
              Schedules
            </CardTitle>
            <CardDescription>Schedule entries for {formatShortDate(currentDate)}</CardDescription>
          </CardHeader>
          <CardContent>
            {glanceLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-16 skeleton rounded" />
                ))}
              </div>
            ) : glanceData?.schedules?.length ? (
              <div className="space-y-3">
                {glanceData.schedules.map((schedule, i) => (
                  <div
                    key={schedule.id || i}
                    className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800"
                  >
                    <p className="text-sm">{schedule.content}</p>
                    {(schedule.metadata as { filename?: string })?.filename ? (
                      <p className="text-xs text-muted-foreground mt-1">
                        From: {(schedule.metadata as { filename?: string }).filename}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Calendar className="h-12 w-12 mx-auto text-muted-foreground/30 mb-3" />
                <p className="text-sm text-muted-foreground">No schedules for this day</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Upload schedule files to the Living Memory collection
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Other Files */}
      {(glanceData?.files?.length ?? 0) > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-purple-500" />
              Related Files
            </CardTitle>
            <CardDescription>Other files relevant to this day</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {glanceData?.files?.map((file, i) => (
                <div
                  key={file.id || i}
                  className="p-3 bg-muted/50 rounded-lg"
                >
                  <p className="text-sm line-clamp-2">{file.content}</p>
                  {(file.metadata as { filename?: string })?.filename ? (
                    <p className="text-xs text-muted-foreground mt-1">
                      {(file.metadata as { filename?: string }).filename}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
