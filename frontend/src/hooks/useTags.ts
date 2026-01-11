import { useState, useEffect, useCallback } from 'react'
import { getTags, createTag, deleteTag, Tag } from '@/lib/db'

export function useTags() {
  const [tags, setTags] = useState<Tag[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const result = await getTags()
      setTags(result)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const create = useCallback(async (name: string, color: string) => {
    const tag = await createTag(name, color)
    await refresh()
    return tag
  }, [refresh])

  const remove = useCallback(async (id: string) => {
    await deleteTag(id)
    await refresh()
  }, [refresh])

  // Get system tags vs user tags
  const systemTags = tags.filter(t => t.type === 'system')
  const userTags = tags.filter(t => t.type === 'user')

  // Get tag by ID
  const getTagById = useCallback((id: string) => {
    return tags.find(t => t.id === id)
  }, [tags])

  // Get tags by IDs
  const getTagsByIds = useCallback((ids: string[]) => {
    return tags.filter(t => ids.includes(t.id))
  }, [tags])

  return {
    tags,
    systemTags,
    userTags,
    loading,
    create,
    remove,
    getTagById,
    getTagsByIds,
    refresh
  }
}
