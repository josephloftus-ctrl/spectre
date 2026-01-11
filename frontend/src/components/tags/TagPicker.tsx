import { useState } from 'react'
import { Plus, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TagBadge } from './TagBadge'
import { useTags } from '@/hooks'
import { cn } from '@/lib/utils'

interface TagPickerProps {
  selectedTagIds: string[]
  onChange: (tagIds: string[]) => void
  className?: string
}

const TAG_COLORS = [
  '#3b82f6', // blue
  '#22c55e', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#06b6d4', // cyan
  '#f97316', // orange
  '#ec4899', // pink
]

export function TagPicker({ selectedTagIds, onChange, className }: TagPickerProps) {
  const { tags, create } = useTags()
  const [isCreating, setIsCreating] = useState(false)
  const [newTagName, setNewTagName] = useState('')
  const [newTagColor, setNewTagColor] = useState(TAG_COLORS[0])

  const toggleTag = (tagId: string) => {
    if (selectedTagIds.includes(tagId)) {
      onChange(selectedTagIds.filter(id => id !== tagId))
    } else {
      onChange([...selectedTagIds, tagId])
    }
  }

  const handleCreateTag = async () => {
    if (!newTagName.trim()) return

    const tag = await create(newTagName.trim(), newTagColor)
    onChange([...selectedTagIds, tag.id])
    setNewTagName('')
    setIsCreating(false)
  }

  return (
    <div className={cn("space-y-3", className)}>
      {/* Selected tags */}
      {selectedTagIds.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selectedTagIds.map(tagId => {
            const tag = tags.find(t => t.id === tagId)
            if (!tag) return null
            return (
              <TagBadge
                key={tag.id}
                name={tag.name}
                color={tag.color}
                onRemove={() => toggleTag(tag.id)}
              />
            )
          })}
        </div>
      )}

      {/* Tag list */}
      <div className="flex flex-wrap gap-2">
        {tags
          .filter(tag => !selectedTagIds.includes(tag.id))
          .map(tag => (
            <button
              key={tag.id}
              onClick={() => toggleTag(tag.id)}
              className={cn(
                "inline-flex items-center gap-1 rounded-full text-xs px-2 py-1 border transition-colors",
                "hover:bg-muted"
              )}
              style={{
                borderColor: `${tag.color}40`,
                color: tag.color
              }}
            >
              <Plus className="h-3 w-3" />
              {tag.name}
            </button>
          ))}

        {/* Create new tag button */}
        {!isCreating && (
          <button
            onClick={() => setIsCreating(true)}
            className="inline-flex items-center gap-1 rounded-full text-xs px-2 py-1 border border-dashed border-muted-foreground/30 text-muted-foreground hover:border-muted-foreground/50 transition-colors"
          >
            <Plus className="h-3 w-3" />
            New tag
          </button>
        )}
      </div>

      {/* Create new tag form */}
      {isCreating && (
        <div className="p-3 rounded-lg border bg-muted/30 space-y-3">
          <Input
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
            placeholder="Tag name..."
            className="h-8"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreateTag()
              if (e.key === 'Escape') setIsCreating(false)
            }}
          />

          {/* Color picker */}
          <div className="flex gap-2">
            {TAG_COLORS.map(color => (
              <button
                key={color}
                onClick={() => setNewTagColor(color)}
                className={cn(
                  "h-6 w-6 rounded-full border-2 transition-transform",
                  newTagColor === color ? "border-white scale-110" : "border-transparent"
                )}
                style={{ backgroundColor: color }}
              />
            ))}
          </div>

          <div className="flex gap-2">
            <Button size="sm" onClick={handleCreateTag} disabled={!newTagName.trim()}>
              <Check className="h-3 w-3 mr-1" />
              Create
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setIsCreating(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
