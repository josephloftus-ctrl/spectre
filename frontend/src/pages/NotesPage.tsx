import { useState } from 'react'
import { useNotes } from '@/hooks'
import { NotesList, NoteEditor } from '@/components/notes'
import { Input } from '@/components/ui/input'
import { Search, Loader2 } from 'lucide-react'
import { Note } from '@/lib/db'

export function NotesPage() {
  const { notes, loading, update, remove, search } = useNotes()
  const [selectedNote, setSelectedNote] = useState<Note | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  const handleSearch = (query: string) => {
    setSearchQuery(query)
    search(query)
  }

  const handleUpdate = async (id: string, updates: { content?: string; tags?: string[] }) => {
    await update(id, updates)
    // Refresh the selected note
    if (selectedNote?.id === id) {
      const updated = notes.find(n => n.id === id)
      if (updated) setSelectedNote({ ...updated, ...updates } as Note)
    }
  }

  const handleDelete = async (id: string) => {
    await remove(id)
    if (selectedNote?.id === id) {
      setSelectedNote(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // Show editor if a note is selected
  if (selectedNote) {
    return (
      <div className="h-[calc(100vh-120px)] -m-4 lg:-m-6">
        <NoteEditor
          note={selectedNote}
          onBack={() => setSelectedNote(null)}
          onUpdate={handleUpdate}
          onDelete={handleDelete}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-head">Notes</h1>
          <p className="text-muted-foreground">
            {notes.length} {notes.length === 1 ? 'note' : 'notes'}
          </p>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search notes..."
            className="pl-9"
          />
        </div>
      </div>

      {/* Notes List */}
      <NotesList
        notes={notes}
        selectedId={undefined}
        onSelect={setSelectedNote}
        onDelete={handleDelete}
      />
    </div>
  )
}
