import { formatDistanceToNow } from 'date-fns'
import { Trash2, Mic } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Note } from '@/lib/db'
import { cn } from '@/lib/utils'

interface NotesListProps {
  notes: Note[]
  selectedId?: string
  onSelect: (note: Note) => void
  onDelete: (id: string) => void
}

export function NotesList({ notes, selectedId, onSelect, onDelete }: NotesListProps) {
  if (notes.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p>No notes yet</p>
        <p className="text-sm mt-1">Create your first note to get started</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {notes.map(note => (
        <div
          key={note.id}
          onClick={() => onSelect(note)}
          className={cn(
            "p-4 rounded-lg border cursor-pointer transition-colors",
            "hover:bg-muted/50",
            selectedId === note.id && "bg-muted border-primary"
          )}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="font-medium truncate">{note.title}</h3>
                {note.isVoiceNote && (
                  <Mic className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                )}
                {note.pendingSync && (
                  <div className="h-2 w-2 rounded-full bg-yellow-500 flex-shrink-0" title="Pending sync" />
                )}
              </div>

              {note.content.split('\n').length > 1 && (
                <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                  {note.content.split('\n').slice(1).join(' ')}
                </p>
              )}

              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(note.updatedAt), { addSuffix: true })}
                </span>

                {note.category && (
                  <Badge variant="secondary" className="text-xs">
                    {note.category}
                  </Badge>
                )}

                {note.tags.length > 0 && (
                  <span className="text-xs text-muted-foreground">
                    +{note.tags.length} tags
                  </span>
                )}
              </div>
            </div>

            <Button
              variant="ghost"
              size="icon"
              className="flex-shrink-0 h-8 w-8 text-muted-foreground hover:text-destructive"
              onClick={(e) => {
                e.stopPropagation()
                onDelete(note.id)
              }}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ))}
    </div>
  )
}
