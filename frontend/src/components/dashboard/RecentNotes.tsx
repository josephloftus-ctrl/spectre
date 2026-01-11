import { useNotes } from '@/hooks'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { StickyNote, ChevronRight, Mic } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useNavigate } from 'react-router-dom'

export function RecentNotes() {
  const { notes, loading } = useNotes()
  const navigate = useNavigate()

  const recentNotes = notes.slice(0, 4)

  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <StickyNote className="h-4 w-4 text-primary" />
            Recent Notes
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground animate-pulse">Loading...</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <StickyNote className="h-4 w-4 text-primary" />
            Recent Notes
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            className="text-xs"
            onClick={() => navigate('/notes')}
          >
            View All
            <ChevronRight className="h-3 w-3 ml-1" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {recentNotes.length === 0 ? (
          <div className="text-sm text-muted-foreground text-center py-4">
            No notes yet. Use the + button to capture one.
          </div>
        ) : (
          <div className="space-y-3">
            {recentNotes.map(note => (
              <div
                key={note.id}
                className="group flex items-start gap-3 p-2 -mx-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                onClick={() => navigate('/notes')}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm line-clamp-2 leading-relaxed">
                    {note.content}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(note.createdAt), { addSuffix: true })}
                    </span>
                    {note.isVoiceNote && (
                      <Mic className="h-3 w-3 text-muted-foreground" />
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
