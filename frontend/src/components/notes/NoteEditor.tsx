import { useState, useEffect, useCallback } from 'react'
import { ArrowLeft, Mic, MicOff, Trash2, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useVoice } from '@/hooks'
import { Note } from '@/lib/db'
import { cn } from '@/lib/utils'

interface NoteEditorProps {
  note: Note
  onBack: () => void
  onUpdate: (id: string, updates: { content?: string; tags?: string[] }) => void
  onDelete: (id: string) => void
}

export function NoteEditor({ note, onBack, onUpdate, onDelete }: NoteEditorProps) {
  const [content, setContent] = useState(note.content)
  const [hasChanges, setHasChanges] = useState(false)
  const { isListening, transcript, start, stop, clear, isSupported } = useVoice()

  // Update content when note changes
  useEffect(() => {
    setContent(note.content)
    setHasChanges(false)
  }, [note.id, note.content])

  // Append voice transcript to content
  useEffect(() => {
    if (transcript) {
      setContent(prev => prev + (prev ? ' ' : '') + transcript)
      setHasChanges(true)
      clear()
    }
  }, [transcript, clear])

  // Auto-save with debounce
  useEffect(() => {
    if (!hasChanges) return

    const timer = setTimeout(() => {
      onUpdate(note.id, { content })
      setHasChanges(false)
    }, 500)

    return () => clearTimeout(timer)
  }, [content, hasChanges, note.id, onUpdate])

  const handleContentChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value)
    setHasChanges(true)
  }, [])

  const handleVoiceToggle = useCallback(() => {
    if (isListening) {
      stop()
    } else {
      start()
    }
  }, [isListening, start, stop])

  const handleDelete = useCallback(() => {
    if (confirm('Delete this note?')) {
      onDelete(note.id)
      onBack()
    }
  }, [note.id, onDelete, onBack])

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-2">
            {note.syncedAt ? (
              <Badge variant="outline" className="text-xs">
                <Check className="h-3 w-3 mr-1" />
                Synced
              </Badge>
            ) : (
              <Badge variant="secondary" className="text-xs">
                Not synced
              </Badge>
            )}
            {hasChanges && (
              <span className="text-xs text-muted-foreground">Saving...</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isSupported && (
            <Button
              variant={isListening ? "default" : "outline"}
              size="icon"
              onClick={handleVoiceToggle}
              className={cn(isListening && "animate-pulse bg-red-500 hover:bg-red-600")}
            >
              {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={handleDelete}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 p-4">
        <textarea
          value={content}
          onChange={handleContentChange}
          placeholder="Start typing..."
          className="w-full h-full resize-none bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none text-lg leading-relaxed"
          autoFocus
        />
      </div>

      {/* Voice indicator */}
      {isListening && (
        <div className="p-4 border-t bg-red-500/10">
          <div className="flex items-center gap-2 text-sm">
            <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
            <span>Listening... Speak now</span>
          </div>
        </div>
      )}
    </div>
  )
}
