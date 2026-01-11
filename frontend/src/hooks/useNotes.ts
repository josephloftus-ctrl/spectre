import { useState, useEffect, useCallback } from 'react'
import { getNotes, createNote, updateNote, deleteNote, searchNotes, Note } from '@/lib/db'

export function useNotes() {
  const [notes, setNotes] = useState<Note[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const result = await getNotes()
      setNotes(result)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const create = useCallback(async (content: string, options?: {
    documentId?: string
    tags?: string[]
    category?: Note['category']
    isVoiceNote?: boolean
  }) => {
    const note = await createNote(content, options)
    await refresh()
    return note
  }, [refresh])

  const update = useCallback(async (id: string, updates: Partial<Pick<Note, 'content' | 'tags' | 'category'>>) => {
    await updateNote(id, updates)
    await refresh()
  }, [refresh])

  const remove = useCallback(async (id: string) => {
    await deleteNote(id)
    await refresh()
  }, [refresh])

  const search = useCallback(async (query: string) => {
    if (!query.trim()) {
      await refresh()
      return
    }
    const results = await searchNotes(query)
    setNotes(results)
  }, [refresh])

  return {
    notes,
    loading,
    create,
    update,
    remove,
    search,
    refresh
  }
}
